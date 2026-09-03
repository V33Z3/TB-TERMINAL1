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
sma_period = st.sidebar.number_input("SMA Period", value=20, min_value=5, max_value=200)
initial_capital = st.sidebar.number_input("Initial Capital ($)", value=10000.0, step=1000.0)

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
    # Calculate Indicators
    data['SMA'] = data['Close'].rolling(window=sma_period).mean()
    
    # Calculate rolling Fibonacci 0.618 level based on a 30-day window lookback
    rolling_high = data['High'].rolling(window=30).max()
    rolling_low = data['Low'].rolling(window=30).min()
    data['Fib_618'] = rolling_high - ((rolling_high - rolling_low) * 0.618)
    
    data = data.dropna()

    # Backtest Simulation Engine
    cash = initial_capital
    shares = 0
    portfolio_value = []
    trades = []

    for i in range(len(data)):
        current_price = float(data['Close'].iloc[i])
        sma_val = float(data['SMA'].iloc[i])
        fib_val = float(data['Fib_618'].iloc[i])
        date = data.index[i]

        # Buy Rule: Price dips near SMA and touches the 0.618 Fibonacci zone
        is_near_support = (current_price <= sma_val * 1.01) and (current_price >= fib_val * 0.99)

        if shares == 0 and is_near_support and cash > 0:
            shares = cash / current_price
            cash = 0
            trades.append({"Date": date, "Type": "BUY", "Price": current_price})

        # Sell Rule: Take profit at +5% or Stop loss at -3% (tracked against entry price)
        elif shares > 0:
            entry_price = trades[-1]["Price"]
            pnl_pct = (current_price - entry_price) / entry_price
            if pnl_pct >= 0.05 or pnl_pct <= -0.03:
                cash = shares * current_price
                shares = 0
                trades.append({"Date": date, "Type": "SELL", "Price": current_price})

        current_val = cash if shares == 0 else shares * current_price
        portfolio_value.append(current_val)

    data['Portfolio'] = portfolio_value

    # Performance Metrics
    final_value = data['Portfolio'].iloc[-1]
    total_return = ((final_value - initial_capital) / initial_capital) * 100
    
    # Calculate Max Drawdown
    rolling_max = data['Portfolio'].cummax()
    drawdown = (data['Portfolio'] - rolling_max) / rolling_max
    max_drawdown = drawdown.min() * 100

    # Layout Metrics Display
    col1, col2, col3 = st.columns(3)
    col1.metric("Ending Portfolio Value", f"${final_value:,.2f}", f"{total_return:.2f}%")
    col2.metric("Max Drawdown", f"{max_drawdown:.2f}%")
    col3.metric("Total Trades Executed", len(trades) // 2)

    # Plot Equity Curve and Price Action using Plotly
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=data.index, y=data['Portfolio'], mode='lines', name='Strategy Equity ($)', line=dict(color='orange')))
    fig.update_layout(title=f"Stress Test Results: {ticker}", xaxis_title="Date", height=500)
    st.plotly_chart(fig, use_container_width=True)

    # Show Trade Log
    if trades:
        st.subheader("Execution Log")
        st.dataframe(pd.DataFrame(trades))
