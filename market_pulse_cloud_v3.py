from html import escape

import feedparser
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
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


@st.cache_data(ttl=10 * 60, show_spinner=False)
def get_news():
    news = []
    feeds = [
        "https://feeds.economictimes.indiatimes.com/markets/stocks",
        "https://www.moneycontrol.com/rss/stocks.xml",
    ]
    for url in feeds:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]:
                news.append({"title": str(entry.get("title", "")), "source": url.split("/")[2]})
        except Exception:
            pass
    return news[:12]


def get_series(data, column):
    if data is None or column not in data:
        return None

    series = data[column]
    if isinstance(series, pd.DataFrame):
        series = series.iloc[:, 0]
    return pd.to_numeric(series.squeeze(), errors="coerce").dropna()


def sentiment(text):
    text = str(text).lower()
    pos = sum(text.count(w) for w in ["breakout", "surge", "growth", "profit", "bullish", "up"])
    neg = sum(text.count(w) for w in ["crash", "fall", "weak", "drop", "bearish", "down"])
    score = min(10, max(-10, (pos - neg) * 2))
    if score >= 4:
        return score, "BULLISH", "#6ee7b7"
    if score <= -4:
        return score, "BEARISH", "#fca5a5"
    return score, "NEUTRAL", "#fcd34d"


def wma(close, period=20):
    if close is None or len(close) < period:
        return None
    weights = np.arange(1, period + 1)
    return close.rolling(period).apply(lambda x: np.sum(weights * x) / np.sum(weights), raw=False)


def rsi(close, period=14):
    if close is None or len(close) < period:
        return None
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = -delta.where(delta < 0, 0).rolling(period).mean()
    relative_strength = gain / loss.replace(0, np.nan)
    return (100 - (100 / (1 + relative_strength))).fillna(50)


def backtest():
    data = get_data()
    close = get_series(data, "Close")
    if close is None or len(close) < 40:
        return None

    weighted_ma = wma(close, 20)
    momentum = rsi(close, 14)
    if weighted_ma is None or momentum is None:
        return None

    wins = 0
    total = 0
    returns = []
    for i in range(30, len(close) - 1):
        buy_signal = close.iloc[i] > weighted_ma.iloc[i] and momentum.iloc[i] < 70
        sell_signal = close.iloc[i] < weighted_ma.iloc[i] and momentum.iloc[i] > 30
        signal = 1 if buy_signal else -1 if sell_signal else 0

        if signal != 0:
            daily_return = (close.iloc[i + 1] - close.iloc[i]) / close.iloc[i]
            strategy_return = daily_return if signal == 1 else -daily_return
            returns.append(strategy_return)
            wins += strategy_return > 0
            total += 1

    if total == 0:
        return None
    return {"ret": sum(returns) * 100, "wr": (wins / total) * 100, "trades": total}


with st.sidebar:
    st.markdown('<div class="title">Market Pulse</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Sentiment + Technical</div>', unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("### News")
    if st.button("Fetch Live News", use_container_width=True, key="fetch"):
        st.session_state.news = get_news()
    st.markdown("### Paste Headline")
    st.session_state.headline = st.text_area(
        "Enter headline:",
        st.session_state.headline,
        height=80,
        label_visibility="collapsed",
    )

st.markdown('<div class="title">Market Pulse</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Real-time Sentiment + Technical</div>', unsafe_allow_html=True)
st.info("Educational only. Delayed data (15-20 min), keyword sentiment (60% accurate).")

st.markdown('<div class="section">Market</div>', unsafe_allow_html=True)
data = get_data()
if data is not None:
    try:
        close_series = get_series(data, "Close")
        volume_series = get_series(data, "Volume")
        if close_series is None or len(close_series) < 2:
            raise ValueError("Not enough close-price data returned by Yahoo Finance.")

        cur = float(close_series.iloc[-1])
        prv = float(close_series.iloc[-2])
        ch = cur - prv
        pct = (ch / prv * 100) if prv != 0 else 0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Nifty50", f"{cur:,.0f}", f"{ch:+.2f} ({pct:+.2f}%)")
        c2.metric("52W High", f"{float(close_series.max()):,.0f}")
        c3.metric("52W Low", f"{float(close_series.min()):,.0f}")
        vol_mean = float(volume_series.mean()) if volume_series is not None and len(volume_series) else 0
        c4.metric("Avg Vol", f"{vol_mean / 1e6:.1f}M")
    except Exception as exc:
        st.error(f"Data error: {exc}")
else:
    st.warning("Could not load Nifty50 data from Yahoo Finance. Check your internet connection and try again.")

st.markdown("---")
st.markdown('<div class="section">Technical</div>', unsafe_allow_html=True)
if data is not None and len(data) >= 40:
    close = get_series(data, "Close")
    weighted_ma = wma(close, 20)
    momentum = rsi(close, 14)

    if weighted_ma is not None and momentum is not None:
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.65, 0.35])
        fig.add_trace(
            go.Scatter(x=close.index, y=close, name="Close", line=dict(color="#a5b4fc", width=2)),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Scatter(x=weighted_ma.index, y=weighted_ma, name="WMA(20)", line=dict(color="#ec4899", width=1, dash="dash")),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Scatter(x=momentum.index, y=momentum, name="RSI", line=dict(color="#6ee7b7", width=2)),
            row=2,
            col=1,
        )
        fig.add_hline(70, line_dash="dash", line_color="rgba(252,165,165,0.5)", row=2, col=1)
        fig.add_hline(30, line_dash="dash", line_color="rgba(110,231,183,0.5)", row=2, col=1)
        fig.update_layout(
            height=600,
            hovermode="x unified",
            plot_bgcolor="rgba(30,27,75,0.3)",
            paper_bgcolor="rgba(10,14,39,0)",
            font=dict(color="#a5b4fc"),
        )
        st.plotly_chart(fig, use_container_width=True)

        c1, c2, c3 = st.columns(3)
        try:
            latest_rsi = float(momentum.iloc[-1])
            status = "Overbought" if latest_rsi > 70 else "Oversold" if latest_rsi < 30 else "Neutral"
            c1.metric("RSI", f"{latest_rsi:.0f}", status)

            latest_wma = float(weighted_ma.iloc[-1])
            latest_close = float(close.iloc[-1])
            c2.metric("Price vs WMA", "Above" if latest_close > latest_wma else "Below")
            c3.metric("Status", "OK")
        except Exception as exc:
            st.error(f"Indicator error: {exc}")

st.markdown("---")
st.markdown('<div class="section">Sentiment</div>', unsafe_allow_html=True)

headlines = []
if st.session_state.news:
    headlines = st.session_state.news
    st.success(f"Got {len(headlines)} headlines")
elif st.session_state.headline.strip():
    headlines = [{"title": st.session_state.headline, "source": "Manual"}]
    st.success("Analyzing...")

if headlines:
    sentiments = [sentiment(h["title"]) for h in headlines]
    avg = np.mean([s[0] for s in sentiments])
    signal = "BUY" if avg >= 4 else "SELL" if avg <= -4 else "HOLD"
    signal_class = "buy" if avg >= 4 else "sell" if avg <= -4 else "hold"

    c1, c2 = st.columns([1.5, 2])
    with c1:
        st.markdown(
            f'<div class="card {signal_class}"><div>Signal</div><div class="signal">{signal}</div><div>{avg:+.1f}/10</div></div>',
            unsafe_allow_html=True,
        )
    with c2:
        bullish = sum(1 for s in sentiments if s[1] == "BULLISH")
        bearish = sum(1 for s in sentiments if s[1] == "BEARISH")
        neutral = sum(1 for s in sentiments if s[1] == "NEUTRAL")
        st.markdown(
            f'<div class="card"><div><strong>Sentiment Split</strong></div><div style="margin-top: 8px;">Bullish: {bullish} | Neutral: {neutral} | Bearish: {bearish}</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("**Headlines Analyzed:**")
    for headline, sent in zip(headlines[:10], sentiments[:10]):
        title = escape(headline["title"])
        source = escape(headline["source"])
        st.markdown(
            f'<div style="background: rgba(30,27,75,0.5); border-left: 3px solid {sent[2]}; padding: 12px; margin-bottom: 8px; border-radius: 8px;"><strong>{title}</strong><br><small style="color: #a5b4fc;">Source: {source} | {sent[1]} ({sent[0]:+.1f})</small></div>',
            unsafe_allow_html=True,
        )
else:
    st.info("Fetch news or paste a headline in the sidebar.")

st.markdown("---")
st.markdown('<div class="section">Backtest</div>', unsafe_allow_html=True)
if st.button("Run Backtest", use_container_width=True):
    with st.spinner("Testing..."):
        st.session_state.bt = backtest()

if st.session_state.bt:
    c1, c2, c3 = st.columns(3)
    c1.metric("Return", f"{st.session_state.bt['ret']:.2f}%")
    c2.metric("Win Rate", f"{st.session_state.bt['wr']:.1f}%")
    c3.metric("Signals", f"{st.session_state.bt['trades']}")

st.markdown("---")
st.markdown(
    '<div style="text-align: center; color: #a5b4fc; font-size: 10px; margin-top: 20px;">MARKET PULSE - EDUCATIONAL ONLY</div>',
    unsafe_allow_html=True,
)
