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

# Map tabs to short query param codes (including Live Trading News with Trump feed option)
tab_to_param = {
    "📈 Terminal Chart & Watchlist": "chart",
    "⚛️ Gamma Exposure (GEX) Analysis": "gex",
    "🎯 Optimal Contract Finder": "finder",
    "🔄 Sector Rotation Leaderboard": "sectors",
    "⚡ Unusual Options Activity": "uoa",
    "📰 Live Trading News": "news"
}
param_to_tab = {v: k for k, v in tab_to_param.items()}

# Handle Ticker from Query Parameters
if "ticker" in st.query_params:
    st.session_state.active_ticker = st.query_params["ticker"].upper().strip()

# Handle Tab Query Parameters without overriding manual clicks
if "tab" in st.query_params:
    tab_param = st.query_params["tab"].lower()
    if tab_param in param_to_tab:
        expected_tab = param_to_tab[tab_param]
        if st.session_state.get("active_main_tab") != expected_tab:
            st.session_state.active_main_tab = expected_tab
            st.session_state.main_nav_radio = expected_tab

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
        return create_client(url, key)
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

# Session state initializations
if "user" not in st.session_state:
    st.session_state.user = None
if "show_splash" not in st.session_state:
    st.session_state.show_splash = False
if "active_ticker" not in st.session_state:
    st.session_state.active_ticker = "AAPL"
if "watchlist" not in st.session_state:
    st.session_state.watchlist = ["AAPL", "TSLA", "NVDA", "AMZN", "MSFT", "GOOGL", "SPY", "QQQ"]
if "active_main_tab" not in st.session_state:
    st.session_state.active_main_tab = "📈 Terminal Chart & Watchlist"
if "main_nav_radio" not in st.session_state:
    st.session_state.main_nav_radio = st.session_state.active_main_tab

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
    if st.session_state.show_splash:
        components.html(
            """
            <div style="background: #000000; height: 100vh; display: flex; flex-direction: column; justify-content: center; align-items: center; color: #eaecef; font-family: -apple-system, sans-serif; overflow: hidden;">
                <div style="text-align: center; width: 100%; max-width: 950px; padding: 0 20px;">
                    <div style="font-size: 48px; font-weight: bold; color: #f0b90b; letter-spacing: 3px; margin-bottom: 12px;">⚡ TB TERMINAL</div>
                    <p style="color: #848e9c; font-size: 16px; font-family: monospace; letter-spacing: 2px; margin-bottom: 35px;">LOADING QUANT RESEARCH SUITE & GEX MODULE...</p>
                </div>
            </div>
            """,
            height=300,
        )
        time.sleep(1.2)
        st.session_state.show_splash = False
        st.rerun()

    # Load watchlist from DB into Session State if empty
    try:
        wl_res = supabase.table("user_watchlists").select("symbols").eq("user_id", st.session_state.user.id).execute()
        if wl_res.data and len(wl_res.data) > 0 and wl_res.data[0].get("symbols"):
            st.session_state.watchlist = wl_res.data[0].get("symbols")
    except Exception:
        pass

    def save_watchlist_to_db():
        try:
            supabase.table("user_watchlists").upsert(
                {"user_id": st.session_state.user.id, "symbols": st.session_state.watchlist}
            ).execute()
        except Exception:
            pass

    with st.sidebar:
        st.markdown("### ⚙️ Research Terminal")
        st.markdown("<p style='font-size: 12px; color: #848e9c;'>Mode: <b>Market Research & GEX Analytics</b></p>", unsafe_allow_html=True)
        if st.button("Log Out", use_container_width=True):
            supabase.auth.sign_out()
            st.session_state.user = None
            st.rerun()

    # Ticker Search Input Row
    def on_ticker_change():
        st.session_state.active_ticker = st.session_state.ticker_search_input.upper().strip()
    st.text_input("Search Ticker", value=st.session_state.active_ticker, key="ticker_search_input", on_change=on_ticker_change, label_visibility="collapsed")

    target_symbol = st.session_state.active_ticker

    @st.cache_resource
    def get_yf_session():
        session = requests.Session()
        session.headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        return session

    @st.cache_data(ttl=10)
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

    def format_vol(v):
        if v >= 1e9: return f"{v/1e9:.2f}B"
        elif v >= 1e6: return f"{v/1e6:.2f}M"
        elif v >= 1e3: return f"{v/1e3:.1f}K"
        return str(v)

    # Header display ticker badges & TB TERMINAL TITLE on the top green bar line
    spy_price, spy_pct, _ = fetch_live_quote("SPY")
    qqq_price, qqq_pct, _ = fetch_live_quote("QQQ")
    active_price, active_pct, _ = fetch_live_quote(target_symbol)

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

    # NAVIGATION CALLBACK TO SYNC STATE AND URL QUERY PARAMS
    def on_nav_change():
        selected = st.session_state.main_nav_radio
        st.session_state.active_main_tab = selected
        if selected in tab_to_param:
            st.query_params["tab"] = tab_to_param[selected]

    nav_options = list(tab_to_param.keys())
    
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
                    p_val, p_pct, p_vol = fetch_live_quote(sym)
                    color = "#0ecb81" if p_pct >= 0 else "#f6465d"
                    sign = "+" if p_pct >= 0 else ""
                    logo_url = f"https://assets.parqet.com/logos/symbol/{sym}"
                    vol_str = format_vol(p_vol) if p_vol > 0 else "-"

                    w_col_info, w_col_vol, w_col_price, w_col_del = st.columns([2.2, 1.4, 1.8, 1.0])
                    with w_col_info:
                        st.markdown(
                            f"""
                            <a href="?ticker={sym}&tab=chart" target="_self" style="text-decoration: none; display: flex; align-items: center; gap: 8px; padding-top: 4px;">
                                <img src="{logo_url}" width="24" height="24" style="border-radius:50%; object-fit:contain; background:#222;" onerror="this.onerror=null;this.src='https://ui-avatars.com/api/?name={sym}&background=333333&color=ffffff&size=64';">
                                <span style="font-weight: bold; font-size: 13px; color: #eaecef;">{sym}</span>
                            </a>
                            """,
                            unsafe_allow_html=True,
                        )
                    with w_col_vol:
                        st.markdown(f"<div style='font-size: 13px; color: #eaecef; padding-top: 4px;'>{vol_str}</div>", unsafe_allow_html=True)
                    with w_col_price:
                        st.markdown(f"<div style='font-size: 11px; text-align: right; padding-top: 3px; color: {color};'>${p_val:,.2f}<br><b>{sign}{p_pct:.2f}%</b></div>", unsafe_allow_html=True)
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
            except Exception as e:
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

                                    df_filtered = df_grouped[(df_grouped["strike"] >= spot_price * 0.75) & (df_grouped["strike"] <= spot_price * 1.25)]

                                    total_net_gex = df_grouped["gex"].sum()

                                    df_grouped = df_grouped.sort_values("strike")
                                    df_grouped["cum_gex"] = df_grouped["gex"].cumsum()
                                    
                                    flip_strike = spot_price
                                    zero_crossings = df_grouped[(df_grouped["cum_gex"].shift(1) * df_grouped["cum_gex"]) < 0]
                                    if not zero_crossings.empty:
                                        closest_idx = (zero_crossings["strike"] - spot_price).abs().idxmin()
                                        flip_strike = zero_crossings.loc[closest_idx, "strike"]

                                    m1, m2, m3, m4 = st.columns(4)
                                    with m1:
                                        st.metric("Underlying Spot Price", f"${spot_price:,.2f}")
                                    with m2:
                                        gex_color_label = "Positive (Mean Reverting)" if total_net_gex > 0 else "Negative (High Volatility)"
                                        st.metric("Total Net GEX", f"${total_net_gex:,.2f}M", delta=gex_color_label)
                                    with m3:
                                        st.metric("Gamma Flip Point", f"${flip_strike:,.2f}")
                                    with m4:
                                        st.metric("Expirations Selected", f"{len(selected_exp_dates)}")

                                    st.markdown("<br>", unsafe_allow_html=True)

                                    import altair as alt

                                    df_filtered["color"] = np.where(df_filtered["gex"] >= 0, "#0ecb81", "#f6465d")

                                    chart = alt.Chart(df_filtered).mark_bar().encode(
                                        y=alt.Y("strike:O", title="Strike Price ($)", sort="descending"),
                                        x=alt.X("gex:Q", title="Gamma Exposure ($ Millions per 1% Move)"),
                                        color=alt.Color("color:N", scale=None),
                                        tooltip=["strike", "gex"]
                                    ).properties(
                                        height=650,
                                        background="#080808"
                                    ).configure_view(
                                        strokeWidth=0
                                    ).configure_axis(
                                        gridColor="#1a1a1a",
                                        domainColor="#333333",
                                        labelColor="#848e9c",
                                        titleColor="#eaecef"
                                    )

                                    st.altair_chart(chart, use_container_width=True)
                            except Exception as e:
                                st.error(f"Error computing Gamma Exposure: {e}")

    elif selected_main_tab == "🎯 Optimal Contract Finder":
        st.markdown(
            f"""
            <div style="background-color: #080808; border: 1px solid #1a1a1a; padding: 12px 18px; border-radius: 4px; margin-bottom: 15px;">
                <h3 style="margin: 0; color: #eaecef; font-size: 16px;">🎯 Contract Selection // {target_symbol}</h3>
                <p style="margin: 4px 0 0 0; color: #848e9c; font-size: 12px;">Automatically analyzes the options chain to identify and rank the highest-conviction Call and Put contracts.</p>
            </div>
        """,
            unsafe_allow_html=True,
        )

        if not YFINANCE_AVAILABLE:
            st.error("`yfinance` is required for options chain data.")
        else:
            try:
                tk_finder = yf.Ticker(target_symbol, session=get_yf_session())
                finder_exp_dates = tk_finder.options
            except Exception as e:
                finder_exp_dates = []

            if not finder_exp_dates:
                st.warning(f"No option expiration dates found for {target_symbol}.")
            else:
                f_col1, f_col2 = st.columns([2, 2])
                with f_col1:
                    selected_finder_exp = st.selectbox("Select Expiration Date", options=list(finder_exp_dates), key="finder_exp_select")
                with f_col2:
                    st.markdown("<br>", unsafe_allow_html=True)
                    scan_triggered = st.button("⚡ Run Contract Selection", use_container_width=True, type="primary")

                if scan_triggered or "finder_scanned" in st.session_state:
                    st.session_state.finder_scanned = True
                    with st.spinner(f"Evaluating optimal contracts for {target_symbol} ({selected_finder_exp})..."):
                        try:
                            spot_price, _, _ = fetch_live_quote(target_symbol)
                            if spot_price <= 0:
                                hist = tk_finder.history(period="1d")
                                if not hist.empty:
                                    spot_price = float(hist["Close"].iloc[-1])

                            opt_chain = tk_finder.option_chain(selected_finder_exp)
                            now = datetime.datetime.now()
                            exp_dt = datetime.datetime.strptime(selected_finder_exp, "%Y-%m-%d")
                            T = max((exp_dt - now).days / 365.25, 0.001)
                            r = 0.045

                            def norm_cdf(x):
                                return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0

                            def evaluate_contracts(df_chain, opt_type):
                                scored_contracts = []
                                for _, row in df_chain.iterrows():
                                    strike = float(row["strike"])
                                    bid = float(row["bid"]) if not pd.isna(row["bid"]) else 0.0
                                    ask = float(row["ask"]) if not pd.isna(row["ask"]) else 0.0
                                    last = float(row["lastPrice"]) if not pd.isna(row["lastPrice"]) else 0.0
                                    volume = float(row["volume"]) if not pd.isna(row["volume"]) else 0.0
                                    oi = float(row["openInterest"]) if not pd.isna(row["openInterest"]) else 0.0
                                    iv = float(row["impliedVolatility"]) if not pd.isna(row["impliedVolatility"]) and row["impliedVolatility"] > 0 else 0.2
                                    
                                    if iv <= 0 or spot_price <= 0:
                                        continue
                                        
                                    d1 = (math.log(spot_price / strike) + (r + 0.5 * iv**2) * T) / (iv * math.sqrt(T))
                                    delta = norm_cdf(d1) if opt_type == "call" else norm_cdf(d1) - 1.0
                                        
                                    abs_delta = abs(delta)
                                    if 0.30 <= abs_delta <= 0.60:
                                        spread = ask - bid if ask >= bid else 0.0
                                        mid_price = (bid + ask) / 2 if (bid > 0 and ask > 0) else last
                                        spread_pct = (spread / mid_price) if mid_price > 0 else 1.0
                                        
                                        liquidity_score = volume * 1.5 + oi * 0.5
                                        spread_penalty = max(0.0, 1.0 - spread_pct * 2)
                                        score = liquidity_score * spread_penalty
                                        
                                        scored_contracts.append({
                                            "Contract": row["contractSymbol"],
                                            "Type": opt_type.upper(),
                                            "Strike": strike,
                                            "Bid": bid,
                                            "Ask": ask,
                                            "Last": last,
                                            "Volume": int(volume),
                                            "Open Interest": int(oi),
                                            "IV": f"{iv*100:.1f}%",
                                            "Delta": round(delta, 2),
                                            "Score": score
                                        })
                                        
                                df_res = pd.DataFrame(scored_contracts)
                                if not df_res.empty:
                                    df_res = df_res.sort_values(by="Score", ascending=False).head(5)
                                return df_res

                            calls_df = evaluate_contracts(opt_chain.calls, "call")
                            puts_df = evaluate_contracts(opt_chain.puts, "put")
                            
                            col_c1, col_c2 = st.columns(2)
                            with col_c1:
                                st.markdown("#### 🔥 Top Ranked Call Contracts")
                                if not calls_df.empty:
                                    st.dataframe(calls_df.drop(columns=["Score"]), use_container_width=True, hide_index=True)
                                else:
                                    st.info("No call contracts met the optimal delta and liquidity criteria.")
                                    
                            with col_c2:
                                st.markdown("#### 🩸 Top Ranked Put Contracts")
                                if not puts_df.empty:
                                    st.dataframe(puts_df.drop(columns=["Score"]), use_container_width=True, hide_index=True)
                                else:
                                    st.info("No put contracts met the optimal delta and liquidity criteria.")
                        except Exception as e:
                            st.error(f"Error scanning options contracts: {e}")

    elif selected_main_tab == "🔄 Sector Rotation Leaderboard":
        @st.fragment(run_every=15)
        def render_sector_rotation():
            st.markdown(
                """
                <div style="background-color: #080808; border: 1px solid #1a1a1a; padding: 12px 18px; border-radius: 4px; margin-bottom: 15px;">
                    <h3 style="margin: 0; color: #eaecef; font-size: 16px;">🔄 All 11 GICS Sectors Performance Leaderboard</h3>
                    <p style="margin: 4px 0 0 0; color: #848e9c; font-size: 12px;">Ranked live from best to worst performing sector. Auto-updates every 15 seconds. Click any constituent stock to inspect it on the terminal chart.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            sectors_master = {
                "Technology (XLK)": {
                    "etf": "XLK",
                    "constituents": [{"ticker": "AAPL", "price": 225.50}, {"ticker": "MSFT", "price": 440.20}, {"ticker": "NVDA", "price": 128.40}, {"ticker": "AVGO", "price": 165.20}, {"ticker": "CRM", "price": 265.40}]
                },
                "Financials (XLF)": {
                    "etf": "XLF",
                    "constituents": [{"ticker": "JPM", "price": 210.30}, {"ticker": "BAC", "price": 39.40}, {"ticker": "WFC", "price": 58.20}, {"ticker": "GS", "price": 475.10}, {"ticker": "MS", "price": 102.50}]
                },
                "Energy (XLE)": {
                    "etf": "XLE",
                    "constituents": [{"ticker": "XOM", "price": 116.80}, {"ticker": "CVX", "price": 152.70}, {"ticker": "COP", "price": 114.15}, {"ticker": "SLB", "price": 45.93}, {"ticker": "OXY", "price": 61.01}]
                },
                "Healthcare (XLV)": {
                    "etf": "XLV",
                    "constituents": [{"ticker": "LLY", "price": 950.20}, {"ticker": "UNH", "price": 560.10}, {"ticker": "JNJ", "price": 160.40}, {"ticker": "MRK", "price": 125.30}, {"ticker": "ABBV", "price": 185.60}]
                },
                "Consumer Discretionary (XLY)": {
                    "etf": "XLY",
                    "constituents": [{"ticker": "AMZN", "price": 185.20}, {"ticker": "TSLA", "price": 220.40}, {"ticker": "HD", "price": 385.10}, {"ticker": "NKE", "price": 85.30}, {"ticker": "MCD", "price": 290.10}]
                },
                "Consumer Staples (XLP)": {
                    "etf": "XLP",
                    "constituents": [{"ticker": "WMT", "price": 75.40}, {"ticker": "PG", "price": 170.20}, {"ticker": "COST", "price": 880.50}, {"ticker": "KO", "price": 68.40}, {"ticker": "PEP", "price": 175.20}]
                },
                "Industrials (XLI)": {
                    "etf": "XLI",
                    "constituents": [{"ticker": "GE", "price": 175.40}, {"ticker": "CAT", "price": 360.20}, {"ticker": "RTX", "price": 110.50}, {"ticker": "UNP", "price": 245.30}, {"ticker": "HON", "price": 210.10}]
                },
                "Utilities (XLU)": {
                    "etf": "XLU",
                    "constituents": [{"ticker": "NEE", "price": 80.40}, {"ticker": "SO", "price": 85.20}, {"ticker": "DUK", "price": 105.10}, {"ticker": "SRE", "price": 82.30}, {"ticker": "AEP", "price": 98.40}]
                },
                "Materials (XLB)": {
                    "etf": "XLB",
                    "constituents": [{"ticker": "LIN", "price": 460.20}, {"ticker": "SHW", "price": 350.40}, {"ticker": "FCX", "price": 48.20}, {"ticker": "APD", "price": 305.10}, {"ticker": "NEM", "price": 52.40}]
                },
                "Real Estate (XLRE)": {
                    "etf": "XLRE",
                    "constituents": [{"ticker": "PLD", "price": 125.40}, {"ticker": "AMT", "price": 220.50}, {"ticker": "EQIX", "price": 890.10}, {"ticker": "CCI", "price": 115.20}, {"ticker": "PSA", "price": 330.40}]
                },
                "Communication Services (XLC)": {
                    "etf": "XLC",
                    "constituents": [{"ticker": "GOOGL", "price": 178.10}, {"ticker": "META", "price": 510.40}, {"ticker": "NFLX", "price": 680.20}, {"ticker": "DIS", "price": 95.40}, {"ticker": "CMCSA", "price": 41.20}]
                }
            }

            sector_performance_list = []
            for sec_name, data in sectors_master.items():
                etf_sym = data["etf"]
                price, pct, _ = fetch_live_quote(etf_sym)
                sector_performance_list.append({
                    "Sector": sec_name,
                    "ETF": etf_sym,
                    "Price": price,
                    "Change": pct,
                    "constituents": data["constituents"]
                })

            sector_performance_list = sorted(sector_performance_list, key=lambda x: x["Change"], reverse=True)

            st.markdown("#### 🏆 Sector Performance Ranking (Best to Worst)")
            
            l_col1, l_col2, l_col3, l_col4 = st.columns([3, 1.5, 2, 2])
            with l_col1:
                st.markdown("<b>Sector Name</b>", unsafe_allow_html=True)
            with l_col2:
                st.markdown("<b>ETF Ticker</b>", unsafe_allow_html=True)
            with l_col3:
                st.markdown("<b>ETF Price</b>", unsafe_allow_html=True)
            with l_col4:
                st.markdown("<b>Performance</b>", unsafe_allow_html=True)
            st.divider()

            selected_sector_to_inspect = st.selectbox(
                "Select Sector to View Top Constituents & Stocks", 
                options=[s["Sector"] for s in sector_performance_list],
                key="sector_drilldown_select"
            )

            for s_item in sector_performance_list:
                sec_name = s_item["Sector"]
                etf_sym = s_item["ETF"]
                price = s_item["Price"]
                pct = s_item["Change"]
                color = "#0ecb81" if pct >= 0 else "#f6465d"
                sign = "+" if pct >= 0 else ""

                r_col1, r_col2, r_col3, r_col4 = st.columns([3, 1.5, 2, 2])
                with r_col1:
                    st.markdown(f"<b>{sec_name}</b>", unsafe_allow_html=True)
                with r_col2:
                    st.markdown(f"<code>{etf_sym}</code>", unsafe_allow_html=True)
                with r_col3:
                    st.markdown(f"${price:,.2f}", unsafe_allow_html=True)
                with r_col4:
                    st.markdown(f"<span style='color: {color}; font-weight: bold;'>{sign}{pct:.2f}%</span>", unsafe_allow_html=True)

            st.markdown("<br><hr>", unsafe_allow_html=True)

            active_sec_data = next((s for s in sector_performance_list if s["Sector"] == selected_sector_to_inspect), sector_performance_list[0])
            st.markdown(f"#### Top Constituents: {active_sec_data['Sector']}")

            for item in active_sec_data["constituents"]:
                sym = item["ticker"]
                p_val, p_pct, _ = fetch_live_quote(sym)
                if p_val <= 0:
                    p_val = item["price"]
                    
                color = "#0ecb81" if p_pct >= 0 else "#f6465d"
                sign = "+" if p_pct >= 0 else ""

                col_sec1, col_sec2, col_sec3, col_sec4 = st.columns([1.5, 2, 2, 2])
                with col_sec1:
                    st.markdown(
                        f"""
                        <a href="?ticker={sym}&tab=chart" target="_self" style="text-decoration: none; font-weight: bold; color: #f0b90b; font-size: 14px;">
                            ⚡ {sym}
                        </a>
                        """, 
                        unsafe_allow_html=True
                    )
                with col_sec2:
                    st.write(f"${p_val:,.2f}")
                with col_sec3:
                    st.markdown(f"<span style='color: {color}; font-weight: bold;'>{sign}{p_pct:.2f}%</span>", unsafe_allow_html=True)
                with col_sec4:
                    if st.button("Open Terminal Chart", key=f"btn_sector_term_{sym}", use_container_width=True):
                        st.session_state.active_ticker = sym
                        st.session_state.active_main_tab = "📈 Terminal Chart & Watchlist"
                        st.query_params.clear()
                        st.query_params["ticker"] = sym
                        st.query_params["tab"] = "chart"
                        st.rerun()
                st.divider()

        render_sector_rotation()

    elif selected_main_tab == "⚡ Unusual Options Activity":
        st.markdown(
            f"""
            <div style="background-color: #080808; border: 1px solid #1a1a1a; padding: 12px 18px; border-radius: 4px; margin-bottom: 15px;">
                <h3 style="margin: 0; color: #eaecef; font-size: 16px;">⚡ S&P 500 Unusual Options Activity (UOA) Scanner</h3>
                <p style="margin: 4px 0 0 0; color: #848e9c; font-size: 12px;">Scans option chains across the S&P 500 universe for volume/OI anomalies.</p>
            </div>
        """,
            unsafe_allow_html=True,
        )

        if not YFINANCE_AVAILABLE:
            st.error("`yfinance` is required for options chain data.")
        else:
            scan_col1, scan_col2, scan_col3 = st.columns([2, 1, 1])
            with scan_col1:
                scan_scope = st.radio("Scan Universe", options=["Custom Watchlist", "S&P 500 Universe"], horizontal=True)
            with scan_col2:
                min_vol_filter = st.slider("Min Daily Volume", min_value=50, max_value=2000, value=200, step=50)
            with scan_col3:
                max_results = st.slider("Top Results Limit", min_value=10, max_value=100, value=25, step=5)

            if st.button("Run S&P 500 UOA Scan", type="primary", use_container_width=True):
                @st.cache_data(ttl=86400)
                def get_sp500_symbols():
                    try:
                        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
                        tables = pd.read_html(url)
                        df = tables[0]
                        symbols = df["Symbol"].tolist()
                        return [str(s).replace(".", "-") for s in symbols]
                    except Exception:
                        return ["SPY", "QQQ", "AAPL", "NVDA", "TSLA", "AMZN", "MSFT", "META", "GOOGL", "AMD"]

                if scan_scope == "Custom Watchlist":
                    symbols_to_scan = st.session_state.get("watchlist", ["SPY", "QQQ"])
                else:
                    symbols_to_scan = get_sp500_symbols()

                uoa_results = []
                progress_bar = st.progress(0)
                status_text = st.empty()
                total_symbols = len(symbols_to_scan)

                for idx, sym in enumerate(symbols_to_scan):
                    status_text.text(f"Scanning ({idx+1}/{total_symbols}): {sym}...")
                    progress_bar.progress((idx + 1) / total_symbols)
                    try:
                        tk = yf.Ticker(sym, session=get_yf_session())
                        exp_dates = tk.options
                        if not exp_dates:
                            continue
                        
                        for exp in exp_dates[:1]:
                            opt_chain = tk.option_chain(exp)
                            for opt_type, df in [("CALL", opt_chain.calls), ("PUT", opt_chain.puts)]:
                                if df.empty:
                                    continue
                                active = df[(df["volume"] > df["openInterest"]) & (df["volume"] > min_vol_filter)]
                                for _, row in active.iterrows():
                                    vol = float(row["volume"]) if not pd.isna(row["volume"]) else 0.0
                                    oi = float(row["openInterest"]) if not pd.isna(row["openInterest"]) else 1.0
                                    ratio = round(vol / max(oi, 1), 2)
                                    iv = float(row["impliedVolatility"]) if not pd.isna(row["impliedVolatility"]) else 0.0
                                    
                                    uoa_results.append({
                                        "Ticker": sym,
                                        "Type": opt_type,
                                        "Strike": float(row["strike"]),
                                        "Expiry": exp,
                                        "Volume": int(vol),
                                        "Open Interest": int(oi),
                                        "Vol/OI Ratio": ratio,
                                        "Last Price": float(row["lastPrice"]) if not pd.isna(row["lastPrice"]) else 0.0,
                                        "IV": f"{iv*100:.1f}%"
                                    })
                    except Exception:
                        continue

                progress_bar.empty()
                status_text.empty()

                if not uoa_results:
                    st.info("No unusual options activity detected matching criteria across the selected universe.")
                else:
                    df_uoa = pd.DataFrame(uoa_results)
                    df_uoa = df_uoa.sort_values(by="Vol/OI Ratio", ascending=False).drop_duplicates(subset=["Ticker", "Type", "Strike", "Expiry"])
                    df_uoa = df_uoa.head(max_results)
                    st.success(f"Scan complete! Showing top {len(df_uoa)} most unusual options contracts.")
                    st.dataframe(df_uoa, use_container_width=True, hide_index=True)

    elif selected_main_tab == "📰 Live Trading News":
        st.markdown(
            f"""
            <div style="background-color: #080808; border: 1px solid #1a1a1a; padding: 12px 18px; border-radius: 4px; margin-bottom: 15px;">
                <h3 style="margin: 0; color: #eaecef; font-size: 16px;">📰 Live Financial & Trading News // {target_symbol} & Macro/Trump Feed</h3>
                <p style="margin: 4px 0 0 0; color: #848e9c; font-size: 12px;">Real-time headlines, press releases, market intelligence, and political statements.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        
        news_col1, news_col2 = st.columns([2, 1])
        with news_col1:
            news_source_type = st.radio(
                "News Scope", 
                options=[f"Ticker Specific ({target_symbol})", "General Market & Macro", "Trump Statements (Truth Social / Filtered)"], 
                horizontal=True
            )
        with news_col2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🔄 Refresh News Feed", use_container_width=True):
                st.cache_data.clear()
                st.rerun()

        @st.cache_data(ttl=300)
        def fetch_news_feed(sym, mode):
            articles = []
            if mode.startswith("Ticker"):
                if YFINANCE_AVAILABLE:
                    try:
                        tk = yf.Ticker(sym, session=get_yf_session())
                        raw_news = tk.news
                        for item in raw_news:
                            content = item.get("content", item)
                            title = content.get("title", item.get("title", ""))
                            publisher = content.get("provider", {}).get("displayName", item.get("publisher", "Yahoo Finance"))
                            link = content.get("clickThroughUrl", {}).get("url", item.get("link", "#"))
                            pub_time = content.get("pubDate", item.get("providerPublishTime", 0))
                            
                            if isinstance(pub_time, int) or isinstance(pub_time, float):
                                dt_str = datetime.datetime.fromtimestamp(pub_time).strftime("%Y-%m-%d %H:%M")
                            else:
                                dt_str = str(pub_time)[:16]
                                
                            if title:
                                articles.append({
                                    "title": title,
                                    "publisher": publisher,
                                    "link": link,
                                    "time": dt_str
                                })
                    except Exception:
                        pass
            
            if not articles or mode.startswith("General") or mode.startswith("Trump"):
                try:
                    rss_url = "https://finance.yahoo.com/news/rss"
                    resp = requests.get(rss_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
                    if resp.status_code == 200:
                        root = ET.fromstring(resp.content)
                        for item in root.findall(".//item"):
                            title = item.find("title").text if item.find("title") is not None else ""
                            pub = item.find("source").text if item.find("source") is not None else "Yahoo Finance"
                            link = item.find("link").text if item.find("link") is not None else "#"
                            pub_date = item.find("pubDate").text if item.find("pubDate") is not None else ""
                            
                            if mode.startswith("Trump"):
                                if any(kw in title.lower() for kw in ["trump", "tariff", "white house", "executive order", "duty", "trade"]):
                                    articles.append({
                                        "title": title,
                                        "publisher": f"Macro / {pub}",
                                        "link": link,
                                        "time": pub_date[:16]
                                    })
                            elif mode.startswith("General"):
                                articles.append({
                                    "title": title,
                                    "publisher": pub,
                                    "link": link,
                                    "time": pub_date[:16]
                                })
                except Exception:
                    pass

            if mode.startswith("Trump") and len(articles) <= 1:
                try:
                    from truthbrush import Api
                    api = Api(require_auth=False)
                    statuses = api.user(username="realDonaldTrump")
                    for status in list(statuses)[:15]:
                        text_content = getattr(status, "content", str(status))
                        articles.append({
                            "title": text_content[:180] + "...",
                            "publisher": "Truth Social (@realDonaldTrump)",
                            "link": "https://truthsocial.com/@realDonaldTrump",
                            "time": "Live Feed"
                        })
                except Exception:
                    pass

            return articles

        articles = fetch_news_feed(target_symbol, news_source_type)

        if not articles:
            st.info("No recent news articles found at the moment.")
        else:
            for art in articles:
                st.markdown(
                    f"""
                    <div style="background-color: #080808; border: 1px solid #1a1a1a; padding: 12px 15px; border-radius: 4px; margin-bottom: 10px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                            <span style="font-size: 11px; color: #f0b90b; font-weight: bold; background: rgba(240,185,11,0.1); padding: 2px 6px; border-radius: 3px;">{art['publisher']}</span>
                            <span style="font-size: 11px; color: #848e9c;">{art['time']}</span>
                        </div>
                        <a href="{art['link']}" target="_blank" style="text-decoration: none; color: #eaecef; font-size: 14px; font-weight: 500; display: block; margin-bottom: 4px;">
                            {art['title']} ↗
                        </a>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
