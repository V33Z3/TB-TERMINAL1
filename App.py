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
st.set_page_config(page_title="TB Institutional Trading Terminal", layout="wide", page_icon="📈")

# Terminal Dark Theme Styling
st.markdown("""
    <style>
    .stApp { background-color: #0b0e14; color: #d1d5db; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; background-color: #0b0e14; padding: 10px 0px; }
    .stTabs [data-baseweb="tab"] { background-color: #161b22; border: 1px solid #30363d; border-radius: 4px; padding: 8px 20px; color: #c9d1d9; font-weight: 600; font-size: 14px; }
    .stTabs [aria-selected="true"] { background-color: #238636 !important; color: white !important; border-color: #2ea043 !important; }
    div[data-testid="stMetric"] { background-color: #161b22; border: 1px solid #30363d; padding: 15px; border-radius: 6px; }
    .terminal-header { background-color: #161b22; border-bottom: 1px solid #30363d; padding: 10px 20px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
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
    st.title("🔐 TB Terminal - Authentication")
    if not supabase:
        st.error("Supabase credentials are missing from Streamlit Secrets. Please configure `SUPABASE_URL` and `SUPABASE_KEY`.")
    else:
        auth_tab1, auth_tab2 = st.tabs(["Log In", "Sign Up"])
        
        with auth_tab1:
            st.subheader("Log Into Your Account")
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
            st.subheader("Create a New Account")
            with st.form("signup_form"):
                signup_email = st.text_input("Email")
                signup_pass = st.text_input("Password", type="password")
                signup_btn = st.form_submit_button("Sign Up")
                
                if signup_btn:
                    try:
                        res = supabase.auth.sign_up({"email": signup_email, "password": signup_pass})
                        st.success("Account created! Check your email to confirm if required, or log in.")
                    except Exception as e:
                        st.error(f"Sign up failed: {e}")
else:
    # Main Application when logged in
    st.sidebar.markdown(f"**Terminal User:** `{st.session_state.user.email}`")
    if st.sidebar.button("Log Out"):
        supabase.auth.sign_out()
        st.session_state.user = None
        st.rerun()
        
    st.markdown("""
        <div class="terminal-header">
            <h3>⚡ VESTTERMINAL // INSTITUTIONAL LIVE FEED</h3>
            <span style="color: #2ea043; font-weight: bold;">● SYSTEM ONLINE</span>
        </div>
    """, unsafe_allow_html=True)
    
    tab_charts, tab_keys, tab_trade, tab_ai = st.tabs([
        "📊 TradingView Charts", 
        "⚙️ API Settings",
        "⚡ Execution Desk", 
        "🤖 AI Intelligence"
    ])
    
    with tab_charts:
        col_s1, col_s2 = st.columns([1, 4])
        with col_s1:
            exchange_prefix = st.selectbox("Exchange", ["NASDAQ", "NYSE", "AMEX", "BINANCE", "FX"])
            ticker_input = st.text_input("Ticker Symbol", "AAPL").upper().strip()
            target_symbol = f"{exchange_prefix}:{ticker_input}"
        
        # Embedded TradingView Advanced Chart Widget
        tv_html = f"""
        <div class="tradingview-widget-container" style="height:650px;width:100%">
          <div class="tradingview-widget-container__widget" style="height:100%;width:100%"></div>
          <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" async>
          {{
            "width": "100%",
            "height": "650",
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
        with col_s2:
            components.html(tv_html, height=660)

    with tab_keys:
        st.subheader("Manage Your Alpaca API Credentials")
        st.info("Your keys are securely stored in your private database profile and only fetched when you execute trades.")
        
        existing_key, existing_sec = "", ""
        try:
            db_res = supabase.table("user_credentials").select("*").eq("user_id", st.session_state.user.id).execute()
            if db_res.data and len(db_res.data) > 0:
                existing_key = db_res.data[0].get("alpaca_key", "")
                existing_sec = db_res.data[0].get("alpaca_secret", "")
        except Exception:
            pass
            
        with st.form("keys_form"):
            new_alpaca_key = st.text_input("Alpaca API Key ID", value=existing_key, type="password")
            new_alpaca_sec = st.text_input("Alpaca Secret Key", value=existing_sec, type="password")
            save_keys_btn = st.form_submit_button("Save Credentials")
            
            if save_keys_btn:
                try:
                    supabase.table("user_credentials").upsert({
                        "user_id": st.session_state.user.id,
                        "alpaca_key": new_alpaca_key,
                        "alpaca_secret": new_alpaca_sec
                    }).execute()
                    st.success("API credentials saved successfully!")
                except Exception as e:
                    st.error(f"Failed to save credentials: {e}")

    with tab_trade:
        st.subheader("Alpaca Execution Desk")
        
        user_alpaca_key, user_alpaca_sec = "", ""
        try:
            db_res = supabase.table("user_credentials").select("*").eq("user_id", st.session_state.user.id).execute()
            if db_res.data and len(db_res.data) > 0:
                user_alpaca_key = db_res.data[0].get("alpaca_key", "")
                user_alpaca_sec = db_res.data[0].get("alpaca_secret", "")
        except Exception:
            pass
            
        account_type = st.radio("Account Mode", ["Paper Trading (Sandbox)", "Live Trading (Real Money)"], horizontal=True)
        is_paper = True if "Paper" in account_type else False

        if not ALPACA_AVAILABLE:
            st.error("The `alpaca-py` library is missing from your requirements.txt file.")
        elif not user_alpaca_key or not user_alpaca_sec:
            st.warning("No Alpaca API keys found. Please save your credentials under the **API Settings** tab first.")
        else:
            try:
                client = TradingClient(user_alpaca_key, user_alpaca_sec, paper=is_paper)
                account = client.get_account()
                
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Account Status", str(account.status))
                m2.metric("Portfolio Equity", f"${float(account.equity):,.2f}")
                m3.metric("Buying Power", f"${float(account.buying_power):,.2f}")
                m4.metric("Cash Balance", f"${float(account.cash):,.2f}")
                
                st.markdown("---")
                st.write("### Route New Order")
                
                with st.form("order_form"):
                    o_col1, o_col2, o_col3 = st.columns(3)
                    with o_col1:
                        order_symbol = st.text_input("Asset Ticker", "AAPL").upper()
                    with o_col2:
                        order_qty = st.number_input("Quantity", min_value=0.01, value=1.0, step=1.0)
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
                        st.success(f"Order successfully routed! Order ID: {res.id}")
            except Exception as e:
                st.error(f"Alpaca Connection Error: {e}")

    with tab_ai:
        st.subheader("Groq Quant Intelligence Assistant")
        sys_prompt = "You are an elite quantitative trading assistant. Give professional guidance on technical setups, risk management, and market analysis."
        user_prompt = st.text_area("Ask the AI about your trading strategy:", "Evaluate momentum and risk parameters for trading tech equities.")
        
        if st.button("Generate AI Insights"):
            if not groq_key:
                st.error("Groq API key not configured in Streamlit Secrets.")
            elif not user_prompt.strip():
                st.warning("Please enter a question.")
            else:
                with st.spinner("Processing analysis via Groq LPU..."):
                    try:
                        ai_client = Groq(api_key=groq_key)
                        completion = ai_client.chat.completions.create(
                            model="llama-3.3-70b-versatile",  # Updated to current valid Groq model
                            messages=[{"role": "system", "content": sys_prompt}, {"role": "user", "content": user_prompt}],
                            temperature=0.7
                        )
                        st.markdown("### Terminal AI Analysis Result:")
                        st.write(completion.choices[0].message.content)
                    except Exception as e:
                        st.error(f"AI Error: {e}")
