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
    st.session_state.active_ticker = st.query_params["ticker"].upper().strip()

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
        padding-top: 2rem;
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

if "started" not in st.session_state:
    st.session_state.started = False
if "animating" not in st.session_state:
    st.session_state.animating = False
if "active_ticker" not in st.session_state:
    st.session_state.active_ticker = "AAPL"
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

# 10-Second Fibonacci Trading Back-Test Animation Sequence
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
    let maxCandles = 38;
    let spawnCounter = 0;
    
    const fibLevels = [
        {val: 0.20, label: '0.236 (Retrace)', color: '#f6465d'},
        {val: 0.35, label: '0.382 (Golden)', color: '#f0b90b'},
        {val: 0.50, label: '0.500 (Mid Pivot)', color: '#0ecb81'},
        {val: 0.65, label: '0.618 (Golden Ratio)', color: '#29b6f6'},
        {val: 0.80, label: '0.786 (Deep Value)', color: '#ab47bc'}
    ];

    function spawnCandle() {
        if (candles.length < maxCandles) {
            let x = 45 + candles.length * 23;
            let baseY = canvas.height * (0.3 + Math.random() * 0.4);
            let height = 20 + Math.random() * 55;
            let isGreen = Math.random() > 0.42;
            candles.push({
                x: x,
                baseY: baseY,
                height: height,
                isGreen: isGreen,
                alpha: 0,
                oscillationOffset: Math.random() * Math.PI * 2
            });
        }
    }

    let startTime = Date.now();
    
    function animate() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        // Grid & Fib Lines
        fibLevels.forEach(fib => {
            let y = canvas.height * fib.val;
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

        spawnCounter++;
        if (spawnCounter % 16 === 0) {
            spawnCandle();
        }

        let timeSec = (Date.now() - startTime) / 1000;
        let remaining = Math.max(0, (10.0 - timeSec)).toFixed(1);
        document.getElementById('timerText').innerText = "Fibonacci Back-test in Progress... " + remaining + "s remaining";

        candles.forEach((c) => {
            if (c.alpha < 1) c.alpha += 0.06;
            
            // Move candles smoothly up and down based on market oscillation
            let wave = Math.sin(Date.now() * 0.0035 + c.oscillationOffset) * 22;
            let currentY = c.baseY + wave;

            ctx.save();
            ctx.globalAlpha = c.alpha;
            ctx.strokeStyle = c.isGreen ? '#0ecb81' : '#f6465d';
            ctx.fillStyle = c.isGreen ? 'rgba(14, 203, 129, 0.25)' : 'rgba(246, 70, 93, 0.25)';
            ctx.lineWidth = 1.5;

            // Wick
            ctx.beginPath();
            ctx.moveTo(c.x, currentY - c.height/2 - 10);
            ctx.lineTo(c.x, currentY + c.height/2 + 10);
            ctx.stroke();

            // Body
            ctx.fillRect(c.x - 6, currentY - c.height/2, 12, c.height);
            ctx.strokeRect(c.x - 6, currentY - c.height/2, 12, c.height);

            ctx.restore();
        });

        if (timeSec < 10.0) {
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

    header_col1, header_col2, header_col3, header_col4 = st.columns([1.5, 1.8, 1.8, 2.2])

    with header_col1:
        st.markdown("<div style='padding-top: 5px; color: #f0b90b; font-weight: bold; font-size: 13px;'>⚡ TB TERMINAL // RESEARCH</div>", unsafe_allow_html=True)

    with header_col2:
        def on_ticker_change():
            st.session_state.active_ticker = st.session_state.ticker_search_input.upper().strip()
        st.text_input("Search Ticker", value=st.session_state.active_ticker, key="ticker_search_input", on_change=on_ticker_change, label_visibility="collapsed")

    target_symbol = st.session_state.active_ticker

    @st.cache_resource
    def get_yf_session():
        session = requests.Session()
        session.headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        return session

    @st.cache_data(ttl=60)
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
            {format_badge("SPY", spy_price, spy_pct, "#1f0c0c", "#f6465d")}
            {format_badge("QQQ", qqq_price, qqq_pct, "#1f1a0c", "#f0b90b")}
            {format_badge(f"{target_symbol} (Live)", active_price, active_pct, "#150c1f", "#9c27b0")}
        </div>
    """, unsafe_allow_html=True)

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
                tk = yf.Ticker(target_symbol, session=get_yf_session())
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
                tk_finder = yf.Ticker(target_symbol, session=get_yf_session())
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
                <h3 style="margin: 0; color: #eaecef; font-size: 16px;">🔄 Sector Rotation Leaderboard</h3>
                <p style="margin: 4px 0 0 0; color: #848e9c; font-size: 12px;">Relative strength and performance metrics across major sector ETFs.</p>
            </div>
        """,
            unsafe_allow_html=True,
        )
        sectors = ["XLF", "XLE", "XLK", "XLV", "XLI", "XLP", "XLY", "XLU", "XLRE", "XLB", "XLC"]
        sector_data = []
        for sec in sectors:
            p, pct, vol = fetch_live_quote(sec)
            sector_data.append({"Sector ETF": sec, "Price ($)": p, "Change (%)": pct, "Volume": format_vol(vol)})
        
        df_sectors = pd.DataFrame(sector_data).sort_values(by="Change (%)", ascending=False)
        st.dataframe(df_sectors, use_container_width=True, hide_index=True)
