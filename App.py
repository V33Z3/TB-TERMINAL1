import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import scipy.stats as si
import plotly.graph_objects as go

st.set_page_config(page_title="Strategy Stress Tester", layout="wide")
st.title("Historical Strategy Stress Tester (Options & Equity Mode)")

# Sidebar Configuration
st.sidebar.header("Backtest Parameters")
ticker = st.sidebar.text_input("Ticker Symbol to Trade", value="AAPL").upper()
start_date = st.sidebar.date_input("Start Date", value=pd.to_datetime("2022-01-01"))
end_date = st.sidebar.date_input("End Date", value=pd.to_datetime("2026-01-01"))
initial_capital = st.sidebar.number_input("Initial Capital ($)", value=10000.0, step=1000.0)

st.sidebar.header("Execution Mode")
trade_mode = st.sidebar.radio("Trade Asset Type", ["Underlying Shares", "Options (2-Weeks Out, $5 OTM)"])

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

# Black-Scholes pricing function for option simulation
def black_scholes_call(S, K, T, r, sigma):
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return max(0.0, S - K)
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    call = S * si.norm.cdf(d1) - K * np.exp(-r * T) * si.norm.cdf(d2)
    return max(0.01, call)

@st.cache_data
def load_data(symbol, start, end):
    df = yf.download(symbol, start=start, end=end)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)
    return df

@st.cache_data
def load_universe_data(symbols, start, end):
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
        universe_tickers = ['AAPL', 'MSFT', 'NVDA', 'AMZN', 'GOOGL', 'META', 'TSLA', 'AMD', 'NFLX', 'SPY', 'QQQ', 'JPM', 'BAC']
        if ticker not in universe_tickers:
            universe_tickers.append(ticker)
        
        univ_data = load_universe_data(universe_tickers, start_date, end_date)
        returns_20d = univ_data.pct_change(20)
        returns_252d = univ_data.pct_change(252)
        
        rs_20 = returns_20d.rank(axis=1, pct=True) * 98 + 1
        rs_252 = returns_252d.rank(axis=1, pct=True) * 98 + 1
        
        data['RS_20'] = rs_20[ticker] if ticker in rs_20.columns else 50
        data['RS_252'] = rs_252[ticker] if ticker in rs_252.columns else 50
        data['RS_Gap'] = data['RS_20'] - data['RS_252']
        data = data.dropna()

    # Calculate rolling historical volatility for option pricing proxy
    data['Daily_Ret'] = data['Close'].pct_change()
    data['Hist_Vol'] = data['Daily_Ret'].rolling(window=20).std() * np.sqrt(252)
    data = data.dropna()

    # Backtest Simulation Engine
    cash = initial_capital
    position_qty = 0
    entry_price = 0.0
    days_in_trade = 0
    portfolio_value = []
    trades = []
    r = 0.045 # Risk-free rate proxy

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
            rs20 = float(data['RS_20'].iloc[i])
            rs252 = float(data['RS_252'].iloc[i])
            rs_gap = float(data['RS_Gap'].iloc[i])
            is_active_bench = (rs20 >= 70) and (rs252 >= 70)
            is_heating_up = rs_gap >= 15 and rs20 >= 60
            is_signal = is_active_bench or is_heating_up

        # Options pricing evaluation per loop iteration
        current_opt_val = 0.0
        if trade_mode == "Options (2-Weeks Out, $5 OTM)":
            iv = max(0.15, float(data['Hist_Vol'].iloc[i]))
            t_expiry = max(0.001, (14 - days_in_trade) / 365.0) if position_qty > 0 else (14 / 365.0)
            strike_price = (entry_price + 5.0) if position_qty > 0 else (current_price + 5.0)
            opt_unit_price = black_scholes_call(current_price, strike_price, t_expiry, r, iv)
            current_opt_val = opt_unit_price * 100 # Standard 100 multiplier

        # Entry condition check
        if position_qty == 0 and is_signal and cash > 0:
            if trade_mode == "Underlying Shares":
                position_qty = cash / current_price
                entry_price = current_price
                cash = 0
                trades.append({"Date": date, "Type": "BUY SHARES", "Price": current_price})
            else:
                iv = max(0.15, float(data['Hist_Vol'].iloc[i]))
                strike_price = current_price + 5.0
                opt_unit_price = black_scholes_call(current_price, strike_price, 14/365.0, r, iv)
                contract_cost = opt_unit_price * 100
                if cash >= contract_cost and contract_cost > 0:
                    position_qty = int(cash // contract_cost)
                    cash -= position_qty * contract_cost
                    entry_price = current_price
                    days_in_trade = 0
                    trades.append({"Date": date, "Type": "BUY OPTION", "Strike": strike_price, "Price": opt_unit_price})

        # Exit condition check / position management
        elif position_qty > 0:
            if trade_mode == "Underlying Shares":
                pnl_pct = (current_price - entry_price) / entry_price
                if pnl_pct >= 0.08 or pnl_pct <= -0.04:
                    cash = position_qty * current_price
                    position_qty = 0
                    trades.append({"Date": date, "Type": "SELL SHARES", "Price": current_price})
            else:
                days_in_trade += 1
                iv = max(0.15, float(data['Hist_Vol'].iloc[i]))
                t_expiry = max(0.001, (14 - days_in_trade) / 365.0)
                strike_price = entry_price + 5.0
                current_opt_price = black_scholes_call(current_price, strike_price, t_expiry, r, iv)
                
                # Exit options if 14 days expire, or option reaches +50% / -50% return target
                initial_iv = max(0.15, float(data['Hist_Vol'].iloc[max(0, i - days_in_trade)]))
                entry_opt_price = black_scholes_call(entry_price, strike_price, 14/365.0, r, initial_iv)
                opt_pnl_pct = (current_opt_price - entry_opt_price) / entry_opt_price if entry_opt_price > 0 else 0
                
                if days_in_trade >= 14 or opt_pnl_pct >= 0.50 or opt_pnl_pct <= -0.50:
                    cash += position_qty * current_opt_price * 100
                    position_qty = 0
                    trades.append({"Date": date, "Type": "SELL OPTION", "Strike": strike_price, "Price": current_opt_price})

        # Track total equity portfolio valuation
        if position_qty == 0:
            total_val = cash
        else:
            if trade_mode == "Underlying Shares":
                total_val = position_qty * current_price
            else:
                total_val = cash + (position_qty * current_opt_val)
                
        portfolio_value.append(total_val)

    data['Portfolio'] = portfolio_value

    # Performance Metrics
    final_value = data['Portfolio'].iloc[-1]
    total_return = ((final_value - initial_capital) / initial_capital) * 100
    
    rolling_max = data['Portfolio'].cummax()
    drawdown = (data['Portfolio'] - rolling_max) / rolling_max
    max_drawdown = drawdown.min() * 100

    col1, col2, col3 = st.columns(3)
    col1.metric("Ending Portfolio Value", f"${final_value:,.2f}", f"{total_return:.2f}%")
    col2.metric("Max Drawdown", f"${max_drawdown:.2f}%")
    col3.metric("Total Trades Executed", len(trades) // (1 if trade_mode == "Underlying Shares" else 2))

    # Plot Price Chart with Execution Markers
    st.subheader(f"Price Chart & Trade Executions: {ticker}")
    fig_price = go.Figure()
    fig_price.add_trace(go.Scatter(x=data.index, y=data['Close'], mode='lines', name='Close Price', line=dict(color='gray', width=1.5)))
    
    buy_dates = [t["Date"] for t in trades if "BUY" in t["Type"]]
    sell_dates = [t["Date"] for t in trades if "SELL" in t["Type"]]

    if buy_dates:
        fig_price.add_trace(go.Scatter(x=buy_dates, y=data.loc[buy_dates]['Close'], mode='markers', name='BUY', marker=dict(symbol='triangle-up', size=12, color='limegreen')))
    if sell_dates:
        fig_price.add_trace(go.Scatter(x=sell_dates, y=data.loc[sell_dates]['Close'], mode='markers', name='SELL', marker=dict(symbol='triangle-down', size=12, color='crimson')))
        
    fig_price.update_layout(xaxis_title="Date", yaxis_title="Price ($)", height=450)
    st.plotly_chart(fig_price, use_container_width=True)

    # Plot Equity Curve
    st.subheader("Strategy Equity Curve")
    fig_equity = go.Figure()
    fig_equity.add_trace(go.Scatter(x=data.index, y=data['Portfolio'], mode='lines', name='Portfolio Value ($)', line=dict(color='lime', width=2)))
    fig_equity.update_layout(xaxis_title="Date", yaxis_title="Value ($)", height=400)
    st.plotly_chart(fig_equity, use_container_width=True)

    if trades:
        st.subheader("Execution Log")
        st.dataframe(pd.DataFrame(trades))
