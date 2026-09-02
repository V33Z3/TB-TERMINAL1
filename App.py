import streamlit as st
import pandas as pd
import numpy as np
import datetime
import time
import streamlit.components.v1 as components
from groq import Groq
from supabase import create_client, Client

# Try importing yfinance for instant real-time market quotes
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

# Try importing Alpaca SDKs for trading execution
try:
    from alpaca.trading.client import TradingClient
    from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
    from alpaca.trading.enums import OrderSide, TimeInForce
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False

# Page configuration - Wide mode
st.set_page_config(page_title="VestTerminal // Real-Time Institutional Trading", layout="wide", page_icon="📈")

# Pro Exchange Dark Theme Styling
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    .block-container {
        padding-top: 0.5rem;
        padding-bottom: 0rem;
        padding-left: 0.8rem;
        padding-right: 0.8rem;
        max-width: 100% !important;
    }
    
    .stApp { background-color: #0b0e11; color: #b7bdc6; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    
    /* Top Exchange Ticker Bar Layout */
    .exchange-header {
        background-color: #1e2329;
        border-bottom: 1px solid #2b313a;
        padding: 8px 15px;
        display: flex;
        align-items: center;
        gap: 15px;
        font-size: 13px;
        border-radius: 4px;
        margin-bottom: 10px;
        flex-wrap: wrap;
    }
    
    .stTextInput input, .stSelectbox select, .stNumberInput input {
        background-color: #181a20 !important;
        color: #eaecef !important;
        border: 1px solid #2b313a !important;
        border-radius: 3px !important;
        font-size: 13px !important;
        min-height: 30px !important;
    }
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
if "show_splash" not in st.session_state:
    st.session_state.show_splash = False

# Authentication Gate if user is not logged in
if not st.session_state.user:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col_auth1, col_auth2, col_auth3 = st.columns([1, 1.2, 1])
    with col_auth2:
        st.markdown("<h2 style='text-align: center; color: #eaecef;'>🔐 VestTerminal Login</h2>", unsafe_allow_html=True)
        if not supabase:
            st.error("Supabase credentials missing from Streamlit Secrets.")
        else:
            auth_tab1, auth_tab2 = st.tabs(["Sign In", "Register"])
            with auth_tab1:
                with st.form("login_form"):
                    login_email = st.text_input("Email")
                    login_pass = st.text_input("Password", type="password")
                    login_btn = st.form_submit_button("Access Terminal", use_container_width=True)
                    if login_btn:
                        try:
                            res = supabase.auth.sign_in_with_password({"email": login_email, "password": login_pass})
                            st.session_state.user = res.user
                            st.session_state.show_splash = True  # Trigger cool trading boot animation
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
            with auth_tab2:
                with st.form("signup_form"):
                    signup_email = st.text_input("Email")
                    signup_pass = st.text_input("Password", type="password")
                    signup_btn = st.form_submit_button("Create Account", use_container_width=True)
                    if signup_btn:
                        try:
                            supabase.auth.sign_up({"email": signup_email, "password": signup_pass})
                            st.success("Account created! You can now sign in.")
                        except Exception as e:
                            st.error(f"Error: {e}")
else:
    # Play cool trading splash screen animation once right after login
    if st.session_state.show_splash:
        components.html("""
            <div style="background: #0b0e11; height: 100vh; display: flex; flex-direction: column; justify-content: center; align-items: center; color: #eaecef; font-family: -apple-system, sans-serif;">
                <div style="text-align: center;">
                    <div style="font-size: 28px; font-weight: bold; color: #f0b90b; letter-spacing: 2px; margin-bottom: 8px;">⚡ VESTTERMINAL</div>
                    <p style="color: #848e9c; font-size: 12px; font-family: monospace; letter-spacing: 1px;">ESTABLISHING SECURE QUANT FEED & LIQUIDITY NODES...</p>
                    <div style="width: 280px; height: 3px; background: #2b313a; border-radius: 2px; margin: 25px auto; overflow: hidden;">
                        <div style="width: 100%; height: 100%; background: linear-gradient(90deg, transparent, #0ecb81, #f0b90b, transparent); animation: slide 1.2s infinite linear;"></div>
                    </div>
                </div>
            </div>
            <style>
            @keyframes slide {
                0% { transform: translateX(-100%); }
                100% { transform: translateX(100%); }
            }
            </style>
        """, height=700)
        time.sleep(1.8)
        st.session_state.show_splash = False
        st.rerun()

    # Sidebar settings & API credentials retrieval
    with st.sidebar:
        st.markdown("### ⚙️ Terminal Settings")
        if st.button("Log Out", use_container_width=True):
            supabase.auth.sign_out()
            st.session_state.user = None
            st.rerun()
            
        st.markdown("---")
        st.markdown("**Alpaca API Credentials (for Trading Desk)**")
        
        existing_key, existing_sec = "", ""
        try:
            db_res = supabase.table("user_credentials").select("*").eq("user_id", st.session_state.user.id).execute()
            if db_res.data and len(db_res.data) > 0:
                existing_key = db_res.data[0].get("alpaca_key", "")
                existing_sec = db_res.data[0].get("alpaca_secret", "")
        except Exception:
            pass
            
        with st.form("keys_form"):
            new_alpaca_key = st.text_input("API Key ID", value=existing_key, type="password")
            new_alpaca_sec = st.text_input("Secret Key", value=existing_sec, type="password")
            save_keys_btn = st.form_submit_button("Save Keys", use_container_width=True)
            if save_keys_btn:
                try:
                    supabase.table("user_credentials").upsert({
                        "user_id": st.session_state.user.id,
                        "alpaca_key": new_alpaca_key,
                        "alpaca_secret": new_alpaca_sec
                    }).execute()
                    st.success("Saved securely!")
                except Exception as e:
                    st.error(f"Error: {e}")

    # Build top header layout with integrated Ticker Search box
    header_col1, header_col2, header_col3, header_col4 = st.columns([1.5, 1.8, 1.8, 2.2])
    
    with header_col1:
        st.markdown("<div style='padding-top: 5px; color: #f0b90b; font-weight: bold; font-size: 13px;'>⚡ VESTTERMINAL</div>", unsafe_allow_html=True)
    
    with header_col2:
        active_ticker = st.text_input("Search Ticker", value="AAPL", label_visibility="collapsed").upper().strip()

    target_symbol = active_ticker

    # Fetch live real-time prices & % changes via yfinance
    def fetch_live_quote(symbol):
        price, pct = 0.0, 0.0
        if YFINANCE_AVAILABLE:
            try:
                t = yf.Ticker(symbol)
                hist = t.history(period="2d")
                if not hist.empty:
                    price = float(hist['Close'].iloc[-1])
                    prev = float(hist['Close'].iloc[0]) if len(hist) > 1 else float(hist['Open'].iloc[0])
                    pct = ((price - prev) / prev) * 100 if prev > 0 else 0.0
            except Exception:
                pass
        return price, pct

    spy_price, spy_pct = fetch_live_quote("SPY")
    qqq_price, qqq_pct = fetch_live_quote("QQQ")
    active_price, active_pct = fetch_live_quote(active_ticker)

    def format_badge(sym, price, pct, bg_color, border_color):
        color = "#0ecb81" if pct >= 0 else "#f6465d"
        sign = "+" if pct >= 0 else ""
        return f"""
        <div style="background: {bg_color}; border: 1px solid {border_color}; padding: 4px 10px; border-radius: 4px; display: inline-flex; align-items: center; gap: 8px;">
            <b>{sym}</b>
            <span style="color: #eaecef;">${price:,.2f}</span>
            <span style="color: {color}; font-weight: bold;">{sign}{pct:.2f}%</span>
        </div>
        """

    spy_html = format_badge("SPY", spy_price, spy_pct, "#3a1a1a", "#f6465d")
    qqq_html = format_badge("QQQ", qqq_price, qqq_pct, "#3a331a", "#f0b90b")
    active_html = format_badge(f"{active_ticker} (Live)", active_price, active_pct, "#331a3a", "#9c27b0")

    # Render clean exchange bar containing the badges and user email
    st.markdown(f"""
        <div class="exchange-header">
            {spy_html}
            {qqq_html}
            {active_html}
            <span style="margin-left: auto; color: #848e9c; font-size: 12px;">User: <b style="color: #eaecef;">{st.session_state.user.email}</b></span>
        </div>
    """, unsafe_allow_html=True)

    # Main Grid: Advanced Chart on Left, Execution Desk on Right
    col_chart, col_trade = st.columns([3.4, 1.2])

    with col_chart:
        tv_html = f"""
        <div class="tradingview-widget-container" style="height:670px;width:100%">
          <div class="tradingview-widget-container__widget" style="height:100%;width:100%"></div>
          <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" async>
          {{
            "width": "100%",
            "height": "670",
            "symbol": "{target_symbol}",
            "interval": "D",
            "timezone": "Etc/UTC",
            "theme": "dark",
            "style": "1",
            "locale": "en",
            "allow_symbol_change": true,
            "hide_side_toolbar": false,
            "calendar": false,
            "support_host": "https://www.tradingview.com"
          }}
          </script>
        </div>
        """
        components.html(tv_html, height=680)

    with col_trade:
        st.markdown("""
            <div style="background-color: #1e2329; border: 1px solid #2b313a; padding: 10px; border-radius: 4px;">
                <div style="font-weight: bold; font-size: 13px; color: #eaecef; margin-bottom: 8px;">Trading Desk</div>
            </div>
        """, unsafe_allow_html=True)
        
        account_type = st.radio("Mode", ["Paper Trading", "Live Trading"], horizontal=True, label_visibility="collapsed")
        is_paper = True if "Paper" in account_type else False

        user_alpaca_key, user_alpaca_sec = existing_key, existing_sec

        if not ALPACA_AVAILABLE:
            st.error("Missing `alpaca-py` library.")
        elif not user_alpaca_key or not user_alpaca_sec:
            st.warning("Configure your Alpaca keys in the sidebar to execute orders.")
        else:
            try:
                client = TradingClient(user_alpaca_key, user_alpaca_sec, paper=is_paper)
                account = client.get_account()
                
                st.markdown(f"""
                <div style="background-color: #181a20; padding: 8px; border-radius: 3px; border: 1px solid #2b313a; font-size: 11px; margin-top: 8px; margin-bottom: 8px; color: #848e9c;">
                    <b>Equity:</b> <span style="color:#eaecef;">${float(account.equity):,.2f}</span><br>
                    <b>Buying Power:</b> <span style="color:#eaecef;">${float(account.buying_power):,.2f}</span><br>
                    <b>Cash:</b> <span style="color:#eaecef;">${float(account.cash):,.2f}</span>
                </div>
                """, unsafe_allow_html=True)
                
                with st.form("order_exec_form"):
                    o_sym = st.text_input("Asset", value=active_ticker).upper()
                    o_qty = st.number_input("Quantity", min_value=0.01, value=1.0, step=1.0)
                    o_side = st.selectbox("Action", ["BUY", "SELL"])
                    o_type = st.radio("Order Type", ["Market", "Limit"], horizontal=True)
                    
                    limit_p = 0.0
                    if o_type == "Limit":
                        limit_p = st.number_input("Limit Price", min_value=0.01, value=100.00)
                        
                    submit_order = st.form_submit_button("Place Order", use_container_width=True)
                    
                    if submit_order:
                        side_enum = OrderSide.BUY if o_side == "BUY" else OrderSide.SELL
                        if o_type == "Market":
                            req = MarketOrderRequest(symbol=o_sym, qty=o_qty, side=side_enum, time_in_force=TimeInForce.GTC)
                        else:
                            req = LimitOrderRequest(symbol=o_sym, qty=o_qty, side=side_enum, time_in_force=TimeInForce.GTC, limit_price=limit_p)
                        
                        res = client.submit_order(order_data=req)
                        st.success(f"Order executed! ID: {res.id}")
            except Exception as e:
                st.error(f"Connection error: {e}")

    # Bottom AI Assistant drawer
    with st.expander("🤖 Groq Quant Intelligence Assistant"):
        ai_c1, ai_c2 = st.columns([4, 1])
        with ai_c1:
            ai_query = st.text_input("Prompt AI:", "Analyze technical momentum for trading setups.", label_visibility="collapsed")
        with ai_c2:
            ai_btn = st.button("Ask AI", use_container_width=True)
            
        if ai_btn and groq_key and ai_query.strip():
            with st.spinner("Processing..."):
                try:
                    ai_client = Groq(api_key=groq_key)
                    completion = ai_client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "system", "content": "You are an expert institutional trading analyst."}, {"role": "user", "content": ai_query}],
                        temperature=0.7
                    )
                    st.write(completion.choices[0].message.content)
                except Exception as e:
                    st.error(f"AI Error: {e}")
