import streamlit as st
import pandas as pd
import numpy as np
import datetime
import time
import requests
import plotly.graph_objects as go
import streamlit.components.v1 as components
from groq import Groq
from supabase import create_client, Client

# Try importing yfinance for market quotes fallback
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

# Try importing Alpaca SDKs for real-time data and trading execution
try:
    from alpaca.trading.client import TradingClient
    from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
    from alpaca.trading.enums import OrderSide, TimeInForce
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockLatestQuoteRequest, StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    from alpaca.data.enums import DataFeed
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False

# Page configuration - Wide mode with expanded sidebar by default
st.set_page_config(
    page_title="TB TERMINAL // Real-Time Institutional Trading", 
    layout="wide", 
    page_icon="📈",
    initial_sidebar_state="expanded"
)

# Pro Exchange Dark Theme Styling
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    [data-testid="stHeader"] {
        background-color: transparent !important;
    }
    
    .block-container {
        padding-top: 2rem;
        padding-bottom: 0rem;
        padding-left: 0.8rem;
        padding-right: 0.8rem;
        max-width: 100% !important;
    }
    
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stSidebar"], .main { 
        background-color: #131722 !important; 
        color: #b7bdc6; 
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; 
    }
    
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

# Session state initializations
if "user" not in st.session_state:
    st.session_state.user = None
if "show_splash" not in st.session_state:
    st.session_state.show_splash = False
if "active_ticker" not in st.session_state:
    st.session_state.active_ticker = "AAPL"
if "alpaca_key" not in st.session_state:
    st.session_state.alpaca_key = ""
if "alpaca_secret" not in st.session_state:
    st.session_state.alpaca_secret = ""

# Authentication Gate
if not st.session_state.user:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col_auth1, col_auth2, col_auth3 = st.columns([1, 1.2, 1])
    with col_auth2:
        st.markdown("<h2 style='text-align: center; color: #eaecef;'>TB TERMINAL LOGIN</h2>", unsafe_allow_html=True)
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
                            st.session_state.show_splash = True
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
    # Splash Animation
    if st.session_state.show_splash:
        components.html("""
            <div style="background: #131722; height: 100vh; display: flex; flex-direction: column; justify-content: center; align-items: center; color: #eaecef; font-family: -apple-system, sans-serif; overflow: hidden;">
                <div style="text-align: center; width: 100%; max-width: 420px;">
                    <div style="font-size: 28px; font-weight: bold; color: #f0b90b; letter-spacing: 2px; margin-bottom: 5px;">⚡ TB TERMINAL</div>
                    <p style="color: #848e9c; font-size: 11px; font-family: monospace; letter-spacing: 1px; margin-bottom: 20px;">CONNECTING TO EXCHANGE LIQUIDITY & MARKET FEED...</p>
                    
                    <div style="background: #12161c; border: 1px solid #2b313a; border-radius: 6px; padding: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.6);">
                        <svg width="100%" height="110" viewBox="0 0 300 110" style="overflow: visible;">
                            <line x1="0" y1="25" x2="300" y2="25" stroke="#1e2329" stroke-width="1" />
                            <line x1="0" y1="55" x2="300" y2="55" stroke="#1e2329" stroke-width="1" />
                            <line x1="0" y1="85" x2="300" y2="85" stroke="#1e2329" stroke-width="1" />
                            
                            <rect x="35" y="45" width="7" height="30" fill="#f6465d" rx="2" />
                            <line x1="38" y1="35" x2="38" y2="90" stroke="#f6465d" stroke-width="2" />
                            
                            <rect x="75" y="60" width="7" height="20" fill="#0ecb81" rx="2" />
                            <line x1="78" y1="50" x2="78" y2="95" stroke="#0ecb81" stroke-width="2" />
                            
                            <rect x="115" y="40" width="7" height="35" fill="#0ecb81" rx="2" />
                            <line x1="118" y1="25" x2="118" y2="90" stroke="#0ecb81" stroke-width="2" />
                            
                            <rect x="155" y="50" width="7" height="25" fill="#f6465d" rx="2" />
                            <line x1="158" y1="40" x2="158" y2="80" stroke="#f6465d" stroke-width="2" />
                            
                            <rect x="195" y="30" width="7" height="45" fill="#0ecb81" rx="2" />
                            <line x1="198" y1="15" x2="198" y2="85" stroke="#0ecb81" stroke-width="2" />

                            <rect x="235" y="15" width="7" height="55" fill="#0ecb81" rx="2" />
                            <line x1="238" y1="5" x2="238" y2="85" stroke="#0ecb81" stroke-width="2" />

                            <path d="M 15 75 Q 55 85, 95 60 T 175 45 T 255 15" fill="none" stroke="#0ecb81" stroke-width="3" stroke-linecap="round" class="glow-line" />
                        </svg>
                        
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 12px; font-size: 12px;">
                            <span style="color: #848e9c; font-family: monospace;">MOMENTUM SURGE</span>
                            <span style="color: #0ecb81; font-weight: bold; background: rgba(14,203,129,0.15); padding: 2px 6px; border-radius: 3px;">+5.42% ▲</span>
                        </div>
                    </div>

                    <div style="width: 100%; height: 3px; background: #2b313a; border-radius: 2px; margin: 25px 0 10px 0; overflow: hidden;">
                        <div style="width: 100%; height: 100%; background: linear-gradient(90deg, transparent, #0ecb81, #f0b90b, transparent); animation: slide 1.1s infinite linear;"></div>
                    </div>
                </div>
            </div>
            <style>
            @keyframes slide {
                0% { transform: translateX(-100%); }
                100% { transform: translateX(100%); }
            }
            .glow-line {
                filter: drop-shadow(0px 0px 8px rgba(14, 203, 129, 0.7));
                stroke-dasharray: 400;
                stroke-dashoffset: 400;
                animation: drawChart 1.4s ease-in-out forwards;
            }
            @keyframes drawChart {
                to { stroke-dashoffset: 0; }
            }
            </style>
        """, height=700)
        time.sleep(1.8)
        st.session_state.show_splash = False
        st.rerun()

    # Load credentials from DB into Session State if empty
    if not st.session_state.alpaca_key or not st.session_state.alpaca_secret:
        try:
            db_res = supabase.table("user_credentials").select("*").eq("user_id", st.session_state.user.id).execute()
            if db_res.data and len(db_res.data) > 0:
                st.session_state.alpaca_key = db_res.data[0].get("alpaca_key", "")
                st.session_state.alpaca_secret = db_res.data[0].get("alpaca_secret", "")
        except Exception:
            pass

    existing_key = st.session_state.alpaca_key
    existing_sec = st.session_state.alpaca_secret

    # Sidebar settings
    with st.sidebar:
        st.markdown("### ⚙️ Terminal Settings")
        if st.button("Log Out", use_container_width=True):
            supabase.auth.sign_out()
            st.session_state.user = None
            st.session_state.alpaca_key = ""
            st.session_state.alpaca_secret = ""
            st.rerun()

    # Header layout
    header_col1, header_col2, header_col3, header_col4 = st.columns([1.5, 1.8, 1.8, 2.2])
    
    with header_col1:
        st.markdown("<div style='padding-top: 5px; color: #f0b90b; font-weight: bold; font-size: 13px;'>⚡ TB TERMINAL</div>", unsafe_allow_html=True)
    
    with header_col2:
        def on_ticker_change():
            st.session_state.active_ticker = st.session_state.ticker_search_input.upper().strip()
            
        st.text_input("Search Ticker", value=st.session_state.active_ticker, key="ticker_search_input", on_change=on_ticker_change, label_visibility="collapsed")

    target_symbol = st.session_state.active_ticker

    @st.cache_resource
    def get_yf_session():
        session = requests.Session()
        session.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        return session

    def fetch_live_quote(symbol, a_key, a_sec):
        price, pct = 0.0, 0.0
        
        if ALPACA_AVAILABLE and a_key and a_sec:
            try:
                data_client = StockHistoricalDataClient(a_key, a_sec)
                # Use SIP feed for extended-hours pricing quotes
                req = StockLatestQuoteRequest(symbol_or_symbols=[symbol], feed=DataFeed.SIP)
                quotes = data_client.stock_latest_quote(req)
                if symbol in quotes and quotes[symbol]:
                    q = quotes[symbol]
                    price = float(q.ask_price if q.ask_price and q.ask_price > 0 else q.bid_price)
            except Exception:
                pass

        if YFINANCE_AVAILABLE:
            try:
                session = get_yf_session()
                t = yf.Ticker(symbol, session=session)
                hist = t.history(period="2d")
                if not hist.empty:
                    yf_close = float(hist['Close'].iloc[-1])
                    prev = float(hist['Close'].iloc[0]) if len(hist) > 1 else float(hist['Open'].iloc[0])
                    if price == 0.0:
                        price = yf_close
                    pct = ((price - prev) / prev) * 100 if prev > 0 else 0.0
            except Exception:
                pass
                
        return price, pct

    @st.fragment(run_every="3s")
    def render_live_header(sym, a_key, a_sec):
        spy_price, spy_pct = fetch_live_quote("SPY", a_key, a_sec)
        qqq_price, qqq_pct = fetch_live_quote("QQQ", a_key, a_sec)
        active_price, active_pct = fetch_live_quote(sym, a_key, a_sec)

        def format_badge(s, price, pct, bg_color, border_color):
            color = "#0ecb81" if pct >= 0 else "#f6465d"
            sign = "+" if pct >= 0 else ""
            return f"""
            <div style="background: {bg_color}; border: 1px solid {border_color}; padding: 4px 10px; border-radius: 4px; display: inline-flex; align-items: center; gap: 8px;">
                <b>{s}</b>
                <span style="color: #eaecef;">${price:,.2f}</span>
                <span style="color: {color}; font-weight: bold;">{sign}{pct:.2f}%</span>
            </div>
            """

        spy_html = format_badge("SPY", spy_price, spy_pct, "#3a1a1a", "#f6465d")
        qqq_html = format_badge("QQQ", qqq_price, qqq_pct, "#3a331a", "#f0b90b")
        active_html = format_badge(f"{sym} (Live)", active_price, active_pct, "#331a3a", "#9c27b0")

        st.markdown(f"""
            <div class="exchange-header">
                {spy_html}
                {qqq_html}
                {active_html}
            </div>
        """, unsafe_allow_html=True)

    render_live_header(target_symbol, existing_key, existing_sec)

    # Inline Config Panel
    if not existing_key or not existing_sec:
        with st.expander("🔑 CONFIGURATION REQUIRED: Click here to enter your Alpaca API Keys", expanded=True):
            st.info("Enter your Alpaca API credentials below:")
            with st.form("inline_keys_form"):
                ik_col1, ik_col2 = st.columns(2)
                with ik_col1:
                    inline_key = st.text_input("Alpaca API Key ID", value=existing_key, type="password")
                with ik_col2:
                    inline_sec = st.text_input("Alpaca API Secret Key", value=existing_sec, type="password")
                
                save_inline = st.form_submit_button("Save Credentials & Connect Feed", use_container_width=True)
                if save_inline:
                    st.session_state.alpaca_key = inline_key
                    st.session_state.alpaca_secret = inline_sec
                    
                    try:
                        supabase.table("user_credentials").upsert({
                            "user_id": st.session_state.user.id,
                            "alpaca_key": inline_key,
                            "alpaca_secret": inline_sec
                        }).execute()
                        st.success("Credentials saved to database and active!")
                    except Exception:
                        st.warning("Active in session memory!")
                    
                    time.sleep(1)
                    st.rerun()

    # Main Grid: Real-Time Plotly Chart on Left, Execution Desk & Watchlist on Right
    col_chart, col_trade = st.columns([3.4, 1.2])

    with col_chart:
        st.markdown(f"""
            <div style="background-color: #1e2329; border: 1px solid #2b313a; padding: 6px 12px; border-radius: 4px; margin-bottom: 5px; display: flex; justify-content: space-between; align-items: center;">
                <span style="font-weight: bold; font-size: 13px; color: #eaecef;">📊 Real-Time Institutional Feed // {target_symbol} (46,000 Extended-Hours Bars)</span>
                <span style="font-size: 11px; color: #0ecb81; background: rgba(14,203,129,0.1); padding: 2px 6px; border-radius: 3px;">● SIP EXTENDED FEED</span>
            </div>
        """, unsafe_allow_html=True)

        if not existing_key or not existing_sec:
            st.warning("⚠️ Please enter your API keys in the panel above to initialize the live exchange stream.")
        else:
            @st.fragment(run_every="5s")
            def render_realtime_chart(symbol, api_key, api_sec):
                try:
                    data_client = StockHistoricalDataClient(api_key, api_sec)
                    end_dt = datetime.datetime.now(datetime.timezone.utc)
                    # ~3 months captures ~46,000 minute bars when including pre-market and after-hours (SIP feed)
                    start_dt = end_dt - datetime.timedelta(days=90) 
                    
                    all_dfs = []
                    page_token = None
                    
                    # Paginate through Alpaca's SIP API to fetch up to 46,000 bars including extended hours
                    while True:
                        req = StockBarsRequest(
                            symbol_or_symbols=[symbol],
                            timeframe=TimeFrame.Minute,
                            start=start_dt,
                            end=end_dt,
                            limit=10000,
                            page_token=page_token,
                            feed=DataFeed.SIP
                        )
                        bars = data_client.get_stock_bars(req)
                        if bars.df.empty:
                            break
                        all_dfs.append(bars.df)
                        page_token = bars.next_page_token
                        
                        total_bars = sum(len(d) for d in all_dfs)
                        if not page_token or total_bars >= 46000:
                            break
                            
                    df = pd.concat(all_dfs) if all_dfs else pd.DataFrame()
                    
                    if not df.empty:
                        if isinstance(df.index, pd.MultiIndex):
                            df = df.xs(symbol)
                            
                        # Trim precisely to the requested 46,000 bars if needed
                        if len(df) > 46000:
                            df = df.tail(46000)
                            
                        # Convert index to string timestamps for continuous categorical plotting
                        df['time_str'] = df.index.strftime('%Y-%m-%d %H:%M')
                            
                        fig = go.Figure(data=[go.Candlestick(
                            x=df['time_str'],
                            open=df['open'],
                            high=df['high'],
                            low=df['low'],
                            close=df['close'],
                            increasing_line_color='#0ecb81',
                            decreasing_line_color='#f6465d'
                        )])
                        
                        fig.update_layout(
                            template="plotly_dark",
                            paper_bgcolor="#131722",
                            plot_bgcolor="#131722",
                            margin=dict(l=10, r=10, t=10, b=10),
                            height=630,
                            xaxis=dict(type='category', showgrid=False, nticks=10),
                            xaxis_rangeslider_visible=False,
                            font=dict(color="#b7bdc6", size=11)
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("Awaiting live exchange bar data...")
                except Exception as e:
                    st.error(f"Data stream error: {e}")

            render_realtime_chart(target_symbol, existing_key, existing_sec)

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
            st.warning("Configure your Alpaca keys above to execute orders.")
        else:
            try:
                base_url = "https://paper-api.alpaca.markets" if is_paper else "https://api.alpaca.markets"
                client = TradingClient(user_alpaca_key, user_alpaca_sec, paper=is_paper, url_override=base_url)
                account = client.get_account()
                
                st.markdown(f"""
                <div style="background-color: #181a20; padding: 8px; border-radius: 3px; border: 1px solid #2b313a; font-size: 11px; margin-top: 8px; margin-bottom: 8px; color: #848e9c;">
                    <b>Equity:</b> <span style="color:#eaecef;">${float(account.equity):,.2f}</span><br>
                    <b>Buying Power:</b> <span style="color:#eaecef;">${float(account.buying_power):,.2f}</span><br>
                    <b>Cash:</b> <span style="color:#eaecef;">${float(account.cash):,.2f}</span>
                </div>
                """, unsafe_allow_html=True)
                
                with st.form("order_exec_form"):
                    o_sym = st.text_input("Asset", value=target_symbol).upper()
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
                st.error(f"Connection error: Ensure your Alpaca keys match the selected mode ({account_type}). Details: {e}")

        # Watchlist
        st.markdown("""
            <div style="background-color: #1e2329; border: 1px solid #2b313a; padding: 10px; border-radius: 4px; margin-top: 15px; margin-bottom: 10px;">
                <div style="font-weight: bold; font-size: 13px; color: #eaecef;">Watchlist (Real-Time)</div>
            </div>
        """, unsafe_allow_html=True)

        watchlist_symbols = ["AAPL", "TSLA", "NVDA", "AMZN", "MSFT", "GOOGL", "CVS", "SPY", "QQQ"]
        
        @st.fragment(run_every="4s")
        def render_watchlist(symbols, a_key, a_sec):
            for sym in symbols:
                w_price, w_pct = fetch_live_quote(sym, a_key, a_sec)
                color = "#0ecb81" if w_pct >= 0 else "#f6465d"
                sign = "+" if w_pct >= 0 else ""
                
                col_w1, col_w2, col_w3 = st.columns([1.2, 1.5, 1.2])
                with col_w1:
                    if st.button(sym, key=f"wl_{sym}", use_container_width=True):
                        st.session_state.active_ticker = sym
                        st.rerun()
                with col_w2:
                    st.markdown(f"<div style='padding-top: 5px; font-size: 12px; color: #eaecef; text-align: right;'>${w_price:,.2f}</div>", unsafe_allow_html=True)
                with col_w3:
                    st.markdown(f"<div style='padding-top: 5px; font-size: 12px; color: {color}; font-weight: bold; text-align: right;'>{sign}{w_pct:.2f}%</div>", unsafe_allow_html=True)

        render_watchlist(watchlist_symbols, existing_key, existing_sec)

    # AI Assistant drawer
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
                        model="openai/gpt-oss-120b",
                        messages=[{"role": "system", "content": "You are an expert institutional trading analyst."}, {"role": "user", "content": ai_query}],
                        temperature=0.7
                    )
                    st.write(completion.choices[0].message.content)
                except Exception as e:
                    st.error(f"AI Error: {e}")
