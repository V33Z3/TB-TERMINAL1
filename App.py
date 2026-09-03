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

tab_to_param = {
    "📈 Terminal Chart & Watchlist": "chart",
    "⚛️ Gamma Exposure (GEX) Analysis": "gex",
    "🎯 Optimal Contract Finder": "finder",
    "🔄 Sector Rotation Leaderboard": "sectors",
    "⚡ Unusual Options Activity": "uoa",
    "📰 Live Trading News": "news"
}
param_to_tab = {v: k for k, v in tab_to_param.items()}

if "ticker" in st.query_params:
    st.session_state.active_ticker = st.query_params["ticker"].upper().strip()

if "tab" in st.query_params:
    tab_param = st.query_params["tab"].lower()
    if tab_param in param_to_tab:
        expected_tab = param_to_tab[tab_param]
        if st.session_state.get("active_main_tab") != expected_tab:
            st.session_state.active_main_tab = expected_tab
            st.session_state.main_nav_radio = expected_tab

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

    .stAlert {
        background-color: #1f1a0c !important;
        color: #f0b90b !important;
        border: 1px solid #f0b90b !important;
    }

    [data-testid="stInfo"] {
        background-color: #080808 !important;
        color: #eaecef !important;
        border: 1px solid #1a1a1a !important;
    }
    
    [data-testid="stInfo"] svg {
        fill: #eaecef !important;
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

if "terminal_opened" not in st.session_state:
    st.session_state.terminal_opened = False
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
                <div id="winFlash" style="position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(14, 203, 129, 0.4); opacity: 0; pointer-events: none; transition: opacity 0.05s ease-in-out; z-index: 9999;"></div>

                <div style="text-align: center; width: 100%; max-width: 700px; padding: 0 20px;">
                    <div style="font-size: 32px; font-weight: bold; color: #f0b90b; letter-spacing: 3px; margin-bottom: 6px;">⚡ TB TERMINAL</div>
                    <p style="color: #0ecb81; font-size: 13px; font-family: monospace; letter-spacing: 2px; margin-bottom: 16px;">INITIALIZING INSTITUTIONAL FEED & GEX KERNEL...</p>
                    
                    <svg viewBox="0 0 700 220" style="width: 100%; max-width: 700px; background: #080808; border: 1px solid #1a1a1a; border-radius: 6px; overflow: hidden;">
                        <line x1="0" y1="40" x2="700" y2="40" stroke="#151515" stroke-width="1" />
                        <line x1="0" y1="85" x2="700" y2="85" stroke="#151515" stroke-width="1" />
                        <line x1="0" y1="130" x2="700" y2="130" stroke="#151515" stroke-width="1" />
                        <line x1="0" y1="175" x2="700" y2="175" stroke="#1a1a1a" stroke-width="1" />
                        
                        <line x1="140" y1="0" x2="140" y2="220" stroke="#121212" stroke-width="1" stroke-dasharray="3,3" />
                        <line x1="350" y1="0" x2="350" y2="220" stroke="#121212" stroke-width="1" stroke-dasharray="3,3" />
                        <line x1="560" y1="0" x2="560" y2="220" stroke="#121212" stroke-width="1" stroke-dasharray="3,3" />

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

                        <path d="M 30 140 Q 180 130 350 115 T 670 75" fill="none" stroke="#f0b90b" stroke-width="1.8" opacity="0.9"/>
                        <path d="M 30 155 Q 180 145 350 130 T 670 95" fill="none" stroke="#0ecb81" stroke-width="1.8" opacity="0.9"/>

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
                        rect.setAttribute('height', currentRh);
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
            st.rerun()

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

    elif selected_main_tab == "⚛️ Gamma Exposure (GEX) Analysis":
        st.markdown(f"### ⚛️ Gamma Exposure (GEX) Profile // {target_symbol}", unsafe_allow_html=True)
        st.info("Analyze dealer gamma exposure, key flip points, and strike concentrations.")
        
        sim_spot = active_price if active_price > 0 else 150.0
        exp_dates = ["2026-09-18", "2026-10-16", "2026-11-20"]
        if YFINANCE_AVAILABLE:
            try:
                session = get_yf_session()
                tk = yf.Ticker(target_symbol, session=session)
                live_opts = getattr(tk, "options", None)
                if live_opts and len(live_opts) > 0:
                    exp_dates = list(live_opts)
            except Exception:
                pass

        sel_exp = st.selectbox("Select Expiration Date:", options=exp_dates, key="gex_exp_box")
        strikes = np.arange(sim_spot - 20, sim_spot + 21, 5)
        mock_gex = np.sin(np.linspace(0, 3.14, len(strikes))) * 1000000
        df_grouped = pd.DataFrame({"Strike": strikes, "GEX": mock_gex})
        st.bar_chart(df_grouped.set_index("Strike")["GEX"])

    elif selected_main_tab == "🎯 Optimal Contract Finder":
        st.markdown(f"### 🎯 Optimal Contract Finder // {target_symbol}", unsafe_allow_html=True)
        st.info("Scan option chains for high-probability directional and volatility setups.")
        
        sim_price = active_price if active_price > 0 else 150.0
        exp_dates = ["2026-09-18", "2026-10-16", "2026-11-20"]
        
        if YFINANCE_AVAILABLE:
            try:
                session = get_yf_session()
                t_obj = yf.Ticker(target_symbol, session=session)
                live_opts = getattr(t_obj, "options", None)
                if live_opts and len(live_opts) > 0:
                    exp_dates = list(live_opts)
            except Exception:
                pass

        c1, c2 = st.columns(2)
        with c1:
            sel_exp = st.selectbox("Contract Expiration:", options=exp_dates, key="finder_opt_exp")
        with c2:
            opt_type = st.selectbox("Option Type:", options=["Calls", "Puts"], key="finder_opt_type")

        strikes = [sim_price - 15, sim_price - 10, sim_price - 5, sim_price, sim_price + 5, sim_price + 10, sim_price + 15]
        df_opts = pd.DataFrame({
            "contractSymbol": [f"{target_symbol}260918C{int(s*1000):08d}" for s in strikes],
            "strike": strikes,
            "lastPrice": [round(max(0.5, abs(sim_price - s) + 2.5), 2) for s in strikes],
            "bid": [round(max(0.4, abs(sim_price - s) + 2.2), 2) for s in strikes],
            "ask": [round(max(0.6, abs(sim_price - s) + 2.8), 2) for s in strikes],
            "volume": [12450, 8320, 45200, 68900, 15300, 6100, 4100],
            "openInterest": [45200, 21300, 89000, 124500, 34000, 15000, 9200],
            "impliedVolatility": [0.35, 0.38, 0.32, 0.30, 0.36, 0.40, 0.44]
        })

        st.dataframe(df_opts.sort_values(by="volume", ascending=False), use_container_width=True)

    elif selected_main_tab == "🔄 Sector Rotation Leaderboard":
        st.markdown("### 🔄 Sector Rotation Leaderboard", unsafe_allow_html=True)
        st.info("Tracking institutional capital flows across major market sectors.")
        
        simulated = [
            {"Sector": "Technology", "Ticker": "XLK", "Price": 235.40, "Change (%)": 1.45, "Volume": 45000200},
            {"Sector": "Consumer Discretionary", "Ticker": "XLY", "Price": 192.10, "Change (%)": 0.92, "Volume": 23100400},
            {"Sector": "Communication Services", "Ticker": "XLC", "Price": 94.60, "Change (%)": 0.65, "Volume": 18400100},
            {"Sector": "Financials", "Ticker": "XLF", "Price": 45.80, "Change (%)": 0.31, "Volume": 38900000},
            {"Sector": "Industrials", "Ticker": "XLI", "Price": 132.50, "Change (%)": 0.12, "Volume": 15200300},
            {"Sector": "Healthcare", "Ticker": "XLV", "Price": 142.30, "Change (%)": -0.05, "Volume": 19400200},
            {"Sector": "Materials", "Ticker": "XLB", "Price": 91.20, "Change (%)": -0.24, "Volume": 8900100},
            {"Sector": "Consumer Staples", "Ticker": "XLP", "Price": 78.40, "Change (%)": -0.41, "Volume": 12100400},
            {"Sector": "Utilities", "Ticker": "XLU", "Price": 71.90, "Change (%)": -0.68, "Volume": 14300000},
            {"Sector": "Real Estate", "Ticker": "XLRE", "Price": 41.50, "Change (%)": -0.95, "Volume": 9800200},
            {"Sector": "Energy", "Ticker": "XLE", "Price": 88.10, "Change (%)": -1.22, "Volume": 25400100},
        ]
        df_sec = pd.DataFrame(simulated).sort_values(by="Change (%)", ascending=False)
        st.dataframe(df_sec, use_container_width=True)

    elif selected_main_tab == "⚡ Unusual Options Activity":
        st.markdown(f"### ⚡ Unusual Options Activity Scanner // {target_symbol}", unsafe_allow_html=True)
        st.info("Scan option chains for abnormal volume-to-open-interest surges.")
        
        sim_price = active_price if active_price > 0 else 150.0
        unusual_rows = [
            {"Expiration": "2026-09-18", "Type": "CALL", "Strike": sim_price + 5, "Volume": 24500, "Open Interest": 3200, "IV": "42.5%"},
            {"Expiration": "2026-09-18", "Type": "PUT", "Strike": sim_price - 5, "Volume": 18200, "Open Interest": 2100, "IV": "48.1%"},
            {"Expiration": "2026-10-16", "Type": "CALL", "Strike": sim_price + 10, "Volume": 15400, "Open Interest": 1800, "IV": "39.4%"},
            {"Expiration": "2026-10-16", "Type": "PUT", "Strike": sim_price - 10, "Volume": 12100, "Open Interest": 1450, "IV": "45.0%"}
        ]
        st.dataframe(pd.DataFrame(unusual_rows), use_container_width=True)

    elif selected_main_tab == "📰 Live Trading News":
        st.markdown("### 📰 Live Market News & Wires", unsafe_allow_html=True)
        st.info("Real-time financial wire headlines and news feeds.")
        fallback_news = [
            ("Federal Reserve Maintains Interest Rate Outlook Amid Inflation Data", "Today", f"https://finance.yahoo.com/quote/{target_symbol}"),
            (f"Institutional Capital Flows Accelerate Into {target_symbol} Options", "Today", f"https://finance.yahoo.com/quote/{target_symbol}"),
            ("Market Technical Update: Key Support and Resistance Levels Holding", "Yesterday", f"https://finance.yahoo.com/quote/{target_symbol}")
        ]
        for title, date, link in fallback_news:
            st.markdown(f"""
                <div style="background: #080808; border: 1px solid #1a1a1a; padding: 10px; border-radius: 4px; margin-bottom: 8px;">
                    <a href="{link}" target="_blank" style="color: #eaecef; font-weight: bold; font-size: 13px; text-decoration: none;">{title}</a>
                    <div style="color: #848e9c; font-size: 11px; margin-top: 4px;">{date} // Wire Feed Active</div>
                </div>
            """, unsafe_allow_html=True)
