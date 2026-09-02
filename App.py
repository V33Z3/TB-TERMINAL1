import streamlit as st
import pandas as pd
import numpy as np
import streamlit.components.v1 as components
from groq import Groq
from supabase import create_client, Client

# Try importing Alpaca SDK
try:
    from alpaca.trading.client import TradingClient
    from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
    from alpaca.trading.enums import OrderSide, TimeInForce
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False

# Page configuration
st.set_page_config(page_title="VestTerminal // Institutional Trading", layout="wide", page_icon="📈")

# Professional Crypto/Stock Terminal Dark Theme Styling (Binance / Altrady Style)
st.markdown("""
    <style>
    .stApp { background-color: #121212; color: #e0e0e0; font-family: -apple-system, BlinkMacSystemFont, sans-serif; }
    section[data-testid="stSidebar"] { background-color: #181a20; border-right: 1px: solid #2b2f36; }
    .top-ticker-bar { background-color: #181a20; border: 1px solid #2b2f36; padding: 10px 15px; border-radius: 6px; display: flex; gap: 20px; align-items: center; margin-bottom: 15px; font-size: 13px; }
    .terminal-panel { background-color: #181a20; border: 1px solid #2b2f36; padding: 15px; border-radius: 6px; margin-bottom: 15px; }
    div[data-testid="stMetric"] { background-color: #1e222d; border: 1px solid #2b2f36; padding: 10px; border-radius: 4px; }
    .stTextInput input, .stSelectbox select { background-color: #1e222d !important; color: white !important; border-color: #2b2f36 !important; }
    </style>
""", unsafe_allow_html=True)

# Initialize Supabase client
@st.cache_resource
def init_supabase():
    url = st.secrets.get("SUPABASE_URL", "")
    key = st.secrets.get("SUPABASE_KEY", "")
    if url and key:
        return create_client(url, key)
    return None

supabase = init_supabase()
groq_key = st.secrets.get("GROQ_API_KEY", "")

# Manage login state
if "user" not in st.session_state:
    st.session_state.user = None

# Authentication Gate if user is not logged in
if not st.session_state.user:
    st.title("🔐 VestTerminal - Authentication")
    if not supabase:
        st.error("Supabase credentials are missing from Streamlit Secrets. Please configure `SUPABASE_URL` and `SUPABASE_KEY`.")
    else:
        auth_tab1, auth_tab2 = st.tabs(["Log In", "Sign Up"])
        
        with auth_tab1:
            st.subheader("Log Into Your Terminal")
            with st.form("login_form"):
                login_email = st.text_input("Email")
                login_pass = st.text_input("Password", type="password")
                login_btn = st.form_submit_button("Log In")
                
                if login_btn:
                    try:
                        res = supabase.auth.sign_in_with_password({"email": login_email, "password": login_pass})
                        st.session_state.user = res.user
                        st.success("Successfully logged in!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Login failed: {e}")
                        
        with auth_tab2:
            st.subheader("Create a New Terminal Account")
            with st.form("signup_form"):
                signup_email = st.text_input("Email")
                signup_pass = st.text_input("Password", type="password")
                signup_btn = st.form_submit_button("Sign Up")
                
                if signup_btn:
                    try:
                        res = supabase.auth.sign_up({"email": signup_email, "password": signup_pass})
                        st.success("Account created successfully! You can now log in.")
                    except Exception as e:
                        st.error(f"Sign up failed: {e}")
else:
    # Sidebar Navigation & Settings
    st.sidebar.markdown(f"👤 **{st.session_state.user.email}**")
    if st.sidebar.button("Log Out", use_container_width=True):
        supabase.auth.sign_out()
        st.session_state.user = None
        st.rerun()
        
    st.sidebar.markdown("---")
    st.sidebar.subheader("⚙️ API Configuration")
    
    # Fetch existing keys for user
    existing_key, existing_sec = "", ""
    try:
        db_res = supabase.table("user_credentials").select("*").eq("user_id", st.session_state.user.id).execute()
        if db_res.data and len(db_res.data) > 0:
            existing_key = db_res.data[0].get("alpaca_key", "")
            existing_sec = db_res.data[0].get("alpaca_secret", "")
    except Exception:
        pass
        
    with st.sidebar.form("keys_form"):
        new_alpaca_key = st.text_input("Alpaca API Key ID", value=existing_key, type="password")
        new_alpaca_sec = st.text_input("Alpaca Secret Key", value=existing_sec, type="password")
        save_keys_btn = st.form_submit_button("Save Credentials", use_container_width=True)
        
        if save_keys_btn:
            try:
                supabase.table("user_credentials").upsert({
                    "user_id": st.session_state.user.id,
                    "alpaca_key": new_alpaca_key,
                    "alpaca_secret": new_alpaca_sec
                }).execute()
                st.sidebar.success("Saved!")
            except Exception as e:
                st.sidebar.error(f"Error: {e}")

    # Top Ticker Bar Simulation
    st.markdown("""
        <div class="top-ticker-bar">
            <span>🟢 <b>VESTTERMINAL LIVE</b></span>
            <span><b>BTC/USDT</b> <span style="color:#0ecb81;">33,376.02 (+0.18%)</span></span>
            <span><b>ETH/USDT</b> <span style="color:#f6465d;">1,856.29 (-0.54%)</span></span>
            <span><b>AAPL</b> <span style="color:#0ecb81;">325.85 (+0.22%)</span></span>
            <span style="margin-left: auto; color: #0ecb81;">● SYSTEM ONLINE</span>
        </div>
    """, unsafe_allow_html=True)

    # Main Terminal Layout: Side-by-Side (Chart on left, Execution panel on right)
    col_chart, col_trade = st.columns([3.2, 1.3])

    with col_chart:
        c_in1, c_in2 = st.columns([1, 3])
        with c_in1:
            exchange_prefix = st.selectbox("Exchange", ["NASDAQ", "NYSE", "BINANCE", "FX"])
        with c_in2:
            ticker_input = st.text_input("Active Ticker", "AAPL").upper().strip()
        
        target_symbol = f"{exchange_prefix}:{ticker_input}"
        
        # Embedded TradingView Advanced Chart Widget
        tv_html = f"""
        <div class="tradingview-widget-container" style="height:640px;width:100%">
          <div class="tradingview-widget-container__widget" style="height:100%;width:100%"></div>
          <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" async>
          {{
            "width": "100%",
            "height": "640",
            "symbol": "{target_symbol}",
            "interval": "D",
            "timezone": "Etc/UTC",
            "theme": "dark",
            "style": "1",
            "locale": "en",
            "allow_symbol_change": true,
            "calendar": false,
            "support_host": "https://www.tradingview.com"
          }}
          </script>
        </div>
        """
        components.html(tv_html, height=650)

    with col_trade:
        st.markdown("### ⚡ Trading Desk")
        account_type = st.radio("Mode", ["Paper", "Live"], horizontal=True, label_visibility="collapsed")
        is_paper = True if "Paper" in account_type else False

        user_alpaca_key, user_alpaca_sec = existing_key, existing_sec

        if not ALPACA_AVAILABLE:
            st.error("Missing `alpaca-py` in requirements.txt.")
        elif not user_alpaca_key or not user_alpaca_sec:
            st.warning("Enter your Alpaca API keys in the sidebar to load your trading account.")
        else:
            try:
                client = TradingClient(user_alpaca_key, user_alpaca_sec, paper=is_paper)
                account = client.get_account()
                
                # Portfolio Balances Box
                st.markdown(f"""
                <div style="background-color: #1e222d; padding: 10px; border-radius: 6px; border: 1px solid #2b2f36; font-size: 12px; margin-bottom: 10px;">
                    <b>Equity:</b> ${float(account.equity):,.2f}<br>
                    <b>Buying Power:</b> ${float(account.buying_power):,.2f}<br>
                    <b>Cash:</b> ${float(account.cash):,.2f}
                </div>
                """, unsafe_allow_html=True)
                
                with st.form("order_form"):
                    order_symbol = st.text_input("Symbol", value=ticker_input).upper()
                    order_qty = st.number_input("Quantity", min_value=0.01, value=1.0, step=1.0)
                    order_side = st.selectbox("Action", ["BUY", "SELL"])
                    order_type = st.radio("Type", ["Market", "Limit"], horizontal=True)
                    
                    limit_price = 0.0
                    if order_type == "Limit":
                        limit_price = st.number_input("Limit Price ($)", min_value=0.01, value=100.00)
                    
                    submit_btn = st.form_submit_button("Place Order", use_container_width=True)
                    
                    if submit_btn:
                        side_enum = OrderSide.BUY if order_side == "BUY" else OrderSide.SELL
                        if order_type == "Market":
                            req = MarketOrderRequest(symbol=order_symbol, qty=order_qty, side=side_enum, time_in_force=TimeInForce.GTC)
                        else:
                            req = LimitOrderRequest(symbol=order_symbol, qty=order_qty, side=side_enum, time_in_force=TimeInForce.GTC, limit_price=limit_price)
                        
                        res = client.submit_order(order_data=req)
                        st.success(f"Order Placed! ID: {res.id}")
            except Exception as e:
                st.error(f"Alpaca Connection Error: {e}")

    # Bottom AI Assistant Drawer / Expandable Section
    with st.expander("🤖 Groq Quant AI Intelligence Assistant"):
        sys_prompt = "You are an elite quantitative trading assistant. Give professional guidance on technical setups, risk management, and market analysis."
        ai_col1, ai_col2 = st.columns([3, 1])
        with ai_col1:
            user_prompt = st.text_input("Ask AI about current market setups:", "Evaluate risk parameters for trading tech equities.")
        with ai_col2:
            ask_ai_btn = st.button("Generate Insights", use_container_width=True)
            
        if ask_ai_btn:
            if not groq_key:
                st.error("Groq API key not configured in Streamlit Secrets.")
            elif not user_prompt.strip():
                st.warning("Please enter a question.")
            else:
                with st.spinner("Analyzing via Groq LPU..."):
                    try:
                        ai_client = Groq(api_key=groq_key)
                        completion = ai_client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=[{"role": "system", "content": sys_prompt}, {"role": "user", "content": user_prompt}],
                            temperature=0.7
                        )
                        st.markdown(completion.choices[0].message.content)
                    except Exception as e:
                        st.error(f"AI Error: {e}")
