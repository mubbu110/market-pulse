import streamlit as st
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import feedparser

st.set_page_config(page_title="Market Pulse", layout="wide")

if "news" not in st.session_state:
    st.session_state.news = []
if "headline" not in st.session_state:
    st.session_state.headline = ""
if "bt" not in st.session_state:
    st.session_state.bt = None

st.markdown("""<style>
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
</style>""", unsafe_allow_html=True)

def get_data():
    try:
        d = yf.download("^NSEI", period="90d", progress=False, timeout=10)
        return d if d is not None and len(d) >= 30 else None
    except:
        return None

def get_news():
    news = []
    feeds = ["https://feeds.economictimes.indiatimes.com/markets/stocks", "https://www.moneycontrol.com/rss/stocks.xml"]
    for url in feeds:
        try:
            f = feedparser.parse(url)
            for e in f.entries[:5]:
                news.append({"title": str(e.get("title", "")), "source": url.split("/")[2]})
        except:
            pass
    return news[:12]

def sentiment(text):
    t = str(text).lower()
    pos = sum(t.count(w) for w in ["breakout", "surge", "growth", "profit", "bullish", "up"])
    neg = sum(t.count(w) for w in ["crash", "fall", "weak", "drop", "bearish", "down"])
    s = min(10, max(-10, (pos - neg) * 2))
    return (s, "BULLISH", "#6ee7b7") if s >= 4 else (s, "BEARISH", "#fca5a5") if s <= -4 else (s, "NEUTRAL", "#fcd34d")

def wma(close, p=20):
    if len(close) < p:
        return None
    w = np.arange(1, p+1)
    return close.rolling(p).apply(lambda x: np.sum(w*x)/np.sum(w), raw=False)

def rsi(close, p=14):
    if len(close) < p:
        return None
    d = close.diff()
    g = d.where(d>0, 0).rolling(p).mean()
    l = -d.where(d<0, 0).rolling(p).mean()
    return 100 - (100/(1 + g/l))

def backtest():
    d = get_data()
    if d is None or len(d) < 40:
        return None
    c = d['Close']
    w = wma(c, 20)
    r = rsi(c, 14)
    if w is None or r is None:
        return None
    wins = total = 0
    rets = []
    for i in range(30, len(c) - 1):
        sig = 1 if c.iloc[i] > w.iloc[i] and r.iloc[i] < 70 else (-1 if c.iloc[i] < w.iloc[i] and r.iloc[i] > 30 else 0)
        if sig != 0:
            ret = (c.iloc[i+1] - c.iloc[i]) / c.iloc[i]
            ret = ret if sig == 1 else -ret
            rets.append(ret)
            if ret > 0:
                wins += 1
            total += 1
    return {"ret": sum(rets)*100, "wr": (wins/total)*100, "trades": total} if total > 0 else None

with st.sidebar:
    st.markdown('<div class="title">Market Pulse</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Sentiment + Technical</div>', unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("### 📰 News")
    if st.button("Fetch Live News", use_container_width=True, key="fetch"):
        st.session_state.news = get_news()
    st.markdown("### ✍️ Paste Headline")
    st.session_state.headline = st.text_area("Enter headline:", st.session_state.headline, height=80, label_visibility="collapsed")

st.markdown('<div class="title">Market Pulse</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Real-time Sentiment + Technical</div>', unsafe_allow_html=True)
st.info("⚠️ Educational only. Delayed data (15-20 min), keyword sentiment (60% accurate).")

st.markdown('<div class="section">📊 Market</div>', unsafe_allow_html=True)
data = get_data()
if data is not None:
    cur = float(data['Close'].iloc[-1])
    prv = float(data['Close'].iloc[-2])
    ch = cur - prv
    pct = (ch / prv * 100) if prv != 0 else 0
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Nifty50", f"{cur:,.0f}", f"{ch:+.2f} ({pct:+.2f}%)")
    c2.metric("52W High", f"{float(data['Close'].max()):,.0f}")
    c3.metric("52W Low", f"{float(data['Close'].min()):,.0f}")
    c4.metric("Avg Vol", f"{float(data['Volume'].mean())/1e6:.1f}M")

st.markdown("---")
st.markdown('<div class="section">📈 Technical</div>', unsafe_allow_html=True)
if data is not None and len(data) >= 40:
    w = wma(data['Close'], 20)
    r = rsi(data['Close'], 14)
    if w is not None and r is not None:
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.65, 0.35])
        fig.add_trace(go.Scatter(x=data.index, y=data['Close'], name='Close', line=dict(color='#a5b4fc', width=2)), row=1, col=1)
        fig.add_trace(go.Scatter(x=w.index, y=w, name='WMA(20)', line=dict(color='#ec4899', width=1, dash='dash')), row=1, col=1)
        fig.add_trace(go.Scatter(x=r.index, y=r, name='RSI', line=dict(color='#6ee7b7', width=2)), row=2, col=1)
        fig.add_hline(70, line_dash="dash", line_color="rgba(252,165,165,0.5)", row=2, col=1)
        fig.add_hline(30, line_dash="dash", line_color="rgba(110,231,183,0.5)", row=2, col=1)
        fig.update_layout(height=600, hovermode='x unified', plot_bgcolor='rgba(30,27,75,0.3)', paper_bgcolor='rgba(10,14,39,0)', font=dict(color='#a5b4fc'))
        st.plotly_chart(fig, use_container_width=True)
        
        c1, c2, c3 = st.columns(3)
        rr = float(r.iloc[-1])
        status = "Overbought" if rr > 70 else "Oversold" if rr < 30 else "Neutral"
        c1.metric("RSI", f"{rr:.0f}", status)
        ww = float(w.iloc[-1])
        cc = float(data['Close'].iloc[-1])
        c2.metric("Price vs WMA", "Above" if cc > ww else "Below")
        c3.metric("Status", "OK")

st.markdown("---")
st.markdown('<div class="section">💭 Sentiment</div>', unsafe_allow_html=True)

headlines = []
if st.session_state.news:
    headlines = st.session_state.news
    st.success(f"Got {len(headlines)} headlines")
elif st.session_state.headline.strip():
    headlines = [{"title": st.session_state.headline, "source": "Manual"}]
    st.success("Analyzing...")

if headlines:
    sents = [sentiment(h["title"]) for h in headlines]
    avg = np.mean([s[0] for s in sents])
    sig = "BUY" if avg >= 4 else "SELL" if avg <= -4 else "HOLD"
    sgc = "buy" if avg >= 4 else "sell" if avg <= -4 else "hold"
    
    c1, c2 = st.columns([1.5, 2])
    with c1:
        st.markdown(f'<div class="card {sgc}"><div>Signal</div><div class="signal">{sig}</div><div>{avg:+.1f}/10</div></div>', unsafe_allow_html=True)
    with c2:
        bl = sum(1 for s in sents if s[1] == "BULLISH")
        be = sum(1 for s in sents if s[1] == "BEARISH")
        ne = sum(1 for s in sents if s[1] == "NEUTRAL")
        st.markdown(f'<div class="card"><div><strong>Sentiment Split</strong></div><div style="margin-top: 8px;">Bullish: {bl} | Neutral: {ne} | Bearish: {be}</div></div>', unsafe_allow_html=True)
    
    st.markdown("**Headlines Analyzed:**")
    for h, s in zip(headlines[:10], sents[:10]):
        st.markdown(f'<div style="background: rgba(30,27,75,0.5); border-left: 3px solid {s[2]}; padding: 12px; margin-bottom: 8px; border-radius: 8px;"><strong>{h["title"]}</strong><br><small style="color: #a5b4fc;">Source: {h["source"]} | {s[1]} ({s[0]:+.1f})</small></div>', unsafe_allow_html=True)
else:
    st.info("👈 Fetch news or paste headline in sidebar")

st.markdown("---")
st.markdown('<div class="section">🧪 Backtest</div>', unsafe_allow_html=True)
if st.button("Run Backtest", use_container_width=True):
    with st.spinner("Testing..."):
        st.session_state.bt = backtest()

if st.session_state.bt:
    c1, c2, c3 = st.columns(3)
    c1.metric("Return", f"{st.session_state.bt['ret']:.2f}%")
    c2.metric("Win Rate", f"{st.session_state.bt['wr']:.1f}%")
    c3.metric("Signals", f"{st.session_state.bt['trades']}")

st.markdown("---")
st.markdown('<div style="text-align: center; color: #a5b4fc; font-size: 10px; margin-top: 20px;">MARKET PULSE • EDUCATIONAL ONLY</div>', unsafe_allow_html=True)
