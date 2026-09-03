import datetime
import math
import time
import xml.etree.ElementTree as ET
from groq import Groq
import numpy as np
import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components
from supabase import Client, create_client

# Try importing yfinance for market quotes and options data
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

# Page configuration - Wide mode with expanded sidebar by default
st.set_page_config(
    page_title="TB TERMINAL // Institutional Market Research & GEX",
    layout="wide",
    page_icon="📈",
    initial_sidebar_state="expanded",
)

# Session state initializations with persistent fallback
if "terminal_opened" not in st.session_state:
    st.session_state.terminal_opened = True  # Default to True to prevent accidental lockouts

if "show_splash" not in st.session_state:
    st.session_state.show_splash = False

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

# Pro Exchange True Black Theme Styling & Red Delete Button Override
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

# Robust Secret Loader for Supabase & Groq
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

def get_groq_key():
    try:
        if "GROQ_API_KEY" in st.secrets:
            return st.secrets["GROQ_API_KEY"]
        elif "groq" in st.secrets and "GROQ_API_KEY" in st.secrets["groq"]:
            return st.secrets["groq"]["GROQ_API_KEY"]
    except Exception:
        pass
    return ""

groq_key = get_groq_key()

# Load watchlist from DB into Session State if available
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
    if st.button("Lock Terminal", use_container_width=True):
        st.session_state.terminal_opened = False
        st.session_state.show_splash = False
        st.rerun()

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
except Exception:
    spy_price, spy_pct = 100.0, 0.0

try:
    qqq_price, qqq_pct, _ = fetch_live_quote("QQQ")
except Exception:
    qqq_price, qqq_pct = 100.0, 0.0

try:
    active_price, active_pct, _ = fetch_live_quote(target_symbol)
except Exception:
    active_price, active_pct = 100.0, 0.0

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
                    # Rendered purely as inert text so clicking it does absolutely nothing (no callbacks or navigation)
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
                        messages=[
                            {"role": "system", "content": "You are an expert institutional market research analyst."},
                            {"role": "user", "content": ai_query},
                        ],
                        temperature=0.7,
                    )
                    st.write(completion.choices[0].message.content)
                except Exception as e:
                    st.error(f"AI Error: {e}")

elif selected_main_tab == "⚛️ Gamma Exposure (GEX) Analysis":
    st.markdown(
        f"""
        <div style="background-color: #080808; border: 1px solid #1a1a1a; padding: 12px 18px; border-radius: 4px; margin-bottom: 15px;">
            <h3 style="margin: 0; color: #eaecef; font-size: 16px;">⚛️ Gamma Exposure (GEX) Profile // {target_symbol}</h3>
            <p style="margin: 4px 0 0 0; color: #848e9c; font-size: 12px;">Dealer options positioning, strike magnet levels, and volatility dampening/amplifying zones.</p>
        </div>
    """,
        unsafe_allow_html=True,
    )

    if not YFINANCE_AVAILABLE:
        st.error("`yfinance` is required for options chain data.")
    else:
        try:
            tk = yf.Ticker(target_symbol, session=get_yf_session())
            exp_dates = tk.options
        except Exception:
            exp_dates = []

        if not exp_dates:
            st.warning(f"No options chain expiration dates found for {target_symbol}. Ensure the ticker has listed options (e.g. SPY, AAPL, NVDA).")
        else:
            default_selections = list(exp_dates[:min(3, len(exp_dates))])
            selected_exp_dates = st.multiselect(
                "Select Option Expiration Dates for GEX Calculation:",
                options=list(exp_dates),
                default=default_selections
            )

            if not selected_exp_dates:
                st.info("Please select at least one expiration date above to generate the GEX profile.")
            else:
                if st.button("Generate GEX Profile", type="primary"):
                    with st.spinner(f"Computing Gamma Exposure profile for {target_symbol}..."):
                        try:
                            spot_price, _, _ = fetch_live_quote(target_symbol)
                            if spot_price <= 0:
                                hist = tk.history(period="1d")
                                if not hist.empty:
                                    spot_price = float(hist["Close"].iloc[-1])

                            def norm_pdf(x):
                                return (1.0 / math.sqrt(2 * math.pi)) * math.exp(-0.5 * x * x)

                            def calc_gamma(S, K, T, r, sigma):
                                if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
                                    return 0.0
                                try:
                                    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
                                    return norm_pdf(d1) / (S * sigma * math.sqrt(T))
                                except Exception:
                                    return 0.0

                            all_options_data = []
                            now = datetime.datetime.now()
                            r = 0.045

                            for exp in selected_exp_dates:
                                try:
                                    opt_chain = tk.option_chain(exp)
                                    exp_date_obj = datetime.datetime.strptime(exp, "%Y-%m-%d")
                                    T = max((exp_date_obj - now).days / 365.25, 0.001)

                                    calls = opt_chain.calls
                                    puts = opt_chain.puts

                                    for _, row in calls.iterrows():
                                        strike = float(row["strike"])
                                        oi = float(row["openInterest"]) if not pd.isna(row["openInterest"]) else 0.0
                                        iv = float(row["impliedVolatility"]) if not pd.isna(row["impliedVolatility"]) and row["impliedVolatility"] > 0 else 0.2
                                        if oi > 0:
                                            gamma = calc_gamma(spot_price, strike, T, r, iv)
                                            gex_val = gamma * oi * 100.0 * (spot_price ** 2) * 0.01 / 1e6
                                            all_options_data.append({"strike": strike, "gex": gex_val, "type": "call"})

                                    for _, row in puts.iterrows():
                                        strike = float(row["strike"])
                                        oi = float(row["openInterest"]) if not pd.isna(row["openInterest"]) else 0.0
                                        iv = float(row["impliedVolatility"]) if not pd.isna(row["impliedVolatility"]) and row["impliedVolatility"] > 0 else 0.2
                                        if oi > 0:
                                            gamma = calc_gamma(spot_price, strike, T, r, iv)
                                            gex_val = - (gamma * oi * 100.0 * (spot_price ** 2) * 0.01 / 1e6)
                                            all_options_data.append({"strike": strike, "gex": gex_val, "type": "put"})
                                except Exception:
                                    continue

                            if not all_options_data:
                                st.info("Insufficient open interest data found across the selected expiration dates.")
                            else:
                                df_gex = pd.DataFrame(all_options_data)
                                df_grouped = df_gex.groupby("strike")["gex"].sum().reset_index()

                                total_net_gex = df_grouped["gex"].sum()

                                df_grouped = df_grouped.sort_values("strike")
                                df_grouped["cum_gex"] = df_grouped["gex"].cumsum()
                                
                                zero_crossings = df_grouped[(df_grouped["cum_gex"].shift(1) * df_grouped["cum_gex"]) < 0]
                                if not zero_crossings.empty:
                                    closest_idx = (zero_crossings["strike"] - spot_price).abs().idxmin()
                                    flip_strike = float(df_grouped.loc[closest_idx, "strike"])
                                else:
                                    flip_strike = float(df_grouped.loc[(df_grouped["cum_gex"]).abs().idxmin(), "strike"])

                                st.markdown(f"""
                                    <div style="display: flex; gap: 15px; margin-bottom: 15px; flex-wrap: wrap;">
                                        <div style="background: #080808; border: 1px solid #1a1a1a; padding: 12px; border-radius: 4px; flex: 1; min-width: 200px;">
                                            <div style="color: #848e9c; font-size: 11px;">NET GAMMA EXPOSURE</div>
                                            <div style="font-size: 18px; font-weight: bold; color: {'#0ecb81' if total_net_gex >= 0 else '#f6465d'};">${total_net_gex:,.2f}B</div>
                                        </div>
                                        <div style="background: #080808; border: 1px solid #1a1a1a; padding: 12px; border-radius: 4px; flex: 1; min-width: 200px;">
                                            <div style="color: #848e9c; font-size: 11px;">GEX FLIP POINT</div>
                                            <div style="font-size: 18px; font-weight: bold; color: #f0b90b;">${flip_strike:,.2f}</div>
                                        </div>
                                        <div style="background: #080808; border: 1px solid #1a1a1a; padding: 12px; border-radius: 4px; flex: 1; min-width: 200px;">
                                            <div style="color: #848e9c; font-size: 11px;">SPOT PRICE</div>
                                            <div style="font-size: 18px; font-weight: bold; color: #eaecef;">${spot_price:,.2f}</div>
                                        </div>
                                    </div>
                                """, unsafe_allow_html=True)

                                st.bar_chart(df_grouped.set_index("strike")["gex"])
                        except Exception as ex:
                            st.error(f"Error computing GEX profile: {ex}")

elif selected_main_tab == "🎯 Optimal Contract Finder":
    st.markdown("### 🎯 Optimal Contract Finder", unsafe_allow_html=True)
    st.info("Use this module to scan option chains for high-probability directional and volatility setups.")

elif selected_main_tab == "🔄 Sector Rotation Leaderboard":
    st.markdown("### 🔄 Sector Rotation Leaderboard", unsafe_allow_html=True)
    st.info("Tracking institutional capital flows across major market sectors.")

elif selected_main_tab == "⚡ Unusual Options Activity":
    st.markdown("### ⚡ Unusual Options Activity", unsafe_allow_html=True)
    st.info("Real-time sweep and block order scanner highlighting institutional positioning.")

elif selected_main_tab == "📰 Live Trading News":
    st.markdown("### 📰 Live Trading News", unsafe_allow_html=True)
    st.info("Live market wires and macroeconomic news feeds.")
