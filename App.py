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

# Map tabs to short query param codes
tab_to_param = {
    "📈 Terminal Chart & Watchlist": "chart",
    "⚛️ Gamma Exposure (GEX) Analysis": "gex",
    "🎯 Optimal Contract Finder": "finder",
    "🔄 Sector Rotation Leaderboard": "sectors",
    "⚡ Unusual Options Activity": "uoa",
    "📰 Live Trading News": "news"
}
param_to_tab = {v: k for k, v in tab_to_param.items()}

# Session state initializations (Must be at the top)
if "terminal_opened" not in st.session_state:
    st.session_state.terminal_opened = False
if "show_splash" not in st.session_state:
    st.session_state.show_splash = False
if "active_ticker" not in st.session_state:
    # Initialize from query params ONLY ONCE on first load to prevent override loops
    if "ticker" in st.query_params:
        st.session_state.active_ticker = st.query_params["ticker"].upper().strip()
    else:
        st.session_state.active_ticker = "AAPL"

if "watchlist" not in st.session_state:
    st.session_state.watchlist = ["AAPL", "TSLA", "NVDA", "AMZN", "MSFT", "GOOGL", "SPY", "QQQ"]
if "active_main_tab" not in st.session_state:
    st.session_state.active_main_tab = "📈 Terminal Chart & Watchlist"
if "main_nav_radio" not in st.session_state:
    st.session_state.main_nav_radio = st.session_state.active_main_tab

# Handle Tab Query Parameters without overriding manual clicks
if "tab" in st.query_params and "active_main_tab" not in st.session_state:
    tab_param = st.query_params["tab"].lower()
    if tab_param in param_to_tab:
        expected_tab = param_to_tab[tab_param]
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

# Landing Gate with Start Trading Button & Sequential Candlestick Printing Splash Screen Animation
if not st.session_state.terminal_opened:
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    col_auth1, col_auth2, col_auth3 = st.columns([1, 1.3, 1])
    with col_auth2:
        st.markdown("<h1 style='text-align: center; color: #f0b90b; letter-spacing: 3px; margin-bottom: 5px;'>⚡ TB TERMINAL</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #848e9c; font-size: 14px; font-family: monospace; letter-spacing: 1px; margin-bottom: 30px;'>INSTITUTIONAL QUANT RESEARCH & GEX ANALYTICS</p>", unsafe_allow_html=True)
        
        if st.button("Start Trading", use_container_width=True, type="primary"):
            st.session_state.show_splash = True
            st.session_state.terminal_opened = True
            st.rerun()
else:
    if st.session_state.show_splash:
        components.html(
            """
            <div style="background: #000000; height: 100vh; display: flex; flex-direction: column; justify-content: center; align-items: center; color: #eaecef; font-family: -apple-system, sans-serif; overflow: hidden; position: relative;">
                <!-- Win Flash Overlay -->
                <div id="winFlash" style="position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(14, 203, 129, 0.4); opacity: 0; pointer-events: none; transition: opacity 0.05s ease-in-out; z-index: 9999;"></div>

                <div style="text-align: center; width: 100%; max-width: 700px; padding: 0 20px;">
                    <div style="font-size: 32px; font-weight: bold; color: #f0b90b; letter-spacing: 3px; margin-bottom: 6px;">⚡ TB TERMINAL</div>
                    <p style="color: #0ecb81; font-size: 13px; font-family: monospace; letter-spacing: 2px; margin-bottom: 16px;">INITIALIZING INSTITUTIONAL FEED & GEX KERNEL...</p>
                    
                    <svg viewBox="0 0 700 220" style="width: 100%; max-width: 700px; background: #080808; border: 1px solid #1a1a1a; border-radius: 6px; overflow: hidden;">
                        <!-- Grid Lines -->
                        <line x1="0" y1="40" x2="700" y2="40" stroke="#151515" stroke-width="1" />
                        <line x1="0" y1="85" x2="700" y2="85" stroke="#151515" stroke-width="1" />
                        <line x1="0" y1="130" x2="700" y2="130" stroke="#151515" stroke-width="1" />
                        <line x1="0" y1="175" x2="700" y2="175" stroke="#1a1a1a" stroke-width="1" />
                        
                        <line x1="140" y1="0" x2="140" y2="220" stroke="#121212" stroke-width="1" stroke-dasharray="3,3" />
                        <line x1="350" y1="0" x2="350" y2="220" stroke="#121212" stroke-width="1" stroke-dasharray="3,3" />
                        <line x1="560" y1="0" x2="560" y2="220" stroke="#121212" stroke-width="1" stroke-dasharray="3,3" />

                        <!-- Volume Histogram Bars at Bottom -->
                        <g opacity="0.65">
                            <rect x="30" y="195" width="12" height="25" fill="#f6465d" rx="1"/>
                            <rect x="55" y="190" width="12" height="30" fill="#0ecb81" rx="1"/>
                            <rect x="80" y="200" width="12" height="20" fill="#0ecb81" rx="1"/>
                            <rect x="105" y="185" width="12" height="35" fill="#f6465d" rx="1"/>
                            <rect x="130" y="195" width="12" height="25" fill="#0ecb81" rx="1"/>
                            <rect x="155" y="180" width="12" height="40" fill="#0ecb81" rx="1"/>
                            <rect x="180" y="192" width="12" height="28" fill="#f6465d" rx="1"/>
                            <rect x="205" y="185" width="12" height="35" fill="#0ecb81" rx="1"/>
                            <rect x="230" y="175" width="12" height="45" fill="#0ecb81" rx="1"/>
                            <rect x="255" y="190" width="12" height="30" fill="#f6465d" rx="1"/>
                            <rect x="280" y="188" width="12" height="32" fill="#0ecb81" rx="1"/>
                            <rect x="305" y="170" width="12" height="50" fill="#0ecb81" rx="1"/>
                            <rect x="330" y="185" width="12" height="35" fill="#f6465d" rx="1"/>
                            <rect x="355" y="180" width="12" height="40" fill="#0ecb81" rx="1"/>
                            <rect x="380" y="190" width="12" height="30" fill="#f6465d" rx="1"/>
                            <rect x="405" y="175" width="12" height="45" fill="#0ecb81" rx="1"/>
                            <rect x="430" y="165" width="12" height="55" fill="#0ecb81" rx="1"/>
                            <rect x="455" y="180" width="12" height="40" fill="#f6465d" rx="1"/>
                            <rect x="480" y="172" width="12" height="48" fill="#0ecb81" rx="1"/>
                            <rect x="505" y="155" width="12" height="65" fill="#0ecb81" rx="1"/>
                            <rect x="530" y="145" width="12" height="75" fill="#0ecb81" rx="1"/>
                            <rect x="555" y="170" width="12" height="50" fill="#f6465d" rx="1"/>
                            <rect x="580" y="160" width="12" height="60" fill="#0ecb81" rx="1"/>
                            <rect x="605" y="150" width="12" height="70" fill="#0ecb81" rx="1"/>
                            <rect x="630" y="165" width="12" height="55" fill="#f6465d" rx="1"/>
                            <rect x="655" y="140" width="12" height="80" fill="#0ecb81" rx="1"/>
                        </g>

                        <!-- Moving Average Curves -->
                        <path d="M 30 140 Q 180 130 350 115 T 670 75" fill="none" stroke="#f0b90b" stroke-width="1.8" opacity="0.9"/>
                        <path d="M 30 155 Q 180 145 350 130 T 670 95" fill="none" stroke="#0ecb81" stroke-width="1.8" opacity="0.9"/>

                        <!-- Candlesticks Container -->
                        <g id="candlestick-container">
                            <g class="candle" data-y1="125" data-y2="155" data-ry="132" data-rh="16"><line x1="36" y1="140" x2="36" y2="140" stroke="#f6465d" stroke-width="1.5"/><rect x="31" y="140" width="10" height="0" fill="#f6465d" rx="1" opacity="0"/></g>
                            <g class="candle" data-y1="130" data-y2="160" data-ry="138" data-rh="14"><line x1="61" y1="145" x2="61" y2="145" stroke="#f6465d" stroke-width="1.5"/><rect x="56" y="145" width="10" height="0" fill="#f6465d" rx="1" opacity="0"/></g>
                            <g class="candle" data-y1="120" data-y2="148" data-ry="125" data-rh="18"><line x1="86" y1="134" x2="86" y2="134" stroke="#0ecb81" stroke-width="1.5"/><rect x="81" y="134" width="10" height="0" fill="#0ecb81" rx="1" opacity="0"/></g>
                            <g class="candle" data-y1="115" data-y2="145" data-ry="120" data-rh="20"><line x1="111" y1="130" x2="111" y2="130" stroke="#0ecb81" stroke-width="1.5"/><rect x="106" y="130" width="10" height="0" fill="#0ecb81" rx="1" opacity="0"/></g>
                            <g class="candle" data-y1="125" data-y2="152" data-ry="130" data-rh="15"><line x1="136" y1="138" x2="136" y2="138" stroke="#f6465d" stroke-width="1.5"/><rect x="131" y="138" width="10" height="0" fill="#f6465d" rx="1" opacity="0"/></g>
                            <g class="candle" data-y1="110" data-y2="140" data-ry="115" data-rh="22"><line x1="161" y1="125" x2="161" y2="125" stroke="#0ecb81" stroke-width="1.5"/><rect x="156" y="125" width="10" height="0" fill="#0ecb81" rx="1" opacity="0"/></g>
                            <g class="candle" data-y1="105" data-y2="135" data-ry="112" data-rh="18"><line x1="186" y1="120" x2="186" y2="120" stroke="#0ecb81" stroke-width="1.5"/><rect x="181" y="120" width="10" height="0" fill="#0ecb81" rx="1" opacity="0"/></g>
                            <g class="candle" data-y1="112" data-y2="142" data-ry="118" data-rh="16"><line x1="211" y1="127" x2="211" y2="127" stroke="#f6465d" stroke-width="1.5"/><rect x="206" y="127" width="10" height="0" fill="#f6465d" rx="1" opacity="0"/></g>
                            <g class="candle" data-y1="95" data-y2="128" data-ry="102" data-rh="20"><line x1="236" y1="112" x2="236" y2="112" stroke="#0ecb81" stroke-width="1.5"/><rect x="231" y="112" width="10" height="0" fill="#0ecb81" rx="1" opacity="0"/></g>
                            <g class="candle" data-y1="100" data-y2="130" data-ry="106" data-rh="15"><line x1="261" y1="115" x2="261" y2="115" stroke="#f6465d" stroke-width="1.5"/><rect x="256" y="115" width="10" height="0" fill="#f6465d" rx="1" opacity="0"/></g>
                            <g class="candle" data-y1="92" data-y2="122" data-ry="98" data-rh="18"><line x1="286" y1="107" x2="286" y2="107" stroke="#0ecb81" stroke-width="1.5"/><rect x="281" y="107" width="10" height="0" fill="#0ecb81" rx="1" opacity="0"/></g>
                            <g class="candle" data-y1="80" data-y2="112" data-ry="86" data-rh="22"><line x1="311" y1="96" x2="311" y2="96" stroke="#0ecb81" stroke-width="1.5"/><rect x="306" y="96" width="10" height="0" fill="#0ecb81" rx="1" opacity="0"/></g>
                            <g class="candle" data-y1="88" data-y2="118" data-ry="94" data-rh="16"><line x1="336" y1="103" x2="336" y2="103" stroke="#f6465d" stroke-width="1.5"/><rect x="331" y="103" width="10" height="0" fill="#f6465d" rx="1" opacity="0"/></g>
                            <g class="candle" data-y1="82" data-y2="110" data-ry="88" data-rh="18"><line x1="361" y1="96" x2="361" y2="96" stroke="#0ecb81" stroke-width="1.5"/><rect x="356" y="96" width="10" height="0" fill="#0ecb81" rx="1" opacity="0"/></g>
                            <g class="candle" data-y1="90" data-y2="120" data-ry="96" data-rh="16"><line x1="386" y1="105" x2="386" y2="105" stroke="#f6465d" stroke-width="1.5"/><rect x="381" y="105" width="10" height="0" fill="#f6465d" rx="1" opacity="0"/></g>
                            <g class="candle" data-y1="75" data-y2="105" data-ry="80" data-rh="20"><line x1="411" y1="90" x2="411" y2="90" stroke="#0ecb81" stroke-width="1.5"/><rect x="406" y="90" width="10" height="0" fill="#0ecb81" rx="1" opacity="0"/></g>
                            <g class="candle" data-y1="65" data-y2="98" data-ry="70" data-rh="22"><line x1="436" y1="82" x2="436" y2="82" stroke="#0ecb81" stroke-width="1.5"/><rect x="431" y="82" width="10" height="0" fill="#0ecb81" rx="1" opacity="0"/></g>
                            <g class="candle" data-y1="78" data-y2="108" data-ry="84" data-rh="16"><line x1="461" y1="93" x2="461" y2="93" stroke="#f6465d" stroke-width="1.5"/><rect x="456" y="93" width="10" height="0" fill="#f6465d" rx="1" opacity="0"/></g>
                            <g class="candle" data-y1="62" data-y2="92" data-ry="68" data-rh="20"><line x1="486" y1="77" x2="486" y2="77" stroke="#0ecb81" stroke-width="1.5"/><rect x="481" y="77" width="10" height="0" fill="#0ecb81" rx="1" opacity="0"/></g>
                            <g class="candle" data-y1="50" data-y2="82" data-ry="56" data-rh="22"><line x1="511" y1="66" x2="511" y2="66" stroke="#0ecb81" stroke-width="1.5"/><rect x="506" y="66" width="10" height="0" fill="#0ecb81" rx="1" opacity="0"/></g>
                            <g class="candle" data-y1="40" data-y2="72" data-ry="46" data-rh="22"><line x1="536" y1="56" x2="536" y2="56" stroke="#0ecb81" stroke-width="1.5"/><rect x="531" y="56" width="10" height="0" fill="#0ecb81" rx="1" opacity="0"/></g>
                            <g class="candle" data-y1="58" data-y2="88" data-ry="64" data-rh="16"><line x1="561" y1="73" x2="561" y2="73" stroke="#f6465d" stroke-width="1.5"/><rect x="556" y="73" width="10" height="0" fill="#f6465d" rx="1" opacity="0"/></g>
                            <g class="candle" data-y1="48" data-y2="80" data-ry="54" data-rh="20"><line x1="586" y1="64" x2="586" y2="64" stroke="#0ecb81" stroke-width="1.5"/><rect x="581" y="64" width="10" height="0" fill="#0ecb81" rx="1" opacity="0"/></g>
                            <g class="candle" data-y1="35" data-y2="68" data-ry="42" data-rh="22"><line x1="611" y1="52" x2="611" y2="52" stroke="#0ecb81" stroke-width="1.5"/><rect x="606" y="52" width="10" height="0" fill="#0ecb81" rx="1" opacity="0"/></g>
                            <g class="candle" data-y1="45" data-y2="75" data-ry="50" data-rh="18"><line x1="636" y1="60" x2="636" y2="60" stroke="#f6465d" stroke-width="1.5"/><rect x="631" y="60" width="10" height="0" fill="#f6465d" rx="1" opacity="0"/></g>
                            <g class="candle" data-y1="28" data-y2="60" data-ry="34" data-rh="22"><line x1="661" y1="44" x2="661" y2="44" stroke="#0ecb81" stroke-width="1.5"/><rect x="656" y="44" width="10" height="0" fill="#0ecb81" rx="1" opacity="0"/></g>
                        </g>
                    </svg>
                </div>
            </div>

            <script>
            const candles = document.querySelectorAll('.candle');
            let currentIndex = 0;

            function animateNextCandle() {
                if (currentIndex >= candles.length) {
                    const flash = document.getElementById('winFlash');
                    if (flash) {
                        flash.style.opacity = '0.95';
                    }
                    return;
                }

                if (currentIndex >= candles.length - 2) {
                    const flash = document.getElementById('winFlash');
                    if (flash) {
                        flash.style.opacity = '0.75';
                    }
                }

                const candle = candles[currentIndex];
                const rect = candle.querySelector('rect');
                const line = candle.querySelector('line');
                
                rect.setAttribute('opacity', '1');

                const targetY1 = parseFloat(candle.getAttribute('data-y1'));
                const targetY2 = parseFloat(candle.getAttribute('data-y2'));
                const targetRy = parseFloat(candle.getAttribute('data-ry'));
                const targetRh = parseFloat(candle.getAttribute('data-rh'));

                const randomOffset = (Math.random() - 0.5) * 8;
                const finalY1 = targetY1 + randomOffset;
                const finalY2 = targetY2 + randomOffset;
                const finalRy = targetRy + randomOffset;
                const finalRh = Math.max(4, targetRh + (Math.random() - 0.5) * 3);

                let startTime = performance.now();
                let bounceDuration = 10 + Math.random() * 10;

                function frame(now) {
                    let elapsed = now - startTime;
                    let progress = Math.min(1, elapsed / bounceDuration);

                    if (progress < 1) {
                        let bounceAmplitude = 8 * (1 - progress); 
                        let currentRy = finalRy + Math.sin(elapsed / 20) * bounceAmplitude;
                        let currentRh = Math.max(4, finalRh + Math.cos(elapsed / 15) * 2);
                        let currentY1 = currentRy - (finalRy - finalY1);
                        let currentY2 = currentRy + (finalY2 - finalRy);

                        rect.setAttribute('y', currentRy);
                        rect.setAttribute('height', currentRh);
                        line.setAttribute('y1', currentY1);
                        line.setAttribute('y2', currentY2);

                        requestAnimationFrame(frame);
                    } else {
                        rect.setAttribute('y', finalRy);
                        rect.setAttribute('height', finalRh);
                        line.setAttribute('y1', finalY1);
                        line.setAttribute('y2', finalY2);

                        currentIndex++;
                        setTimeout(animateNextCandle, 1);
                    }
                }

                requestAnimationFrame(frame);
            }

            animateNextCandle();
            </script>
            """,
            height=320,
        )
        time.sleep(0.25)
        st.session_state.show_splash = False
        st.rerun()

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
        sym = st.session_state.ticker_search_input.upper().strip()
        st.session_state.active_ticker = sym
        st.query_params["ticker"] = sym
    
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
                    vol_str = format_vol(p_vol) if p_vol > 0 else "-"

                    w_col_info, w_col_vol, w_col_price, w_col_del = st.columns([2.2, 1.4, 1.8, 1.0])
                    with w_col_info:
                        if st.button(sym, key=f"btn_ticker_{sym}", use_container_width=True):
                            st.session_state.active_ticker = sym
                            st.query_params["ticker"] = sym
                            st.rerun()
                    with w_col_vol:
                        st.markdown(f"<div style='font-size: 13px; color: #eaecef; padding-top: 8px;'>{vol_str}</div>", unsafe_allow_html=True)
                    with w_col_price:
                        st.markdown(f"<div style='font-size: 11px; text-align: right; padding-top: 6px; color: {color};'>${p_val:,.2f}<br><b>{sign}{p_pct:.2f}%</b></div>", unsafe_allow_html=True)
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
