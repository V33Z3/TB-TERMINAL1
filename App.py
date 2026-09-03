import datetime
import math
import time
import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

st.set_page_config(
    page_title="TB TERMINAL // Institutional Market Research & GEX",
    layout="wide",
    page_icon="📈",
    initial_sidebar_state="expanded",
)

if "active_ticker" not in st.session_state:
    st.session_state.active_ticker = "AAPL"

if "ticker_search_input" not in st.session_state:
    st.session_state.ticker_search_input = st.session_state.active_ticker

if "active_main_tab" not in st.session_state:
    st.session_state.active_main_tab = "📈 Terminal Chart"

if "main_nav_radio" not in st.session_state:
    st.session_state.main_nav_radio = st.session_state.active_main_tab

if "watchlist" not in st.session_state:
    st.session_state.watchlist = ["AAPL", "TSLA", "NVDA", "AMZN"]

st.markdown(
    """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    [data-testid="stHeader"] {
        background-color: transparent !important;
    }
    
    .block-container {
        padding-top: 1rem;
        padding-bottom: 0rem;
        padding-left: 0.8rem;
        padding-right: 0.8rem;
        max-width: 100% !important;
    }
    
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stSidebar"], .main { 
        background-color: #000000 !important; 
        color: #b7bdc6; 
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; 
    }
    
    [data-testid="stSidebar"] {
        background-color: #050505 !important;
        border-right: 1px solid #1a1a1a;
    }
    
    .exchange-header {
        background-color: #080808;
        border-bottom: 1px solid #1a1a1a;
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
        background-color: #0b0e11 !important;
        color: #eaecef !important;
        border: 1px solid #1f242d !important;
        border-radius: 3px !important;
        font-size: 13px !important;
        min-height: 30px !important;
    }
    </style>
""",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("### ⚙️ Research Terminal")
    st.markdown("<p style='font-size: 12px; color: #848e9c;'>Mode: <b>Market Research & GEX Analytics</b></p>", unsafe_allow_html=True)

def on_ticker_change():
    st.session_state.active_ticker = st.session_state.ticker_search_input.upper().strip()

st.text_input("Search Ticker", key="ticker_search_input", on_change=on_ticker_change, label_visibility="collapsed")

target_symbol = st.session_state.active_ticker

@st.cache_resource
def get_yf_session():
    session = requests.Session()
    session.headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    return session

@st.cache_data(ttl=15)
def fetch_live_quote(symbol):
    price, pct, vol = 100.0, 0.50, 1000000
    if YFINANCE_AVAILABLE:
        try:
            session = get_yf_session()
            t = yf.Ticker(symbol, session=session)
            hist = t.history(period="5d")
            if not hist.empty:
                yf_close = float(hist["Close"].iloc[-1])
                prev = float(hist["Close"].iloc[-2]) if len(hist) > 1 else float(hist["Open"].iloc[-1])
                vol = int(hist["Volume"].iloc[-1]) if "Volume" in hist.columns else 100000
                price = yf_close
                pct = ((price - prev) / prev) * 100 if prev > 0 else 0.0
        except Exception:
            pass
    return price, pct, vol

try:
    spy_price, spy_pct, _ = fetch_live_quote("SPY")
    qqq_price, qqq_pct, _ = fetch_live_quote("QQQ")
    active_price, active_pct, _ = fetch_live_quote(target_symbol)
except Exception:
    spy_price, spy_pct, qqq_price, qqq_pct, active_price, active_pct = 100.0, 0.0, 100.0, 0.0, 100.0, 0.0

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

st.markdown(f"""
    <div class="exchange-header">
        <div style="color: #f0b90b; font-weight: bold; font-size: 13px; margin-right: 10px;">⚡ TB TERMINAL // RESEARCH</div>
        {format_badge("SPY", spy_price, spy_pct, "#1f0c0c", "#f6465d")}
        {format_badge("QQQ", qqq_price, qqq_pct, "#1f1a0c", "#f0b90b")}
        {format_badge(f"{target_symbol} (Live)", active_price, active_pct, "#150c1f", "#9c27b0")}
    </div>
""", unsafe_allow_html=True)

def on_nav_change():
    st.session_state.active_main_tab = st.session_state.main_nav_radio

nav_options = [
    "📈 Terminal Chart",
    "⚛️ Gamma Exposure (GEX) Analysis",
    "🎯 Optimal Contract Finder",
    "🔄 Sector Rotation Leaderboard",
    "⚡ Unusual Options Activity",
    "📰 Live Trading News"
]

if st.session_state.active_main_tab not in nav_options:
    st.session_state.active_main_tab = nav_options[0]
    st.session_state.main_nav_radio = nav_options[0]

selected_main_tab = st.radio(
    "Navigation", 
    options=nav_options, 
    key="main_nav_radio",
    on_change=on_nav_change,
    horizontal=True, 
    label_visibility="collapsed"
)
st.session_state.active_main_tab = selected_main_tab
st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)

if selected_main_tab == "📈 Terminal Chart":
    col_chart, col_wl = st.columns([3, 1])

    with col_chart:
        st.markdown(
            f"""
            <div style="background-color: #080808; border: 1px solid #1a1a1a; padding: 6px 12px; border-radius: 4px; margin-bottom: 5px; display: flex; justify-content: space-between; align-items: center;">
                <span style="font-weight: bold; font-size: 13px; color: #eaecef;">📊 TradingView Advanced Chart // {target_symbol}</span>
                <span style="font-size: 11px; color: #0ecb81; background: rgba(14,203,129,0.1); padding: 2px 6px; border-radius: 3px;">● RESEARCH FEED</span>
            </div>
        """,
            unsafe_allow_html=True,
        )

        tv_html = f"""
        <div class="tradingview-widget-container" style="height:680px;width:100%">
          <div class="tradingview-widget-container__widget" style="height:100%;width:100%"></div>
          <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" async>
          {{
            "autosize": false,
            "width": "100%",
            "height": "680",
            "symbol": "{target_symbol}",
            "interval": "D",
            "timezone": "Etc/UTC",
            "theme": "dark",
            "style": "1",
            "locale": "en",
            "enable_publishing": false,
            "allow_symbol_change": true,
            "calendar": false,
            "support_host": "https://www.tradingview.com",
            "isTransparent": true,
            "hide_side_toolbar": false
          }}
          </script>
        </div>
        """
        components.html(tv_html, height=690)

    with col_wl:
        @st.fragment
        def render_persistent_watchlist():
            st.markdown("### Persistent Custom Watchlist")
            
            new_ticker = st.text_input("Add Ticker", placeholder="e.g. AAPL, BTCUSD", key="add_watchlist_input", label_visibility="collapsed")
            if st.button("+ Add", use_container_width=True, key="add_watchlist_btn"):
                if new_ticker:
                    syms = [s.strip().upper() for s in new_ticker.split(",") if s.strip()]
                    for s in syms:
                        if s not in st.session_state.watchlist:
                            st.session_state.watchlist.append(s)
                    st.rerun()

            st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)

            for symbol in st.session_state.watchlist:
                p, pct, vol = fetch_live_quote(symbol)
                color = "#0ecb81" if pct >= 0 else "#f6465d"
                sign = "+" if pct >= 0 else ""
                
                w_col1, w_col2, w_col3 = st.columns([2, 2, 1])
                with w_col1:
                    if st.button(symbol, key=f"wl_btn_{symbol}", use_container_width=True):
                        st.session_state.active_ticker = symbol
                with w_col2:
                    st.markdown(f"<div style='font-size: 11px; text-align: right; color: #eaecef;'>${p:,.2f}<br><span style='color: {color};'>{sign}{pct:.2f}%</span></div>", unsafe_allow_html=True)
                with w_col3:
                    if st.button("🗑️", key=f"wl_del_{symbol}"):
                        st.session_state.watchlist = [s for s in st.session_state.watchlist if s != symbol]
                        st.rerun()

        render_persistent_watchlist()

elif selected_main_tab == "⚛️ Gamma Exposure (GEX) Analysis":
    st.markdown("### ⚛️ Gamma Exposure (GEX) Analysis", unsafe_allow_html=True)
    st.info("Gamma exposure metrics and dealer positioning profiles.")

elif selected_main_tab == "🎯 Optimal Contract Finder":
    st.markdown("### 🎯 Optimal Contract Finder", unsafe_allow_html=True)

elif selected_main_tab == "🔄 Sector Rotation Leaderboard":
    st.markdown("### 🔄 Sector Rotation Leaderboard", unsafe_allow_html=True)

elif selected_main_tab == "⚡ Unusual Options Activity":
    st.markdown("### ⚡ Unusual Options Activity", unsafe_allow_html=True)

elif selected_main_tab == "📰 Live Trading News":
    st.markdown("### 📰 Live Trading News", unsafe_allow_html=True)
