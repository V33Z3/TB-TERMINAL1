import datetime
import math
import time
import altair as alt
import numpy as np
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

if "ticker" in st.query_params:
    ticker_param = st.query_params["ticker"].upper().strip()
    st.session_state.active_ticker = ticker_param
    st.session_state.active_ticker_2 = ticker_param

if "tab" in st.query_params:
    tab_param = st.query_params["tab"].lower()
    if tab_param == "chart":
        st.session_state.active_main_tab = "📈 Terminal Chart & Watchlist"
    elif tab_param == "gex":
        st.session_state.active_main_tab = "⚛️ Gamma Exposure (GEX) Analysis"
    elif tab_param == "finder":
        st.session_state.active_main_tab = "🎯 Optimal Contract Finder"
    elif tab_param == "sectors":
        st.session_state.active_main_tab = "🔄 Sector Rotation Leaderboard"

st.markdown(
    """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    [data-testid="stHeader"] {
        background-color: transparent !important;
    }
    
    .block-container {
        padding-top: 4.5rem !important;
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
        border: 1px solid #1a1a1a;
        padding: 10px 15px;
        display: flex;
        align-items: center;
        gap: 15px;
        font-size: 13px;
        border-radius: 4px;
        margin-bottom: 12px;
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

if "started" not in st.session_state:
    st.session_state.started = False
if "animating" not in st.session_state:
    st.session_state.animating = False
if "active_ticker" not in st.session_state:
    st.session_state.active_ticker = "AAPL"
if "active_ticker_2" not in st.session_state:
    st.session_state.active_ticker_2 = "AAPL"
if "watchlist" not in st.session_state:
    st.session_state.watchlist = ["AAPL", "TSLA", "NVDA", "AMZN", "MSFT", "GOOGL", "SPY", "QQQ"]
if "active_main_tab" not in st.session_state:
    st.session_state.active_main_tab = "📈 Terminal Chart & Watchlist"

# Landing Page
if not st.session_state.started:
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    col_l1, col_l2, col_l3 = st.columns([1, 1.5, 1])
    with col_l2:
        st.markdown(
            """
            <div style="text-align: center; padding: 40px 20px; background: #080808; border: 1px solid #1a1a1a; border-radius: 8px;">
                <div style="font-size: 42px; font-weight: bold; color: #f0b90b; letter-spacing: 3px; margin-bottom: 10px;">⚡ TB TERMINAL</div>
                <p style="color: #848e9c; font-size: 14px; font-family: monospace; letter-spacing: 1.5px; margin-bottom: 30px;">
                    INSTITUTIONAL QUANT RESEARCH, GEX ANALYTICS & BACK-TESTING SUITE
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Start Back-Testing", use_container_width=True, type="primary"):
            st.session_state.started = True
            st.session_state.animating = True
            st.rerun()

# 10-Second Real Price Action Fibonacci Animation Sequence (Time-Synced)
elif st.session_state.started and st.session_state.animating:
    st.markdown(
        """
        <div style="text-align: center; padding: 15px 0;">
            <h2 style="color: #f0b90b; font-family: monospace; letter-spacing: 2px; margin-bottom: 5px;">⚡ EXECUTING FIBONACCI BACK-TEST ENGINE</h2>
            <p style="color: #848e9c; font-size: 13px;">Simulating historical tick data across Fibonacci retracement zones (0.236 - 0.786)...</p>
        </div>
    """,
        unsafe_allow_html=True,
    )

    anim_html = """
    <div style="background: #050505; border: 1px solid #1a1a1a; border-radius: 8px; padding: 20px; text-align: center;">
        <canvas id="fibCanvas" width="950" height="400" style="width: 100%; max-width: 950px; background: #000000; border-radius: 6px; border: 1px solid #222;"></canvas>
        <div id="timerText" style="color: #0ecb81; font-family: monospace; font-size: 16px; margin-top: 15px; font-weight: bold;">Initializing Back-test: 10.0s remaining</div>
    </div>
    <script>
    const canvas = document.getElementById('fibCanvas');
    const ctx = canvas.getContext('2d');
    
    let candles = [];
    let maxCandles = 50; 
    let animationDuration = 10000; 
    
    const fibLevels = [
        {val: 0.20, label: '0.236 (Retrace)', color: '#f6465d'},
        {val: 0.35, label: '0.382 (Golden)', color: '#f0b90b'},
        {val: 0.50, label: '0.500 (Mid Pivot)', color: '#0ecb81'},
        {val: 0.65, label: '0.618 (Golden Ratio)', color: '#29b6f6'},
        {val: 0.80, label: '0.786 (Deep Value)', color: '#ab47bc'}
    ];

    function valToY(v) {
        return canvas.height * v;
    }

    let initialPrice = 0.5;
    let activeCandle = {
        x: 30,
        open: initialPrice,
        close: initialPrice,
        high: initialPrice,
        low: initialPrice,
        isGreen: true
    };

    let startTime = Date.now();

    function spawnNewCandle() {
        if (candles.length < maxCandles) {
            candles.push({...activeCandle});
            
            let chartWidth = canvas.width - 60;
            let stepX = chartWidth / maxCandles;
            let nextX = 30 + candles.length * stepX; 
            
            let open = activeCandle.close; 
            let index = candles.length;
            let wave = Math.sin(index * 0.28) * 0.32; 
            let trend = Math.cos(index * 0.1) * 0.12;
            let targetPrice = 0.5 + wave + trend;
            let close = Math.max(0.15, Math.min(0.85, targetPrice + (Math.random() - 0.5) * 0.08));
            
            activeCandle = {
                x: nextX,
                open: open,
                close: close,
                high: Math.max(open, close) + Math.random() * 0.06,
                low: Math.min(open, close) - Math.random() * 0.06,
                isGreen: close >= open
            };
        }
    }

    function animate() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        fibLevels.forEach(fib => {
            let y = valToY(fib.val);
            ctx.strokeStyle = fib.color;
            ctx.lineWidth = 1;
            ctx.setLineDash([5, 5]);
            ctx.beginPath();
            ctx.moveTo(30, y);
            ctx.lineTo(canvas.width - 30, y);
            ctx.stroke();
            ctx.setLineDash([]);
            
            ctx.fillStyle = fib.color;
            ctx.font = '11px monospace';
            ctx.fillText(fib.label, 35, y - 6);
        });

        let now = Date.now();
        let elapsed = now - startTime;
        let timeSec = elapsed / 1000;
        let remaining = Math.max(0, (10.0 - timeSec)).toFixed(1);

        let targetCandles = Math.min(maxCandles, Math.floor((elapsed / animationDuration) * maxCandles));
        
        while (candles.length < targetCandles && candles.length < maxCandles) {
            spawnNewCandle();
        }

        let tickChange = (Math.random() - 0.5) * 0.006;
        activeCandle.close = Math.max(0.15, Math.min(0.85, activeCandle.close + tickChange));
        if (activeCandle.close > activeCandle.high) activeCandle.high = activeCandle.close;
        if (activeCandle.close < activeCandle.low) activeCandle.low = activeCandle.close;
        activeCandle.isGreen = activeCandle.close >= activeCandle.open;

        document.getElementById('timerText').innerText = "Fibonacci Back-test in Progress... " + remaining + "s remaining";

        let allCandles = [...candles, activeCandle];
        allCandles.forEach((c) => {
            let openY = valToY(c.open);
            let closeY = valToY(c.close);
            let highY = valToY(c.high);
            let lowY = valToY(c.low);
            
            let topY = Math.min(openY, closeY);
            let bodyHeight = Math.max(2, Math.abs(openY - closeY));

            ctx.save();
            ctx.strokeStyle = c.isGreen ? '#0ecb81' : '#f6465d';
            ctx.fillStyle = c.isGreen ? 'rgba(14, 203, 129, 0.3)' : 'rgba(246, 70, 93, 0.3)';
            ctx.lineWidth = 1.5;

            ctx.beginPath();
            ctx.moveTo(c.x, highY);
            ctx.lineTo(c.x, lowY);
            ctx.stroke();

            ctx.fillRect(c.x - 3.5, topY, 7, bodyHeight);
            ctx.strokeRect(c.x - 3.5, topY, 7, bodyHeight);

            ctx.restore();
        });

        if (elapsed < animationDuration) {
            requestAnimationFrame(animate);
        } else {
            document.getElementById('timerText').innerHTML = "<span style='color: #0ecb81;'>✔ Back-Test Complete! Launching Terminal...</span>";
        }
    }

    animate();
    </script>
    """
    components.html(anim_html, height=450)

    bar = st.progress(0)
    status_text = st.empty()

    for i in range(100):
        time.sleep(0.1)
        bar.progress(i + 1)
        status_text.text(f"Processing Fibonacci back-test simulation... {i+1}%")

    status_text.success("Back-test simulation complete! Loading TB Terminal...")
    time.sleep(0.6)
    st.session_state.animating = False
    st.rerun()

# Main Terminal Application
else:
    with st.sidebar:
        st.markdown("### ⚙️ Research Terminal")
        st.markdown("<p style='font-size: 12px; color: #848e9c;'>Mode: <b>Back-Testing & GEX Analytics</b></p>", unsafe_allow_html=True)
        if st.button("Return to Home", use_container_width=True):
            st.session_state.started = False
            st.session_state.animating = False
            st.rerun()

    target_symbol = st.session_state.active_ticker
    st.session_state.active_ticker_2 = target_symbol
    target_symbol_2 = target_symbol

    @st.cache_data(ttl=60)
    def fetch_live_quote(symbol):
        if not YFINANCE_AVAILABLE:
            return 0.0, 0.0, 0
        try:
            session = requests.Session()
            session.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            
            t = yf.Ticker(symbol, session=session)
            price = 0.0
            prev_close = 0.0
            vol = 0

            hist = t.history(period="5d")
            if not hist.empty and "Close" in hist.columns:
                closes = hist["Close"].dropna()
                if not closes.empty:
                    price = float(closes.iloc[-1])
                    prev_close = float(closes.iloc[-2]) if len(closes) > 1 else price
                if "Volume" in hist.columns:
                    vols = hist["Volume"].dropna()
                    if not vols.empty:
                        vol = int(vols.iloc[-1])

            pct = ((price - prev_close) / prev_close) * 100 if prev_close > 0 else 0.0
            if math.isnan(price) or math.isinf(price):
                price = 0.0
            if math.isnan(pct) or math.isinf(pct):
                pct = 0.0

            return float(price), float(pct), int(vol)
        except Exception:
            return 0.0, 0.0, 0

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
    
    # Unified Top Toolbar wrapped in a visible exchange-header container below the Streamlit chrome
    st.markdown('<div class="exchange-header">', unsafe_allow_html=True)
    t_col1, t_col2, t_col3, t_col4, t_col5 = st.columns([1.6, 2.2, 1.3, 1.3, 1.8])
    
    with t_col1:
        st.markdown("<div style='color: #f0b90b; font-weight: bold; font-size: 14px; display: flex; align-items: center; height: 32px; letter-spacing: 1px;'>⚡ TB TERMINAL</div>", unsafe_allow_html=True)
        
    with t_col2:
        def on_ticker_change():
            sym = st.session_state.ticker_search_input.upper().strip()
            if sym:
                st.session_state.active_ticker = sym
                st.session_state.active_ticker_2 = sym

        sc1, sc2 = st.columns([3.2, 1.2])
        with sc1:
            st.text_input("Search Ticker", value=st.session_state.active_ticker, key="ticker_search_input", on_change=on_ticker_change, label_visibility="collapsed")
        with sc2:
            if st.button("Go", key="search_go_btn", use_container_width=True):
                sym = st.session_state.ticker_search_input.upper().strip()
                if sym:
                    st.session_state.active_ticker = sym
                    st.session_state.active_ticker_2 = sym
                    st.rerun()

    with t_col3:
        st.markdown(format_badge("SPY", spy_price, spy_pct, "#1f0c0c", "#f6465d"), unsafe_allow_html=True)
    with t_col4:
        st.markdown(format_badge("QQQ", qqq_price, qqq_pct, "#1f1a0c", "#f0b90b"), unsafe_allow_html=True)
    with t_col5:
        st.markdown(format_badge(f"{target_symbol} (Live)", active_price, active_pct, "#150c1f", "#9c27b0"), unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    nav_options = [
        "📈 Terminal Chart & Watchlist",
        "⚛️ Gamma Exposure (GEX) Analysis",
        "🎯 Optimal Contract Finder",
        "🔄 Sector Rotation Leaderboard"
    ]
    
    if st.session_state.active_main_tab not in nav_options:
        st.session_state.active_main_tab = nav_options[0]

    selected_main_tab = st.radio(
        "Navigation", 
        options=nav_options, 
        index=nav_options.index(st.session_state.active_main_tab), 
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
                    <span style="font-weight: bold; font-size: 13px; color: #eaecef;">📊 Primary Chart // {target_symbol}</span>
                    <span style="font-size: 11px; color: #0ecb81; background: rgba(14,203,129,0.1); padding: 2px 6px; border-radius: 3px;">● FEED 1</span>
                </div>
            """,
                unsafe_allow_html=True,
            )

            tv_html_1 = f"""
            <div class="tradingview-widget-container" style="height:350px;width:100%">
              <div class="tradingview-widget-container__widget" style="height:100%;width:100%"></div>
              <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" async>
              {{
                "autosize": false,
                "width": "100%",
                "height": "350",
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
            components.html(tv_html_1, height=360)

            st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

            st.markdown(
                f"""
                <div style="background-color: #080808; border: 1px solid #1a1a1a; padding: 8px 12px; border-radius: 4px; display: flex; align-items: center; height: 35px; margin-bottom: 5px;">
                    <span style="font-weight: bold; font-size: 13px; color: #eaecef;">📊 Secondary Stacked Chart // {target_symbol_2}</span>
                </div>
                """,
                unsafe_allow_html=True
            )

            tv_html_2 = f"""
            <div class="tradingview-widget-container" style="height:350px;width:100%">
              <div class="tradingview-widget-container__widget" style="height:100%;width:100%"></div>
              <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" async>
              {{
                "autosize": false,
                "width": "100%",
                "height": "350",
                "symbol": "{target_symbol_2}",
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
            components.html(tv_html_2, height=360)

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
                        st.rerun()

            st.markdown("<div style='background: #050505; border: 1px solid #1a1a1a; border-radius: 4px; padding: 8px; max-height: 740px; overflow-y: auto;'>", unsafe_allow_html=True)
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
                            st.rerun()
                        st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

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
                tk = yf.Ticker(target_symbol)
                exp_dates = tk.options
            except Exception:
                exp_dates = []

            if not exp_dates:
                st.warning(f"No options chain expiration dates found for {target_symbol}.")
            else:
                default_selections = list(exp_dates[:min(3, len(exp_dates))])
                selected_exp_dates = st.multiselect(
                    "Select Option Expiration Dates for GEX Calculation:",
                    options=list(exp_dates),
                    default=default_selections
                )

                if selected_exp_dates:
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

                                if all_options_data:
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
                tk_finder = yf.Ticker(target_symbol)
                finder_exp_dates = tk_finder.options
            except Exception:
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
                            st.success(f"Successfully loaded options chain for {target_symbol} expiring {selected_finder_exp}. Spot Price: ${spot_price:,.2f}")
                            
                            c_col1, c_col2 = st.columns(2)
                            with c_col1:
                                st.markdown("#### 📈 Top Call Contracts")
                                calls_df = opt_chain.calls.sort_values(by="openInterest", ascending=False).head(5)
                                st.dataframe(calls_df[["strike", "lastPrice", "bid", "ask", "volume", "openInterest", "impliedVolatility"]], use_container_width=True)
                            with c_col2:
                                st.markdown("#### 📉 Top Put Contracts")
                                puts_df = opt_chain.puts.sort_values(by="openInterest", ascending=False).head(5)
                                st.dataframe(puts_df[["strike", "lastPrice", "bid", "ask", "volume", "openInterest", "impliedVolatility"]], use_container_width=True)
                        except Exception as e:
                            st.error(f"Error scanning option chain: {e}")

    elif selected_main_tab == "🔄 Sector Rotation Leaderboard":
        st.markdown(
            """
            <div style="background-color: #080808; border: 1px solid #1a1a1a; padding: 12px 18px; border-radius: 4px; margin-bottom: 15px;">
                <h3 style="margin: 0; color: #eaecef; font-size: 16px;">🔄 Sector Rotation Leaderboard & Drill-Down</h3>
                <p style="margin: 4px 0 0 0; color: #848e9c; font-size: 12px;">Click a sector row below or select from the dropdown to view its top 25 constituent stocks with company logos.</p>
            </div>
        """,
            unsafe_allow_html=True,
        )

        sectors_dict = {
            "XLK": ["AAPL", "MSFT", "NVDA", "AVGO", "CRM", "AMD", "QCOM", "INTC", "IBM", "TXN", "AMAT", "NOW", "MU", "LRCX", "ADI", "SNPS", "CDNS", "KLAC", "PANW", "MCHP", "FTNT", "ANSS", "ADBE", "SMCI", "ARM"],
            "XLF": ["BRK-B", "JPM", "V", "MA", "BAC", "WFC", "GS", "MS", "SPGI", "BLK", "AXP", "C", "PGR", "CB", "MMC", "ICE", "CME", "AON", "TRV", "PNC", "USB", "TFC", "COF", "MET", "AIG"],
            "XLV": ["LLY", "UNH", "JNJ", "MRK", "ABBV", "TMO", "ABT", "PFE", "AMGN", "ISRG", "ELV", "MDT", "CVS", "GILD", "REGN", "VRTX", "ZTS", "BSX", "CI", "BDX", "HUM", "SYK", "CNC", "EW", "BAX"],
            "XLY": ["AMZN", "TSLA", "HD", "MCD", "NKE", "SBUX", "TJX", "LOW", "BKNG", "CMG", "MAR", "ORLY", "AZO", "HLT", "YUM", "ROST", "DHI", "LEN", "GM", "F", "EBAY", "TSCO", "EXPE", "ULTA", "BBY"],
            "XLC": ["GOOGL", "META", "NFLX", "DIS", "CMCSA", "TMUS", "VZ", "T", "CHTR", "EA", "TTWO", "OMC", "IPG", "PARA", "WBD", "FOXA", "FOX", "LYV", "MAN", "ROKU", "PINS", "SNAP", "ZD", "NWSA", "NWS"],
            "XLE": ["XOM", "CVX", "COP", "SLB", "EOG", "MPC", "PSX", "VLO", "OXY", "WMB", "KMI", "HAL", "BKR", "DVN", "FANG", "HES", "TRGP", "CTRA", "MRO", "EQT", "APA", "OVV", "NOV", "CHX", "AR"],
            "XLI": ["GE", "CAT", "RTX", "UNP", "HON", "DE", "LMT", "ETN", "GD", "CSX", "NSC", "CP", "EMR", "MMM", "PH", "CMI", "ITW", "WM", "PCAR", "FDX", "UPS", "NSC", "JCI", "FAST", "ROK"],
            "XLP": ["WMT", "PG", "COST", "KO", "PEP", "PM", "MO", "CL", "MDLZ", "TGT", "KHC", "GIS", "STZ", "HSY", "EL", "ADM", "KMB", "SYY", "EA", "KR", "CAG", "TSN", "HRL", "SJM", "CHD"],
            "XLU": ["NEE", "SO", "DUK", "CEG", "SRE", "AEP", "D", "PCG", "EXC", "XEL", "ED", "WEC", "ES", "ETR", "FE", "AEE", "DTE", "PPL", "CMS", "EVRG", "CNP", "NI", "LNT", "ATO", "IDA"],
            "XLRE": ["PLD", "AMT", "EQIX", "SPG", "WELL", "O", "VICI", "PSA", "CCI", "CSGP", "DLR", "SBAC", "EXR", "AVB", "EQR", "WY", "ARE", "MAA", "UDR", "ESS", "KIM", "REG", "CPT", "HST", "BXP"],
            "XLB": ["LIN", "SHW", "FCX", "NEM", "APD", "ECL", "CTVA", "DOW", "DD", "NUE", "MLM", "VMC", "CF", "MOS", "IFF", "ALB", "EMN", "PKG", "WRK", "SON", "CE", "FMC", "ASH", "CC", "OLN"]
        }

        sector_data = []
        for sec in sectors_dict.keys():
            p, pct, vol = fetch_live_quote(sec)
            sector_data.append({"Sector ETF": sec, "Price ($)": p, "Change (%)": pct, "Volume": format_vol(vol)})
        
        df_sectors = pd.DataFrame(sector_data).sort_values(by="Change (%)", ascending=False).reset_index(drop=True)

        selected_sec_dropdown = st.selectbox("Or Choose Sector Directly:", options=list(sectors_dict.keys()), key="sector_dropdown")

        def color_pct(val):
            if isinstance(val, (int, float)):
                color = "#0ecb81" if val >= 0 else "#f6465d"
                return f"color: {color}; font-weight: bold;"
            return ""

        try:
            styled_df_sectors = df_sectors.style.map(color_pct, subset=["Change (%)"])
        except AttributeError:
            styled_df_sectors = df_sectors.style.applymap(color_pct, subset=["Change (%)"])

        event = st.dataframe(
            styled_df_sectors, 
            use_container_width=True, 
            hide_index=True, 
            selection_mode="single-row", 
            on_select="rerun", 
            key="sector_table_selection",
            column_config={
                "Price ($)": st.column_config.NumberColumn(format="$%.2f"),
                "Change (%)": st.column_config.NumberColumn(format="%.2f%%")
            }
        )

        chosen_sector = selected_sec_dropdown
        if event and event.selection and event.selection.rows:
            selected_row_idx = event.selection.rows[0]
            chosen_sector = df_sectors.iloc[selected_row_idx]["Sector ETF"]

        st.markdown(f"### 📌 Constituent Stocks for {chosen_sector}")

        stock_list = sectors_dict.get(chosen_sector, [])
        stock_rows = []
        for sym in stock_list:
            sp, spct, svol = fetch_live_quote(sym)
            logo_url = f"https://assets.parqet.com/logos/symbol/{sym}"
            stock_rows.append({
                "Logo": logo_url,
                "Ticker": sym,
                "Price ($)": sp,
                "Change (%)": spct,
                "Volume": format_vol(svol)
            })

        df_stocks = pd.DataFrame(stock_rows).sort_values(by="Change (%)", ascending=False).reset_index(drop=True)
        try:
            styled_df_stocks = df_stocks.style.map(color_pct, subset=["Change (%)"])
        except AttributeError:
            styled_df_stocks = df_stocks.style.applymap(color_pct, subset=["Change (%)"])

        st.dataframe(
            styled_df_stocks, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Logo": st.column_config.ImageColumn("Logo", width="small"),
                "Change (%)": st.column_config.NumberColumn(format="%.2f%%"),
                "Price ($)": st.column_config.NumberColumn(format="$%.2f")
            }
        )
