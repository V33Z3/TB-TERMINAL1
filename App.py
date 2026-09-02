import os
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from groq import Groq

# Try importing Alpaca SDK
try:
    from alpaca.trading.client import TradingClient
    from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
    from alpaca.trading.enums import OrderSide, TimeInForce
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False

# Page configuration
st.set_page_config(page_title="TB Live Trading Terminal", layout="wide", page_icon="📈")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stTabs [data-baseweb="tab-list"] { gap: 12px; }
    .stTabs [data-baseweb="tab"] { background-color: #161b22; border-radius: 6px; padding: 10px 24px; color: white; font-weight: 600; }
    .stTabs [aria-selected="true"] { background-color: #238636 !important; }
    </style>
""", unsafe_allow_html=True)

st.title("📈 TB Institutional Live Trading Terminal")

# Securely load Groq API Key from Streamlit Secrets
groq_key = None
try:
    if "GROQ_API_KEY" in st.secrets:
        groq_key = st.secrets["GROQ_API_KEY"]
except Exception:
    pass

def calculate_fibonacci(high, low):
    diff = high - low
    return {
        "0.0% (Low)": low,
        "23.6% Retracement": low + 0.236 * diff,
        "38.2% Retracement": low + 0.382 * diff,
        "50.0% Retracement": low + 0.500 * diff,
        "61.8% Retracement": low + 0.618 * diff,
        "78.6% Retracement": low + 0.786 * diff,
        "100.0% (High)": high,
        "127.2% Extension": high + 0.272 * diff,
        "161.8% Extension": high + 0.618 * diff,
    }

tab_charts, tab_trade, tab_ai = st.tabs([
    "📊 Charts & Technicals", 
    "⚡ Execute Trade (Alpaca Live)", 
    "🤖 Groq AI Assistant"
])

with tab_charts:
    st.subheader("Interactive Market Data & Fibonacci Analysis")
    c1, c2 = st.columns([1, 4])
    with c1:
        ticker = st.text_input("Ticker Symbol", "AAPL").upper()
        period = st.selectbox("Timeframe", ["1mo", "3mo", "6mo", "1y", "ytd"], index=1)
    
    if ticker:
        try:
            df = yf.download(ticker, period=period)
            if not df.empty:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                
                with c2:
                    fig = go.Figure(data=[go.Candlestick(
                        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name=ticker
                    )])
                    fig.update_layout(title=f"{ticker} Candlestick Chart", template="plotly_dark", height=450)
                    st.plotly_chart(fig, use_container_width=True)
                
                st.markdown("---")
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    st.write("### Fibonacci Levels Calculator")
                    h_val = st.number_input("Swing High ($)", value=float(df['High'].max()))
                    l_val = st.number_input("Swing Low ($)", value=float(df['Low'].min()))
                
                if h_val > l_val:
                    fibs = calculate_fibonacci(h_val, l_val)
                    with col_f2:
                        st.write("### Calculated Price Points")
                        st.dataframe(pd.DataFrame(list(fibs.items()), columns=["Level", "Price ($)"]), use_container_width=True)
            else:
                st.warning("No market data returned for this ticker.")
        except Exception as e:
            st.error(f"Error loading chart data: {e}")

with tab_trade:
    st.subheader("Alpaca Live Account & Order Execution")
    
    default_key = st.secrets.get("ALPACA_API_KEY", "") if "ALPACA_API_KEY" in st.secrets else ""
    default_sec = st.secrets.get("ALPACA_SECRET_KEY", "") if "ALPACA_SECRET_KEY" in st.secrets else ""

    col_k1, col_k2 = st.columns(2)
    with col_k1:
        alpaca_key = st.text_input("Alpaca Live API Key ID", type="password", value=default_key)
    with col_k2:
        alpaca_sec = st.text_input("Alpaca Live Secret Key", type="password", value=default_sec)

    if not ALPACA_AVAILABLE:
        st.error("The `alpaca-py` library is missing from your requirements.txt file.")
    elif alpaca_key and alpaca_sec:
        try:
            client = TradingClient(alpaca_key, alpaca_sec, paper=False)
            account = client.get_account()
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Account Status", str(account.status))
            m2.metric("Portfolio Equity", f"${float(account.equity):,.2f}")
            m3.metric("Buying Power", f"${float(account.buying_power):,.2f}")
            m4.metric("Cash Balance", f"${float(account.cash):,.2f}")
            
            st.markdown("---")
            st.write("### Place Live Order")
            
            with st.form("order_form"):
                o_col1, o_col2, o_col3 = st.columns(3)
                with o_col1:
                    order_symbol = st.text_input("Asset Ticker", "AAPL").upper()
                with o_col2:
                    order_qty = st.number_input("Quantity of Shares", min_value=0.01, value=1.0, step=1.0)
                with o_col3:
                    order_side = st.selectbox("Action", ["BUY", "SELL"])
                
                order_type = st.radio("Order Type", ["Market Order", "Limit Order"], horizontal=True)
                limit_price = 0.0
                if order_type == "Limit Order":
                    limit_price = st.number_input("Limit Price ($)", min_value=0.01, value=100.00)
                
                submit_btn = st.form_submit_button("🚨 Submit Live Order")
                
                if submit_btn:
                    side_enum = OrderSide.BUY if order_side == "BUY" else OrderSide.SELL
                    if order_type == "Market Order":
                        req = MarketOrderRequest(symbol=order_symbol, qty=order_qty, side=side_enum, time_in_force=TimeInForce.GTC)
                    else:
                        req = LimitOrderRequest(symbol=order_symbol, qty=order_qty, side=side_enum, time_in_force=TimeInForce.GTC, limit_price=limit_price)
                    
                    res = client.submit_order(order_data=req)
                    st.success(f"Order successfully placed! Order ID: {res.id}")
        except Exception as e:
            st.error(f"Alpaca Connection Error: {e}")
    else:
        st.info("Please enter your Alpaca Live API keys above to load account metrics and execute live trades.")

with tab_ai:
    st.subheader("Groq-Powered Institutional AI Assistant")
    sys_prompt = "You are an elite quantitative trading assistant. Give professional guidance on technical setups, risk management, and market analysis."
    user_prompt = st.text_area("Ask the AI about your trading strategy:", "Evaluate momentum and risk parameters for trading tech equities.")
    
    if st.button("Generate AI Insights"):
        if not groq_key:
            st.error("Groq API key not configured in Streamlit Secrets.")
        elif not user_prompt.strip():
            st.warning("Please enter a question.")
        else:
            with st.spinner("Processing analysis via Groq..."):
                try:
                    ai_client = Groq(api_key=groq_key)
                    completion = ai_client.chat.completions.create(
                        model="llama-3.1-8b-instant",
                        messages=[{"role": "system", "content": sys_prompt}, {"role": "user", "content": user_prompt}],
                        temperature=0.7
                    )
                    st.markdown("### Analysis Result:")
                    st.write(completion.choices[0].message.content)
                except Exception as e:
                    st.error(f"AI Error: {e}")