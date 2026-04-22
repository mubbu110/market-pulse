from html import escape

import feedparser
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
import yfinance as yf
from plotly.subplots import make_subplots


TICKER = "^NSEI"

st.set_page_config(page_title="Market Pulse", layout="wide")

if "news" not in st.session_state:
    st.session_state.news = []
if "headline" not in st.session_state:
    st.session_state.headline = ""
if "bt" not in st.session_state:
    st.session_state.bt = None

st.markdown(
    """
<style>
.stApp { background: #0a0e27; color: #e0e7ff; }
section[data-testid="stSidebar"] { background: #0f1629; }
.title { font-size: 48px; font-weight: 800; color: #a78bfa; }
.subtitle { color: #a5b4fc; letter-spacing: 2px; font-size: 12px; text-transform: uppercase; }
.card { background: rgba(30,27,75,0.6); border: 1px solid rgba(99,102,241,0.3); border-radius: 16px; padding: 20px; }
.buy { border-color: rgba(16,185,129,0.5); color: #6ee7b7; }
.sell { border-color: rgba(239,68,68,0.5); color: #fca5a5; }
.hold { border-color: rgba(245,158,11,0.5); color: #fcd34d; }
.signal { font-size: 42px; font-weight: 800; margin: 12px 0; }
.section { font-size: 22px; font-weight: 700; color: #c7d2fe; margin: 24px 0 16px; border-bottom: 2px solid rgba(99,102,241,0.3); padding-bottom: 8px; }
.stButton > button { background: linear-gradient(135deg, #6366f1, #8b5cf6) !important; }
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_data(ttl=15 * 60, show_spinner=False)
def get_data():
    data = fetch_yahoo_chart_data()
    if data is not None:
        return data

    data = fetch_yfinance_data()
    if data is not None:
        return data

    return None


def fetch_yahoo_chart_data():
    try:
        url = "https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI"
        response = requests.get(
            url,
            params={"range": "1y", "interval": "1d", "events": "history"},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        result = payload["chart"]["result"][0]
        timestamps = result.get("timestamp") or []
        quote = result["indicators"]["quote"][0]

        if not timestamps or not quote.get("close"):
            return None

        data = pd.DataFrame(
            {
                "Open": quote.get("open"),
                "High": quote.get("high"),
                "Low": quote.get("low"),
                "Close": quote.get("close"),
                "Volume": quote.get("volume"),
            },
            index=pd.to_datetime(timestamps, unit="s", utc=True).tz_convert("Asia/Kolkata").tz_localize(None),
        )
        data = data.apply(pd.to_numeric, errors="coerce").dropna(subset=["Close"])
        data["Volume"] = data["Volume"].fillna(0)
        return data if len(data) >= 30 else None
    except Exception:
        return None


def fetch_yfinance_data():
    try:
        data = yf.download(
            TICKER,
            period="1y",
            interval="1d",
            auto_adjust=False,
            progress=False,
            timeout=15,
