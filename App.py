import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go

st.set_page_config(page_title="Strategy Stress Tester", layout="wide")
st.title("Historical Strategy Stress Tester")

# Sidebar Configuration
st.sidebar.header("Backtest Parameters")
ticker = st.sidebar.text_input("Ticker Symbol", value="AAPL").upper()
start_date = st.sidebar.date_input("Start Date", value=pd.to_datetime("2022-01-01"))
end_date = st.sidebar.date_input("End Date", value=pd.to_datetime("2026-01-01"))
initial_capital = st.sidebar.number_input("Initial Capital ($)", value=10000.0, step=1000.0)

st.sidebar.header("Strategy Selection")
strategy_choice = st.sidebar.selectbox(
    "Choose Trading Strategy",
    ["SMA Strategy", "Fibonacci Strategy", "GEX Regime Strategy"]
)

# Strategy-specific configuration parameters
if strategy_choice == "SMA Strategy":
    sma_period = st.sidebar.number_input("SMA Period", value=20, min_value=5, max_value=200)
elif strategy_choice == "Fibonacci Strategy":
    fib_lookback = st.sidebar.number_input("Fib Lookback Window", value=30, min_value=10, max_value=100)
else:
    vol_window = st.sidebar.number_input("Volatility Regime Window", value=14, min_value=5, max_value=50)
    st.sidebar.info("Note: GEX strategy uses a historical volatility & volume structural proxy model to simulate dealer gamma regimes.")

@st.cache_data
def load_data(symbol, start, end):
    df = yf.download(symbol, start=start, end=end)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)
    return df

data = load_data(ticker, start_date, end_date)

if data.empty:
    st.error("No data found for this ticker and date range. Try a different symbol.")
else:
    # Compute indicators based on the user's strategy selection
    if strategy_choice == "SMA Strategy":
        data['Indicator'] = data['Close'].rolling(window=sma_period).mean()
        data = data.dropna()
    elif strategy_choice == "Fibonacci Strategy":
        rolling_high = data['High'].rolling(window=fib_lookback).max()
        rolling_low = data['Low'].rolling(window=fib_lookback).min()
        data['Fib_618'] = rolling_high - ((rolling_high - rolling_low) * 0.618)
        data = data.dropna()
    else:
        # GEX Regime Strategy Proxy: model structural dealer gamma via rolling volatility expansion/compression
        data['Returns'] = data['Close'].pct_change()
        data['Volatility'] = data['Returns'].rolling(window=vol_window).std() * 100
        data['Vol_Mean'] = data['Volatility'].rolling(window=30).mean()
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
            # Buy when price pulls back near the moving average support zone
            is_signal = (current_price <= sma_val * 1.01) and (current_price >= sma_val * 0.98)

        elif strategy_choice == "Fibonacci Strategy":
            fib_val = float(data['Fib_618'].iloc[i])
            # Buy when price dips into the 0.618 golden retracement pocket
            is_signal = (current_price <= fib_val * 1.005) and (current_price >= fib_val * 0.995)

        else:
            # GEX Regime Strategy logic: Buy momentum breakouts when entering negative GEX proxy (high volatility expansion)
            vol = float(data['Volatility'].iloc[i])
            vol_mean = float(data['Vol_Mean'].iloc[i])
            prev_price = float(data['Close'].iloc[i - 1]) if i > 0 else current_price
            is_signal = (vol > vol_mean * 1.2) and (current_price > prev_price)

        if shares == 0 and is_signal and cash > 0:
            shares = cash / current_price
            cash = 0
            trades.append({"Date": date, "Type": "BUY", "Price": current_price})

        elif shares > 0:
            entry_price = trades[-1]["Price"]
            pnl_pct = (current_price - entry_price) / entry_price
            # Exit rules: Take profit at +5% or Stop loss at -3%
            if pnl_pct >= 0.05 or pnl_pct <= -0.03:
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
    col2.metric("Max Drawdown", f"${max_drawdown:.2f}%")
    col3.metric("Total Trades Executed", len(trades) // 2)

    # Plot Equity Curve using Plotly
    fig = go.Figure()
    line_color = 'orange' if strategy_choice == "SMA Strategy" else 'cyan' if strategy_choice == "Fibonacci Strategy" else 'magenta'
    fig.add_trace(go.Scatter(x=data.index, y=data['Portfolio'], mode='lines', name=f'{strategy_choice} Equity ($)', line=dict(color=line_color)))
    fig.update_layout(title=f"Stress Test Results ({strategy_choice}): {ticker}", xaxis_title="Date", height=500)
    st.plotly_chart(fig, use_container_width=True)

    # Show Trade Log Table
    if trades:
        st.subheader("Execution Log")
        st.dataframe(pd.DataFrame(trades))
