import datetime
import math
import time
import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components
from supabase import Client, create_client

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

# Initialize persistent session states (No splash screen, no home page redirection)
if "active_ticker" not in st.session_state:
    st.session_state.active_ticker = "AAPL"

if "ticker_search_input" not in st.session_state:
    st.session_state.ticker_search_input = st.session_state.active_ticker

if "watchlist" not in st.session_state:
    st.session_state.watchlist = ["AAPL", "TSLA", "NVDA", "AMZN", "MSFT", "GOOGL", "SPY", "QQQ"]

if "active_main_tab" not in st.session_state:
    st.session_state.active_main_tab = "📈 Terminal Chart & Watchlist"

if "main_nav_radio" not in st.session_state:
    st.session_state.main_nav_radio = st.session_state.active_main_tab

# Pro Exchange True Black Theme Styling
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

    .delete-btn button {
        background-color: rgba(246, 70, 93, 0.1) !important;
        color: #f6465d !important;
        border: 1px solid rgba(246, 70, 93, 0.3) !important;
    }
    .delete-btn button:hover {
        background-color: rgba(246, 70, 93, 0.25) !important;
        border-color: #f6465d !important;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# Supabase Secret Loader
@st.cache_resource
def init_supabase():
    url = ""
    key = ""
    try:
        if "SUPABASE_URL" in st.secrets:
            url = st.secrets["SUPABASE_URL"]
        elif "supabase" in st.secrets and "SUPABASE_URL" in st.secrets["supabase"]:
            url = st.secrets["supabase"]["SUPABASE_URL"]

        if "SUPABASE_KEY" in st.secrets:
            key = st.secrets["SUPABASE_KEY"]
        elif "SUPABASE_SECRET_KEY" in st.secrets:
            key = st.secrets["SUPABASE_SECRET_KEY"]
        elif "supabase" in st.secrets and "SUPABASE_KEY" in st.secrets["supabase"]:
            key = st.secrets["supabase"]["SUPABASE_KEY"]
        elif "supabase" in st.secrets and "SUPABASE_SECRET_KEY" in st.secrets["supabase"]:
            key = st.secrets["supabase"]["SUPABASE_SECRET_KEY"]
    except Exception:
        pass

    if url and key:
        try:
            return create_client(url, key)
        except Exception:
            return None
    return None

supabase = init_supabase()

# Load Watchlist from DB
try:
    if supabase:
        wl_res = supabase.table("user_watchlists").select("symbols").eq("user_id", "guest_terminal_user").execute()
        if wl_res.data and len(wl_res.data) > 0 and wl_res.data[0].get("symbols"):
            st.session_state.watchlist = wl_res.data[0].get("symbols")
except Exception:
    pass

def save_watchlist_to_db():
    try:
        if supabase:
            supabase.table("user_watchlists").upsert(
                {"user_id": "guest_terminal_user", "symbols": st.session_state.watchlist}
            ).execute()
    except Exception:
        pass

with st.sidebar:
    st.markdown("### ⚙️ Research Terminal")
    st.markdown("<p style='font-size: 12px; color: #848e9c;'>Mode: <b>Market Research & GEX Analytics</b></p>", unsafe_allow_html=True)

# Ticker Search Input Row
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

fn_format_vol = lambda v: f"{v/1e9:.2f}B" if v >= 1e9 else (f"{v/1e6:.2f}M" if v >= 1e6 else (f"{v/1e3:.1f}K" if v >= 1e3 else str(v)))

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
    "📈 Terminal Chart & Watchlist",
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

if selected_main_tab == "📈 Terminal Chart & Watchlist":
    col_chart, col_research = st.columns([3.4, 1.2])

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
        <div class="tradingview-widget-container" style="height:630px;width:100%">
          <div class="tradingview-widget-container__widget" style="height:100%;width:100%"></div>
          <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" async>
          {{
            "autosize": false,
            "width": "100%",
            "height": "630",
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
        components.html(tv_html, height=640)

    with col_research:
        st.markdown(
            """
            <div style="background-color: #080808; border: 1px solid #1a1a1a; padding: 10px; border-radius: 4px; margin-bottom: 5px;">
                <div style="font-weight: bold; font-size: 13px; color: #eaecef;">Persistent Custom Watchlist</div>
            </div>
        """,
            unsafe_allow_html=True,
        )

        with st.form("add_watchlist_form", clear_on_submit=True):
            col_w1, col_w2 = st.columns([3, 1])
            with col_w1:
                new_ticker_input = st.text_input("Add Ticker", placeholder="e.g. AAPL, BTCUSD", label_visibility="collapsed")
            with col_w2:
                add_btn = st.form_submit_button("＋ Add", use_container_width=True)

            if add_btn and new_ticker_input.strip():
                clean_sym = new_ticker_input.upper().strip()
                if clean_sym not in st.session_state.watchlist:
                    st.session_state.watchlist.append(clean_sym)
                    save_watchlist_to_db()
                    st.rerun()

        st.markdown("<div style='background: #050505; border: 1px solid #1a1a1a; border-radius: 4px; padding: 8px; max-height: 510px; overflow-y: auto;'>", unsafe_allow_html=True)
        if not st.session_state.watchlist:
            st.markdown("<div style='color: #848e9c; font-size: 12px; text-align: center; padding: 10px;'>Watchlist is empty. Add symbols above.</div>", unsafe_allow_html=True)
        else:
            for sym in list(st.session_state.watchlist):
                try:
                    p_val, p_pct, p_vol = fetch_live_quote(sym)
                except Exception:
                    p_val, p_pct, p_vol = 0.0, 0.0, 0

                color = "#0ecb81" if p_pct >= 0 else "#f6465d"
                sign = "+" if p_pct >= 0 else ""
                vol_str = fn_format_vol(p_vol) if p_vol > 0 else "-"

                w_col_info, w_col_vol, w_col_price, w_col_del = st.columns([2.2, 1.4, 1.8, 1.0])
                with w_col_info:
                    st.markdown(f"<div style='font-size: 13px; font-weight: bold; color: #eaecef; padding-top: 8px; pointer-events: none; user-select: none;'>{sym}</div>", unsafe_allow_html=True)
                with w_col_vol:
                    st.markdown(f"<div style='font-size: 13px; color: #eaecef; padding-top: 8px; pointer-events: none; user-select: none;'>{vol_str}</div>", unsafe_allow_html=True)
                with w_col_price:
                    st.markdown(f"<div style='font-size: 11px; text-align: right; padding-top: 6px; color: {color}; pointer-events: none; user-select: none;'>${p_val:,.2f}<br><b>{sign}{p_pct:.2f}%</b></div>", unsafe_allow_html=True)
                with w_col_del:
                    st.markdown('<div class="delete-btn">', unsafe_allow_html=True)
                    if st.button("🗑️", key=f"btn_del_{sym}", use_container_width=True):
                        st.session_state.watchlist.remove(sym)
                        save_watchlist_to_db()
                        st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

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
