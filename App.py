import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go

st.set_page_config(page_title="Strategy Stress Tester", layout="wide")
st.title("Historical Strategy Stress Tester")

# Sidebar Configuration
st.sidebar.header("Backtest Parameters")
ticker = st.sidebar.text_input("Ticker Symbol to Trade", value="AAPL").upper()
start_date = st.sidebar.date_input("Start Date", value=pd.to_datetime("2022-01-01"))
end_date = st.sidebar.date_input("End Date", value=pd.to_datetime("2026-01-01"))
initial_capital = st.sidebar.number_input("Initial Capital ($)", value=10000.0, step=1000.0)

st.sidebar.header("Strategy Selection")
strategy_choice = st.sidebar.selectbox(
    "Choose Trading Strategy",
    ["SMA Strategy", "Fibonacci Strategy", "GEX Regime Strategy", "Relative Strength (RS) Shape Strategy"]
)

# Strategy-specific configuration parameters
if strategy_choice == "SMA Strategy":
    sma_period = st.sidebar.number_input("SMA Period", value=20, min_value=5, max_value=200)
elif strategy_choice == "Fibonacci Strategy":
    fib_lookback = st.sidebar.number_input("Fib Lookback Window", value=30, min_value=10, max_value=100)
elif strategy_choice == "GEX Regime Strategy":
    vol_window = st.sidebar.number_input("Volatility Regime Window", value=14, min_value=5, max_value=50)
else:
    st.sidebar.info("RS Shape Strategy ranks a universe cross-sectionally across 20D and 252D lookbacks to capture 'Active Bench' leaders or 'Heating Up' breakouts.")

@st.cache_data
def load_data(symbol, start, end):
    df = yf.download(symbol, start=start, end=end)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)
    return df

@st.cache_data
def load_universe_data(symbols, start, end):
    # Download close prices for a cross-sectional universe pool
    universe_df = yf.download(symbols, start=start, end=end, multi_level_index=False)['Close']
    return universe_df

data = load_data(ticker, start_date, end_date)

if data.empty:
    st.error("No data found for this ticker and date range. Try a different symbol.")
else:
    # Compute indicators based on user's strategy selection
    if strategy_choice == "SMA Strategy":
        data['Indicator'] = data['Close'].rolling(window=sma_period).mean()
        data = data.dropna()
    elif strategy_choice == "Fibonacci Strategy":
        rolling_high = data['High'].rolling(window=fib_lookback).max()
        rolling_low = data['Low'].rolling(window=fib_lookback).min()
        data['Fib_618'] = rolling_high - ((rolling_high - rolling_low) * 0.618)
        data = data.dropna()
    elif strategy_choice == "GEX Regime Strategy":
        data['Returns'] = data['Close'].pct_change()
        data['Volatility'] = data['Returns'].rolling(window=vol_window).std() * 100
        data['Vol_Mean'] = data['Volatility'].rolling(window=30).mean()
        data = data.dropna()
    else:
        # Relative Strength Shape Strategy Setup
        universe_tickers = ['AAPL', 'MSFT', 'NVDA', 'AMZN', 'GOOGL', 'META', 'TSLA', 'AMD', 'NFLX', 'SPY', 'QQQ', 'JPM', 'BAC']
        if ticker not in universe_tickers:
            universe_tickers.append(ticker)
        
        univ_data = load_universe_data(universe_tickers, start_date, end_date)
        
        # Calculate cross-sectional percentage rank (1-99) for 20D and 252D returns
        returns_20d = univ_data.pct_change(20)
        returns_252d = univ_data.pct_change(252)
        
        rs_20 = returns_20d.rank(axis=1, pct=True) * 98 + 1
        rs_252 = returns_252d.rank(axis=1, pct=True) * 98 + 1
        
        data['RS_20'] = rs_20[ticker] if ticker in rs_20.columns else 50
        data['RS_252'] = rs_252[ticker] if ticker in rs_252.columns else 50
        data['RS_Gap'] = data['RS_20'] - data['RS_252']
        data = data.dropna()

    # Backtest Simulation Engine
    cash = initial_capital
    shares = 0
    portfolio_value = []
    trades = []

    for i in range(len(data)):
        current_price = float(data['Close'].iloc[i])
        date = data.index[i]
        is_signal = False

        if strategy_choice == "SMA Strategy":
            sma_val = float(data['Indicator'].iloc[i])
            is_signal = (current_price <= sma_val * 1.01) and (current_price >= sma_val * 0.98)

        elif strategy_choice == "Fibonacci Strategy":
            fib_val = float(data['Fib_618'].iloc[i])
            is_signal = (current_price <= fib_val * 1.005) and (current_price >= fib_val * 0.995)

        elif strategy_choice == "GEX Regime Strategy":
            vol = float(data['Volatility'].iloc[i])
            vol_mean = float(data['Vol_Mean'].iloc[i])
            prev_price = float(data['Close'].iloc[i - 1]) if i > 0 else current_price
            is_signal = (vol > vol_mean * 1.2) and (current_price > prev_price)

        else:
            # RS Shape Logic: Enter when stock qualifies as 'Active Bench' (both strong) or 'Heating Up' (short-term gap acceleration)
            rs20 = float(data['RS_20'].iloc[i])
            rs252 = float(data['RS_252'].iloc[i])
            rs_gap = float(data['RS_Gap'].iloc[i])
            
            is_active_bench = (rs20 >= 70) and (rs252 >= 70)
            is_heating_up = rs_gap >= 15 and rs20 >= 60
            
            is_signal = is_active_bench or is_heating_up

        if shares == 0 and is_signal and cash > 0:
            shares = cash / current_price
            cash = 0
            trades.append({"Date": date, "Type": "BUY", "Price": current_price})

        elif shares > 0:
            entry_price = trades[-1]["Price"]
            pnl_pct = (current_price - entry_price) / entry_price
            if pnl_pct >= 0.08 or pnl_pct <= -0.04:  # Slightly wider targets for momentum setups
                cash = shares * current_price
                shares = 0
                trades.append({"Date": date, "Type": "SELL", "Price": current_price})

        current_val = cash if shares == 0 else shares * current_price
        portfolio_value.append(current_val)

    data['Portfolio'] = portfolio_value

    # Performance Metrics Calculation
    final_value = data['Portfolio'].iloc[-1]
    total_return = ((final_value - initial_capital) / initial_capital) * 100
    
    rolling_max = data['Portfolio'].cummax()
    drawdown = (data['Portfolio'] - rolling_max) / rolling_max
    max_drawdown = drawdown.min() * 100

    # Layout Metrics Display
    col1, col2, col3 = st.columns(3)
    col1.metric("Ending Portfolio Value", f"${final_value:,.2f}", f"{total_return:.2f}%")
    col2.metric("Max Drawdown", f"{max_drawdown:.2f}%")
    col3.metric("Total Trades Executed", len(trades) // 2)

    # Plot Equity Curve using Plotly
    fig = go.Figure()
    colors = {
        "SMA Strategy": "orange",
        "Fibonacci Strategy": "cyan",
        "GEX Regime Strategy": "magenta",
        "Relative Strength (RS) Shape Strategy": "lime"
    }
    line_color = colors.get(strategy_choice, 'white')
    fig.add_trace(go.Scatter(x=data.index, y=data['Portfolio'], mode='lines', name=f'{strategy_choice} Equity ($)', line=dict(color=line_color)))
    fig.update_layout(title=f"Stress Test Results ({strategy_choice}): {ticker}", xaxis_title="Date", height=500)
    st.plotly_chart(fig, use_container_width=True)

    # Show Trade Log Table
    if trades:
        st.subheader("Execution Log")
        st.dataframe(pd.DataFrame(trades))
