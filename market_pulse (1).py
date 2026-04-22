import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import feedparser

st.set_page_config(page_title="Market Pulse", layout="wide")

if "news_list" not in st.session_state:
    st.session_state.news_list = []
if "headline_text" not in st.session_state:
    st.session_state.headline_text = ""
if "backtest_data" not in st.session_state:
    st.session_state.backtest_data = None

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@700;800&family=Inter:wght@400;500;600&display=swap');

.stApp {
    background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 50%, #0d1629 100%);
    color: #e0e7ff;
}

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f1629 0%, #1a1f3a 100%);
    border-right: 1px solid rgba(99, 102, 241, 0.2);
}

section[data-testid="stSidebar"] * {
    color: #e0e7ff !important;
}

.title {
    font-family: 'Poppins', sans-serif;
    font-size: 48px;
    font-weight: 800;
    background: linear-gradient(135deg, #6366f1, #a78bfa, #ec4899);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin: 0;
}

.subtitle {
    color: #a5b4fc;
    letter-spacing: 2px;
    text-transform: uppercase;
    font-size: 12px;
    font-weight: 600;
}

.card {
    background: rgba(30, 27, 75, 0.6);
    border: 1px solid rgba(99, 102, 241, 0.3);
    border-radius: 16px;
    padding: 20px;
}

.buy { border-color: rgba(16, 185, 129, 0.5); color: #6ee7b7; }
.sell { border-color: rgba(239, 68, 68, 0.5); color: #fca5a5; }
.hold { border-color: rgba(245, 158, 11, 0.5); color: #fcd34d; }

.signal {
    font-family: 'Poppins', sans-serif;
    font-size: 42px;
    font-weight: 800;
    margin: 12px 0;
}

.section {
    font-family: 'Poppins', sans-serif;
    font-size: 22px;
    font-weight: 700;
    color: #c7d2fe;
    margin: 24px 0 16px 0;
    border-bottom: 2px solid rgba(99, 102, 241, 0.3);
    padding-bottom: 8px;
}

.metric {
    background: rgba(30, 27, 75, 0.4);
    border: 1px solid rgba(99, 102, 241, 0.2);
    border-radius: 12px;
    padding: 16px;
    text-align: center;
}

.metric-label {
    font-size: 11px;
    color: #a5b4fc;
    text-transform: uppercase;
    letter-spacing: 1px;
    font-weight: 600;
    margin-bottom: 8px;
}

.metric-value {
    font-family: 'Poppins', sans-serif;
    font-size: 24px;
    font-weight: 700;
    color: #6366f1;
}

.disclaimer {
    background: rgba(239, 68, 68, 0.15);
    border: 1px solid rgba(239, 68, 68, 0.4);
    border-radius: 12px;
    padding: 16px;
    color: #fca5a5;
    font-size: 12px;
    line-height: 1.6;
}

.stButton > button {
    background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
}

.stTextArea > div > div > textarea {
    background: rgba(30, 27, 75, 0.6) !important;
    color: #e0e7ff !important;
    border: 1px solid rgba(99, 102, 241, 0.3) !important;
}
</style>
""", unsafe_allow_html=True)

def get_nifty():
    try:
        d = yf.download("^NSEI", period="90d", progress=False, timeout=10)
        return d if d is not None and len(d) >= 30 else None
    except:
        return None

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

def macd(close):
    if len(close) < 26:
        return None, None
    m = close.ewm(12).mean() - close.ewm(26).mean()
    return m, m.ewm(9).mean()

def get_news():
    feeds = [
        "https://feeds.economictimes.indiatimes.com/markets/stocks",
        "https://www.moneycontrol.com/rss/stocks.xml",
    ]
    n = []
    for u in feeds:
        try:
            p = feedparser.parse(u)
            for e in p.entries[:5]:
                n.append({"title": e.get("title", ""), "source": u.split("/")[2]})
        except:
            pass
    return n[:12]

def sent(text):
    t = text.lower()
    pos = sum(t.count(w) for w in ["breakout", "surge", "growth", "profit", "bullish", "up", "gain", "rally"])
    neg = sum(t.count(w) for w in ["crash", "fall", "weak", "drop", "bearish", "down", "loss", "decline"])
    s = min(10, max(-10, (pos - neg) * 2))
    if s >= 4:
        return s, "BULLISH", "#6ee7b7"
    elif s <= -4:
        return s, "BEARISH", "#fca5a5"
    return s, "NEUTRAL", "#fcd34d"

def bt():
    d = get_nifty()
    if d is None or len(d) < 40:
        return None
    c = d['Close']
    w = wma(c, 20)
    r = rsi(c, 14)
    if w is None or r is None:
        return None
    wins, total, rets = 0, 0, []
    for i in range(30, len(c) - 1):
        sig = 1 if c.iloc[i] > w.iloc[i] and r.iloc[i] < 70 else -1 if c.iloc[i] < w.iloc[i] and r.iloc[i] > 30 else 0
        if sig != 0:
            rt = (c.iloc[i+1] - c.iloc[i]) / c.iloc[i]
            rt = rt if sig == 1 else -rt
            rets.append(rt)
            if rt > 0: wins += 1
            total += 1
    return None if total == 0 else {"return": sum(rets)*100, "win_rate": (wins/total)*100, "trades": total}

with st.sidebar:
    st.markdown('<div class="title">Market Pulse</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Sentiment + Technical</div>', unsafe_allow_html=True)
    st.markdown("---")
    
    st.markdown("### 📰 News & Sentiment")
    
    if st.button("🔄 Fetch Live News", use_container_width=True, key="fetch_news"):
        st.session_state.news_list = get_news()
        st.success(f"✓ {len(st.session_state.news_list)} headlines")
    
    st.markdown("**OR**")
    st.markdown("### ✍️ Paste Headline")
    st.session_state.headline_text = st.text_area("Enter headline:", value=st.session_state.headline_text, height=100, label_visibility="collapsed", key="paste_headline")

st.markdown('<div class="title">Market Pulse</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Real-time Sentiment + Technical</div>', unsafe_allow_html=True)
st.markdown('<div class="disclaimer">⚠️ EDUCATIONAL ONLY: Delayed data (15-20 min), keyword sentiment (60% accurate).</div>', unsafe_allow_html=True)

st.markdown('<div class="section">📊 Market</div>', unsafe_allow_html=True)
d = get_nifty()
if d is not None:
    cur, prv = d['Close'].iloc[-1], d['Close'].iloc[-2]
    ch, pct = cur - prv, (ch / prv * 100)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="metric"><div class="metric-label">Nifty50</div><div class="metric-value">{cur:,.0f}</div><div style="color: {\'#6ee7b7\' if ch > 0 else \'#fca5a5\'}; font-size: 12px; margin-top: 4px;">{"▲" if ch > 0 else "▼"} {abs(pct):.2f}%</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric"><div class="metric-label">52W High</div><div class="metric-value">{d[\'Close\'].max():,.0f}</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="metric"><div class="metric-label">52W Low</div><div class="metric-value">{d[\'Close\'].min():,.0f}</div></div>', unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div class="metric"><div class="metric-label">Avg Vol</div><div class="metric-value">{d[\'Volume\'].mean()/1e6:.1f}M</div></div>', unsafe_allow_html=True)

st.markdown("---")
st.markdown('<div class="section">📈 Technical</div>', unsafe_allow_html=True)
if d is not None and len(d) >= 40:
    w, r, m, s = wma(d['Close'], 20), rsi(d['Close'], 14), macd(d['Close'])
    if w is not None and r is not None:
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.65, 0.35])
        fig.add_trace(go.Scatter(x=d.index, y=d['Close'], name='Close', line=dict(color='#a5b4fc', width=2)), row=1, col=1)
        fig.add_trace(go.Scatter(x=w.index, y=w, name='WMA(20)', line=dict(color='#ec4899', width=1, dash='dash')), row=1, col=1)
        fig.add_trace(go.Scatter(x=r.index, y=r, name='RSI', line=dict(color='#6ee7b7', width=2)), row=2, col=1)
        fig.add_hline(70, line_dash="dash", line_color="rgba(252, 165, 165, 0.5)", row=2, col=1)
        fig.add_hline(30, line_dash="dash", line_color="rgba(110, 231, 183, 0.5)", row=2, col=1)
        fig.update_layout(height=600, hovermode='x unified', plot_bgcolor='rgba(30, 27, 75, 0.3)', paper_bgcolor='rgba(10, 14, 39, 0)', font=dict(color='#a5b4fc'))
        st.plotly_chart(fig, use_container_width=True)
        col1, col2, col3 = st.columns(3)
        with col1:
            rr = r.iloc[-1]
            st = "Overbought" if rr > 70 else "Oversold" if rr < 30 else "Neutral"
            c = "#fca5a5" if rr > 70 else "#6ee7b7" if rr < 30 else "#a5b4fc"
            st.markdown(f'<div class="metric"><div class="metric-label">RSI</div><div style="color: {c}; font-size: 18px; font-weight: 700;">{st}</div></div>', unsafe_allow_html=True)
        with col2:
            ww, cc = w.iloc[-1], d['Close'].iloc[-1]
            st = "Above" if cc > ww else "Below"
            c = "#6ee7b7" if cc > ww else "#fca5a5"
            st.markdown(f'<div class="metric"><div class="metric-label">WMA</div><div style="color: {c}; font-size: 18px; font-weight: 700;">{st}</div></div>', unsafe_allow_html=True)
        with col3:
            if m[0] is not None and m[1] is not None and len(m[0]) > 0 and len(m[1]) > 0:
                st = "Bullish" if m[0].iloc[-1] > m[1].iloc[-1] else "Bearish"
                c = "#6ee7b7" if m[0].iloc[-1] > m[1].iloc[-1] else "#fca5a5"
            else:
                st, c = "N/A", "#a5b4fc"
            st.markdown(f'<div class="metric"><div class="metric-label">MACD</div><div style="color: {c}; font-size: 18px; font-weight: 700;">{st}</div></div>', unsafe_allow_html=True)

st.markdown("---")
st.markdown('<div class="section">💭 Sentiment</div>', unsafe_allow_html=True)
h = []
if st.session_state.news_list:
    h = st.session_state.news_list
    st.info(f"📡 {len(h)} headlines from live feeds")
elif st.session_state.headline_text.strip():
    h = [{"title": st.session_state.headline_text, "source": "Manual"}]
    st.info("✓ Analyzing your headline")

if h:
    sents = [sent(hh["title"]) for hh in h]
    avg = np.mean([ss[0] for ss in sents])
    sig = "BUY" if avg >= 4 else "SELL" if avg <= -4 else "HOLD"
    sgc = "buy" if avg >= 4 else "sell" if avg <= -4 else "hold"
    col1, col2 = st.columns([1.5, 2])
    with col1:
        st.markdown(f'<div class="card {sgc}"><div style="font-size: 12px;">Signal</div><div class="signal">{sig}</div><div style="font-size: 12px;">Score: {avg:+.1f}/10</div></div>', unsafe_allow_html=True)
    with col2:
        bl = sum(1 for ss in sents if ss[1] == "BULLISH")
        be = sum(1 for ss in sents if ss[1] == "BEARISH")
        ne = sum(1 for ss in sents if ss[1] == "NEUTRAL")
        st.markdown(f'<div class="card"><div style="font-size: 12px; color: #a5b4fc; margin-bottom: 12px;">SPLIT</div><div style="display: flex; gap: 12px;"><div style="flex: 1; text-align: center;"><div style="color: #6ee7b7; font-size: 18px; font-weight: 700;">{bl}</div><div style="font-size: 10px; color: #a5b4fc;">Bull</div></div><div style="flex: 1; text-align: center;"><div style="color: #fcd34d; font-size: 18px; font-weight: 700;">{ne}</div><div style="font-size: 10px; color: #a5b4fc;">Neutral</div></div><div style="flex: 1; text-align: center;"><div style="color: #fca5a5; font-size: 18px; font-weight: 700;">{be}</div><div style="font-size: 10px; color: #a5b4fc;">Bear</div></div></div></div>', unsafe_allow_html=True)
    for hh, ss in zip(h[:10], sents[:10]):
        st.markdown(f'<div style="background: rgba(30, 27, 75, 0.5); border-left: 3px solid {ss[2]}; padding: 12px; border-radius: 8px; margin-bottom: 8px;"><div style="color: #e0e7ff; font-weight: 600;">{hh["title"]}</div><div style="display: flex; justify-content: space-between; margin-top: 6px;"><div style="font-size: 11px; color: #a5b4fc;">📍 {hh["source"]}</div><div style="color: {ss[2]}; font-weight: 700;">{ss[1]} ({ss[0]:+.1f})</div></div></div>', unsafe_allow_html=True)
else:
    st.info("👈 Fetch news or paste a headline")

st.markdown("---")
st.markdown('<div class="section">🧪 Backtest</div>', unsafe_allow_html=True)
if st.button("Run Backtest", use_container_width=True, key="backtest"):
    with st.spinner("Testing..."):
        res = bt()
        st.session_state.backtest_data = res if res else None

if st.session_state.backtest_data:
    r = st.session_state.backtest_data
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f'<div class="metric"><div class="metric-label">Return</div><div class="metric-value" style="color: {\'#6ee7b7\' if r["return"] > 0 else \'#fca5a5\';}>{r["return"]:.2f}%</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric"><div class="metric-label">Win %</div><div class="metric-value">{r["win_rate"]:.1f}%</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="metric"><div class="metric-label">Signals</div><div class="metric-value">{r["trades"]}</div></div>', unsafe_allow_html=True)

st.markdown('<div style="text-align: center; color: #a5b4fc; font-size: 10px; letter-spacing: 2px; margin-top: 20px;">MARKET PULSE • EDUCATIONAL ONLY</div>', unsafe_allow_html=True)
