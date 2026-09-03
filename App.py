import datetime
import math
import time
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

# Handle Ticker Selection via Query Parameters
if "ticker" in st.query_params:
  st.session_state.active_ticker = st.query_params["ticker"].upper().strip()

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
                    
                    <div style="background: #080808; border: 1px solid #1a1a1a; border-radius: 12px; padding: 40px; box-shadow: 0 20px 60px rgba(0,0,0,0.95);">
                        <svg width="100%" height="260" viewBox="0 0 600 260" style="overflow: visible;">
                            <line x1="0" y1="50" x2="600" y2="50" stroke="#1a1a1a" stroke-width="1" />
                            <line x1="0" y1="110" x2="600" y2="110" stroke="#1a1a1a" stroke-width="1" />
                            <line x1="0" y1="170" x2="600" y2="170" stroke="#1a1a1a" stroke-width="1" />
                            <line x1="0" y1="230" x2="600" y2="230" stroke="#1a1a1a" stroke-width="1" />
                            
                            <rect x="60" y="120" width="16" height="50" fill="#f6465d" rx="3" />
                            <line x1="68" y1="95" x2="68" y2="195" stroke="#f6465d" stroke-width="2.5" />
                            <rect x="135" y="140" width="16" height="40" fill="#0ecb81" rx="3" />
                            <line x1="143" y1="115" x2="143" y2="205" stroke="#0ecb81" stroke-width="2.5" />
                            <rect x="210" y="110" width="16" height="55" fill="#0ecb81" rx="3" />
                            <line x1="218" y1="85" x2="218" y2="190" stroke="#0ecb81" stroke-width="2.5" />
                            <rect x="285" y="125" width="16" height="45" fill="#f6465d" rx="3" />
                            <line x1="293" y1="100" x2="293" y2="200" stroke="#f6465d" stroke-width="2.5" />
                            <rect x="360" y="95" width="16" height="60" fill="#0ecb81" rx="3" />
                            <line x1="368" y1="75" x2="368" y2="185" stroke="#0ecb81" stroke-width="2.5" />

                            <path d="M 30 160 Q 180 140, 330 115 T 570 100" fill="none" stroke="#3b82f6" stroke-width="3" stroke-linecap="round" opacity="0.85" />
                            <path d="M 30 145 Q 180 125, 330 100 T 570 85" fill="none" stroke="#f0b90b" stroke-width="3" stroke-linecap="round" opacity="0.9" />

                            <g class="surge-group">
                                <rect x="435" y="45" width="16" height="70" fill="#0ecb81" rx="3" class="surge-candle-1" />
                                <line x1="443" y1="20" x2="443" y2="150" stroke="#0ecb81" stroke-width="2.5" class="surge-candle-1" />
                                <rect x="510" y="15" width="16" height="85" fill="#0ecb81" rx="3" class="surge-candle-2" />
                                <line x1="518" y1="0" x2="518" y2="125" stroke="#0ecb81" stroke-width="2.5" class="surge-candle-2" />
                            </g>
                        </svg>
                        
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 25px; font-size: 15px;">
                            <span style="color: #848e9c; font-family: monospace; display: flex; align-items: center; gap: 8px;">
                                <span style="display:inline-block; width:12px; height:12px; background:#f0b90b; border-radius:50%;"></span> SMA 20 (Fast)
                                <span style="display:inline-block; width:12px; height:12px; background:#3b82f6; border-radius:50%; margin-left:12px;"></span> SMA 50 (Slow)
                            </span>
                            <span style="color: #0ecb81; font-weight: bold; background: rgba(14,203,129,0.2); padding: 6px 14px; border-radius: 6px; font-size: 14px;">🚀 GEX MODULE READY ▲</span>
                        </div>
                    </div>

                    <div style="width: 100%; height: 6px; background: #1a1a1a; border-radius: 3px; margin: 40px 0 15px 0; overflow: hidden;">
                        <div style="width: 100%; height: 100%; background: linear-gradient(90deg, transparent, #0ecb81, #f0b90b, #3b82f6, transparent); animation: slide 1.2s infinite linear;"></div>
                    </div>
                </div>
            </div>
            <style>
            @keyframes slide {
                0% { transform: translateX(-100%); }
                100% { transform: translateX(100%); }
            }
            @keyframes surgeUp {
                0% { transform: translateY(50px) scaleY(0.5); opacity: 0.2; }
                100% { transform: translateY(0px) scaleY(1); opacity: 1; }
            }
            .surge-candle-1 { transform-origin: bottom center; animation: surgeUp 1.0s cubic-bezier(0.1, 0.9, 0.2, 1) forwards; }
            .surge-candle-2 { transform-origin: bottom center; animation: surgeUp 1.3s cubic-bezier(0.1, 0.9, 0.2, 1) forwards; filter: drop-shadow(0px 0px 12px rgba(14, 203, 129, 0.9)); }
            </style>
        """,
        height=850,
    )
    time.sleep(1.8)
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

  def fetch_live_quote(symbol):
    price, pct, vol = 0.0, 0.0, 0
    if YFINANCE_AVAILABLE:
      try:
        session = get_yf_session()
        t = yf.Ticker(symbol, session=session)
        hist = t.history(period="5d")
        if not hist.empty:
          yf_close = float(hist["Close"].iloc[-1])
          prev = float(hist["Close"].iloc[-2]) if len(hist) > 1 else float(hist["Open"].iloc[-1])
          vol = int(hist["Volume"].iloc[-1]) if "Volume" in hist.columns else 0
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

  @st.fragment(run_every="3s")
  def render_live_header(sym):
    spy_price, spy_pct, _ = fetch_live_quote("SPY")
    qqq_price, qqq_pct, _ = fetch_live_quote("QQQ")
    active_price, active_pct, _ = fetch_live_quote(sym)

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
    spy_html = format_badge("SPY", spy_price, spy_pct, "#1f0c0c", "#f6465d")
    qqq_html = format_badge("QQQ", qqq_price, qqq_pct, "#1f1a0c", "#f0b90b")
    active_html = format_badge(f"{sym} (Live)", active_price, active_pct, "#150c1f", "#9c27b0")

    st.markdown(f"""
            <div class="exchange-header">
                {spy_html}
                {qqq_html}
                {active_html}
            </div>
        """, unsafe_allow_html=True)

  render_live_header(target_symbol)

  # TOP-LEVEL TABS: Research Chart / Watchlist, Gamma Exposure (GEX), Optimal Contract Finder, and Sector Rotation
  main_tab_chart, main_tab_gex, main_tab_finder, main_tab_sectors = st.tabs([
      "📈 Terminal Chart & Watchlist",
      "⚛️ Gamma Exposure (GEX) Analysis",
      "🎯 Optimal Contract Finder",
      "🔄 Sector Rotation Matrix"
  ])

  with main_tab_chart:
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

      @st.fragment(run_every="3s")
      def render_watchlist_fragment():
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
                      <a href="?ticker={sym}" target="_self" style="text-decoration: none; display: flex; align-items: center; gap: 8px; padding-top: 4px;">
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

      render_watchlist_fragment()

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

  with main_tab_gex:
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
              r = 0.045  # Risk-free rate assumption

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

                st.markdown(
                    f"""
                    <div style="background-color: #050505; border: 1px solid #1a1a1a; padding: 15px; border-radius: 4px; font-size: 13px; color: #b7bdc6; margin-top: 15px;">
                        <b>Quant Intelligence Note:</b> 
                        <ul>
                            <li><b>Positive GEX (Green Bars — Right):</b> Market makers are long gamma and must dynamically hedge by selling into rallies and buying into dips, which tends to compress intraday volatility.</li>
                            <li><b>Negative GEX (Red Bars — Left):</b> Market makers are short gamma and must chase momentum by buying rising markets and selling falling markets, amplifying volatility.</li>
                            <li><b>Gamma Flip Point (~${flip_strike:,.2f}):</b> The critical institutional pivot level where dealer hedging behavior flips polarity.</li>
                        </ul>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            except Exception as e:
              st.error(f"Error computing Gamma Exposure: {e}")

  with main_tab_finder:
    st.markdown(
        f"""
            <div style="background-color: #080808; border: 1px solid #1a1a1a; padding: 12px 18px; border-radius: 4px; margin-bottom: 15px;">
                <h3 style="margin: 0; color: #eaecef; font-size: 16px;">🎯 Contract Selection // {target_symbol}</h3>
                <p style="margin: 4px 0 0 0; color: #848e9c; font-size: 12px;">Automatically analyzes the options chain to identify and rank the highest-conviction Call and Put contracts based on institutional liquidity, tight bid-ask spreads, and optimal 0.35–0.50 Delta exposure.</p>
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
                  vol = float(row["volume"]) if not pd.isna(row["volume"]) else 0.0
                  oi = float(row["openInterest"]) if not pd.isna(row["openInterest"]) else 0.0
                  iv = float(row["impliedVolatility"]) if not pd.isna(row["impliedVolatility"]) and row["impliedVolatility"] > 0 else 0.2
                  last_p = float(row["lastPrice"]) if not pd.isna(row["lastPrice"]) else 0.0
                  bid = float(row["bid"]) if not pd.isna(row["bid"]) else 0.0
                  ask = float(row["ask"]) if not pd.isna(row["ask"]) else 0.0

                  if vol < 5 and oi < 20:
                    continue

                  # Black-Scholes Delta
                  try:
                    d1 = (math.log(spot_price / strike) + (r + 0.5 * iv**2) * T) / (iv * math.sqrt(T))
                    call_d = norm_cdf(d1)
                    delta = call_d if opt_type == "Call" else call_d - 1.0
                  except Exception:
                    delta = 0.5 if opt_type == "Call" else -0.5

                  # Penalty for deviation from optimal directional swing delta (~0.40)
                  delta_penalty = abs(abs(delta) - 0.40)
                  spread = max(ask - bid, 0.01)

                  # Algorithmic institutional score
                  score = (vol * 2.0 + oi * 1.0) / ((spread * 100.0 + 1.0) * (delta_penalty + 0.5))

                  scored_contracts.append({
                      "Contract": row["contractSymbol"],
                      "Type": opt_type,
                      "Strike": strike,
                      "Last": last_p,
                      "Bid": bid,
                      "Ask": ask,
                      "Volume": int(vol),
                      "Open Interest": int(oi),
                      "IV (%)": round(iv * 100, 1),
                      "Delta": round(delta, 2),
                      "Score": score
                  })
                return sorted(scored_contracts, key=lambda x: x["Score"], reverse=True)

              best_calls = evaluate_contracts(opt_chain.calls, "Call")
              best_puts = evaluate_contracts(opt_chain.puts, "Put")

              top_call = best_calls[0] if best_calls else None
              top_put = best_puts[0] if best_puts else None

              c_col1, c_col2 = st.columns(2)

              with c_col1:
                st.markdown("<div style='background: #080808; border: 1px solid #1a1a1a; padding: 15px; border-radius: 6px;'>", unsafe_allow_html=True)
                st.markdown("<h4 style='color: #0ecb81; margin-top: 0;'>🟢 Top Recommended Call Contract</h4>", unsafe_allow_html=True)
                if top_call:
                  st.markdown(f"**Contract:** `{top_call['Contract']}`")
                  mc1, mc2, mc3 = st.columns(3)
                  mc1.metric("Strike", f"${top_call['Strike']:,.2f}")
                  mc2.metric("Last Price", f"${top_call['Last']:,.2f}")
                  mc3.metric("Delta", f"{top_call['Delta']}")

                  mc4, mc5, mc6 = st.columns(3)
                  mc4.metric("Volume", f"{top_call['Volume']:,}")
                  mc5.metric("Open Interest", f"{top_call['Open Interest']:,}")
                  mc6.metric("Implied Vol", f"{top_call['IV (%)']}%")
                  st.markdown(f"<p style='color: #848e9c; font-size: 11px; margin-bottom: 0;'>Bid: ${top_call['Bid']:,.2f} | Ask: ${top_call['Ask']:,.2f}</p>", unsafe_allow_html=True)
                else:
                  st.warning("No qualifying call contracts found for this expiration.")
                st.markdown("</div>", unsafe_allow_html=True)

              with c_col2:
                st.markdown("<div style='background: #080808; border: 1px solid #1a1a1a; padding: 15px; border-radius: 6px;'>", unsafe_allow_html=True)
                st.markdown("<h4 style='color: #f6465d; margin-top: 0;'>🔴 Top Recommended Put Contract</h4>", unsafe_allow_html=True)
                if top_put:
                  st.markdown(f"**Contract:** `{top_put['Contract']}`")
                  mp1, mp2, mp3 = st.columns(3)
                  mp1.metric("Strike", f"${top_put['Strike']:,.2f}")
                  mp2.metric("Last Price", f"${top_put['Last']:,.2f}")
                  mp3.metric("Delta", f"{top_put['Delta']}")

                  mp4, mp5, mp6 = st.columns(3)
                  mp4.metric("Volume", f"{top_put['Volume']:,}")
                  mp5.metric("Open Interest", f"{top_put['Open Interest']:,}")
                  mp6.metric("Implied Vol", f"{top_put['IV (%)']}%")
                  st.markdown(f"<p style='color: #848e9c; font-size: 11px; margin-bottom: 0;'>Bid: ${top_put['Bid']:,.2f} | Ask: ${top_put['Ask']:,.2f}</p>", unsafe_allow_html=True)
                else:
                  st.warning("No qualifying put contracts found for this expiration.")
                st.markdown("</div>", unsafe_allow_html=True)

              st.markdown("<br><h4 style='color: #eaecef; font-size: 14px;'>Alternative Ranked Contracts</h4>", unsafe_allow_html=True)
              all_ranked = best_calls[:5] + best_puts[:5]
              if all_ranked:
                df_top = pd.DataFrame(all_ranked).drop(columns=["Score"])
                st.dataframe(df_top, use_container_width=True, height=250)

            except Exception as e:
              st.error(f"Error selecting optimal contracts: {e}")

  with main_tab_sectors:
    st.markdown(
        """
            <div style="background-color: #080808; border: 1px solid #1a1a1a; padding: 12px 18px; border-radius: 4px; margin-bottom: 15px;">
                <h3 style="margin: 0; color: #eaecef; font-size: 16px;">🔄 Sector Rotation Matrix</h3>
                <p style="margin: 4px 0 0 0; color: #848e9c; font-size: 12px;">Tracks performance across the 11 GICS sector SPDR ETFs to monitor institutional capital flows and risk-on/risk-off rotations.</p>
            </div>
        """,
        unsafe_allow_html=True,
    )

    if not YFINANCE_AVAILABLE:
      st.error("`yfinance` is required to load sector performance data.")
    else:
      with st.spinner("Fetching institutional sector rotation matrix..."):
        try:
          sectors_dict = {
              "Technology": "XLK",
              "Financials": "XLF",
              "Healthcare": "XLV",
              "Consumer Discretionary": "XLY",
              "Consumer Staples": "XLP",
              "Energy": "XLE",
              "Industrials": "XLI",
              "Utilities": "XLU",
              "Real Estate": "XLRE",
              "Materials": "XLB",
              "Communication Services": "XLC",
          }

          sector_rows = []
          session = get_yf_session()

          for sector_name, sym in sectors_dict.items():
            t = yf.Ticker(sym, session=session)
            hist = t.history(period="1mo")
            if not hist.empty:
              price = float(hist["Close"].iloc[-1])
              p_1d = float(hist["Close"].iloc[-2]) if len(hist) > 1 else price
              p_5d = float(hist["Close"].iloc[-5]) if len(hist) >= 5 else float(hist["Close"].iloc[0])
              p_1m = float(hist["Close"].iloc[0])

              chg_1d = ((price - p_1d) / p_1d) * 100
              chg_5d = ((price - p_5d) / p_5d) * 100
              chg_1m = ((price - p_1m) / p_1m) * 100

              sector_rows.append({
                  "Sector": sector_name,
                  "Ticker": sym,
                  "Price ($)": round(price, 2),
                  "1D Return (%)": round(chg_1d, 2),
                  "5D Return (%)": round(chg_5d, 2),
                  "1M Return (%)": round(chg_1m, 2),
              })

          if sector_rows:
            df_sectors = pd.DataFrame(sector_rows)
            df_sectors = df_sectors.sort_values(by="5D Return (%)", ascending=False).reset_index(drop=True)

            def color_returns(val):
              color = "#0ecb81" if val >= 0 else "#f6465d"
              return f"color: {color}; font-weight: bold;"

            # Version-safe Pandas Styler check (.map replaces applymap in newer versions)
            styler_obj = df_sectors.style
            if hasattr(styler_obj, "map"):
              styled_df = styler_obj.map(color_returns, subset=["1D Return (%)", "5D Return (%)", "1M Return (%)"])
            else:
              styled_df = styler_obj.applymap(color_returns, subset=["1D Return (%)", "5D Return (%)", "1M Return (%)"])

            st.dataframe(styled_df, use_container_width=True, height=450)

            st.markdown(
                """
                <div style="background-color: #050505; border: 1px solid #1a1a1a; padding: 15px; border-radius: 4px; font-size: 13px; color: #b7bdc6; margin-top: 15px;">
                    <b>Rotation Insights:</b> Use this matrix to spot institutional momentum. Leading 5D and 1M returns in Cyclical/Discretionary sectors indicate risk-on behavior, while outperformance in Staples and Utilities signals a defensive flight to safety.
                </div>
                """,
                unsafe_allow_html=True,
            )
          else:
            st.warning("Unable to fetch sector data at the moment.")
        except Exception as e:
          st.error(f"Error loading sector rotation matrix: {e}")
