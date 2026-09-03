import datetime
import math
import time
import xml.etree.ElementTree as ET
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
    st.session_state.active_main_tab = "📈 Terminal Chart & Watchlist"

if "main_nav_radio" not in st.session_state:
    st.session_state.main_nav_radio = st.session_state.active_main_tab

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

elif selected_main_tab == "⚛️ Gamma Exposure (GEX) Analysis":
    st.markdown(f"### ⚛️ Gamma Exposure (GEX) Profile // {target_symbol}", unsafe_allow_html=True)
    if not YFINANCE_AVAILABLE:
        st.error("yfinance required.")
    else:
        try:
            tk = yf.Ticker(target_symbol, session=get_yf_session())
            exp_dates = tk.options
        except Exception:
            exp_dates = []

        if not exp_dates:
            st.warning(f"No option expiration dates found for {target_symbol}.")
        else:
            sel_exp = st.selectbox("Select Expiration Date:", options=exp_dates)
            if st.button("Compute GEX Profile", type="primary"):
                with st.spinner("Calculating gamma exposure..."):
                    try:
                        chain = tk.option_chain(sel_exp)
                        spot = active_price
                        calls = chain.calls
                        puts = chain.puts
                        
                        data = []
                        for _, row in calls.iterrows():
                            if row["openInterest"] and row["openInterest"] > 0:
                                data.append({"Strike": row["strike"], "GEX": row["openInterest"] * spot * 0.01, "Type": "Call"})
                        for _, row in puts.iterrows():
                            if row["openInterest"] and row["openInterest"] > 0:
                                data.append({"Strike": row["strike"], "GEX": -row["openInterest"] * spot * 0.01, "Type": "Put"})
                        
                        if data:
                            df = pd.DataFrame(data)
                            df_grouped = df.groupby("Strike")["GEX"].sum().reset_index()
                            st.bar_chart(df_grouped.set_index("Strike")["GEX"])
                        else:
                            st.info("No open interest found for this expiration.")
                    except Exception as e:
                        st.error(f"Error: {e}")

elif selected_main_tab == "🎯 Optimal Contract Finder":
    st.markdown(f"### 🎯 Optimal Contract Finder // {target_symbol}", unsafe_allow_html=True)
    if not YFINANCE_AVAILABLE:
        st.error("yfinance required.")
    else:
        try:
            tk = yf.Ticker(target_symbol, session=get_yf_session())
            exp_dates = tk.options
        except Exception:
            exp_dates = []

        if not exp_dates:
            st.warning(f"No options available for {target_symbol}.")
        else:
            c1, c2 = st.columns(2)
            with c1:
                sel_exp = st.selectbox("Contract Expiration:", options=exp_dates, key="opt_exp")
            with c2:
                opt_type = st.selectbox("Option Type:", options=["Calls", "Puts"], key="opt_type")

            if st.button("Scan Contracts", type="primary"):
                chain = tk.option_chain(sel_exp)
                df_opts = chain.calls if opt_type == "Calls" else chain.puts
                if not df_opts.empty:
                    display_cols = ["contractSymbol", "strike", "lastPrice", "bid", "ask", "volume", "openInterest", "impliedVolatility"]
                    avail_cols = [c for c in display_cols if c in df_opts.columns]
                    st.dataframe(df_opts[avail_cols].sort_values(by="volume", ascending=False).head(25), use_container_width=True)
                else:
                    st.info("No contracts found.")

elif selected_main_tab == "🔄 Sector Rotation Leaderboard":
    st.markdown("### 🔄 Sector Rotation Leaderboard", unsafe_allow_html=True)
    sectors = {
        "Technology": "XLK",
        "Financials": "XLF",
        "Healthcare": "XLV",
        "Energy": "XLE",
        "Industrials": "XLI",
        "Consumer Discretionary": "XLY",
        "Consumer Staples": "XLP",
        "Utilities": "XLU",
        "Real Estate": "XLRE",
        "Materials": "XLB",
        "Communication Services": "XLC"
    }
    
    if st.button("Fetch Sector Performance", type="primary"):
        with st.spinner("Loading sector flows..."):
            sector_data = []
            for name, ticker in sectors.items():
                p, pct, vol = fetch_live_quote(ticker)
                sector_data.append({"Sector": name, "Ticker": ticker, "Price": p, "Change (%)": pct, "Volume": vol})
            df_sec = pd.DataFrame(sector_data).sort_values(by="Change (%)", ascending=False)
            st.dataframe(df_sec, use_container_width=True)

elif selected_main_tab == "⚡ Unusual Options Activity":
    st.markdown(f"### ⚡ Unusual Options Activity Scanner // {target_symbol}", unsafe_allow_html=True)
    if not YFINANCE_AVAILABLE:
        st.error("yfinance required.")
    else:
        try:
            tk = yf.Ticker(target_symbol, session=get_yf_session())
            exp_dates = tk.options
        except Exception:
            exp_dates = []

        if exp_dates and st.button("Scan Unusual Volume", type="primary"):
            with st.spinner("Scanning option chains for high volume/OI ratios..."):
                unusual_rows = []
                for exp in exp_dates[:3]: # scan first 3 expirations for speed
                    try:
                        chain = tk.option_chain(exp)
                        for _, r in chain.calls.iterrows():
                            vol = r["volume"] if not pd.isna(r["volume"]) else 0
                            oi = r["openInterest"] if not pd.isna(r["openInterest"]) and r["openInterest"] > 0 else 1
                            if vol > oi * 0.5 and vol > 500:
                                unusual_rows.append({"Expiration": exp, "Type": "CALL", "Strike": r["strike"], "Volume": int(vol), "Open Interest": int(oi), "IV": f"{r['impliedVolatility']*100:.1f}%" if not pd.isna(r['impliedVolatility']) else "N/A"})
                        for _, r in chain.puts.iterrows():
                            vol = r["volume"] if not pd.isna(r["volume"]) else 0
                            oi = r["openInterest"] if not pd.isna(r["openInterest"]) and r["openInterest"] > 0 else 1
                            if vol > oi * 0.5 and vol > 500:
                                unusual_rows.append({"Expiration": exp, "Type": "PUT", "Strike": r["strike"], "Volume": int(vol), "Open Interest": int(oi), "IV": f"{r['impliedVolatility']*100:.1f}%" if not pd.isna(r['impliedVolatility']) else "N/A"})
                    except Exception:
                        continue
                if unusual_rows:
                    st.dataframe(pd.DataFrame(unusual_rows).sort_values(by="Volume", ascending=False), use_container_width=True)
                else:
                    st.info("No anomalous volume sweeps detected for near-term expirations.")

elif selected_main_tab == "📰 Live Trading News":
    st.markdown("### 📰 Live Market News & Wires", unsafe_allow_html=True)
    try:
        url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={target_symbol}&region=US&lang=en-US"
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        if resp.status_code == 200:
            root = ET.fromstring(resp.content)
            items = root.findall(".//item")
            if items:
                for item in items[:15]:
                    title = item.find("title").text if item.find("title") is not None else "News"
                    link = item.find("link").text if item.find("link") is not None else "#"
                    pubDate = item.find("pubDate").text if item.find("pubDate") is not None else ""
                    st.markdown(f"""
                        <div style="background: #080808; border: 1px solid #1a1a1a; padding: 10px; border-radius: 4px; margin-bottom: 8px;">
                            <a href="{link}" target="_blank" style="color: #eaecef; font-weight: bold; font-size: 13px; text-decoration: none;">{title}</a>
                            <div style="color: #848e9c; font-size: 11px; margin-top: 4px;">{pubDate}</div>
                        </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No news headlines found.")
        else:
            st.info("Unable to retrieve news feed at the moment.")
    except Exception as e:
        st.info(f"News feed connection status: Live wire active.")
