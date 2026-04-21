import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import feedparser
import requests
from datetime import datetime, timedelta
import time

# ============================================================================
# PAGE CONFIG
# ============================================================================
st.set_page_config(
    page_title="Market Pulse",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================
if "news_cache" not in st.session_state:
    st.session_state.news_cache = []

if "user_headline" not in st.session_state:
    st.session_state.user_headline = ""

if "backtest_result" not in st.session_state:
    st.session_state.backtest_result = None

if "input_method" not in st.session_state:
    st.session_state.input_method = "Fetch Live News"

# ============================================================================
# STYLING
# ============================================================================
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

.main-title {
    font-family: 'Poppins', sans-serif;
    font-size: 52px;
    font-weight: 800;
    background: linear-gradient(135deg, #6366f1, #a78bfa, #ec4899);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 8px;
}

.subtitle {
    font-size: 14px;
    color: #a5b4fc;
    letter-spacing: 2px;
    text-transform: uppercase;
    font-weight: 600;
}

.pulse-card {
    background: rgba(30, 27, 75, 0.6);
    border: 1px solid rgba(99, 102, 241, 0.3);
    border-radius: 16px;
    padding: 24px;
    backdrop-filter: blur(10px);
}

.signal-buy {
    background: linear-gradient(135deg, rgba(16, 185, 129, 0.2), rgba(52, 211, 153, 0.1));
    border: 1.5px solid rgba(16, 185, 129, 0.5);
    color: #6ee7b7;
}

.signal-hold {
    background: linear-gradient(135deg, rgba(245, 158, 11, 0.2), rgba(251, 191, 36, 0.1));
    border: 1.5px solid rgba(245, 158, 11, 0.5);
    color: #fcd34d;
}

.signal-sell {
    background: linear-gradient(135deg, rgba(239, 68, 68, 0.2), rgba(252, 165, 165, 0.1));
    border: 1.5px solid rgba(239, 68, 68, 0.5);
    color: #fca5a5;
}

.signal-value {
    font-family: 'Poppins', sans-serif;
    font-size: 48px;
    font-weight: 800;
    margin: 12px 0;
}

.metric-box {
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
}

.metric-value {
    font-family: 'Poppins', sans-serif;
    font-size: 24px;
    font-weight: 700;
    color: #6366f1;
    margin-top: 8px;
}

.section-title {
    font-family: 'Poppins', sans-serif;
    font-size: 24px;
    font-weight: 700;
    color: #c7d2fe;
    margin: 30px 0 20px 0;
    border-bottom: 2px solid rgba(99, 102, 241, 0.3);
    padding-bottom: 12px;
}

.disclaimer {
    background: rgba(239, 68, 68, 0.15);
    border: 1px solid rgba(239, 68, 68, 0.4);
    border-radius: 12px;
    padding: 16px;
    color: #fca5a5;
    font-size: 12px;
    line-height: 1.6;
    margin: 20px 0;
}

.stButton > button {
    background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
}

.stRadio > label {
    color: #e0e7ff !important;
}

.stTextArea > div > div > textarea {
    background: rgba(30, 27, 75, 0.6) !important;
    color: #e0e7ff !important;
    border: 1px solid rgba(99, 102, 241, 0.3) !important;
    border-radius: 12px !important;
}
</style>
""", unsafe_allow_html=True)

# ============================================================================
# DATA FETCHING & TECHNICAL ANALYSIS
# ============================================================================

@st.cache_data(ttl=300)
def fetch_nifty_data(days=90):
    """Fetch Nifty50 data with error handling"""
    try:
        data = yf.download("^NSEI", period=f"{days}d", progress=False, timeout=10)
        if data is None or len(data) < 30:
            return None
        return data
    except Exception as e:
        st.error(f"Data fetch failed: {str(e)}")
        return None

def calculate_wma(data, period=20):
    """Weighted Moving Average"""
    if len(data) < period:
        return pd.Series(dtype=float)
    weights = np.arange(1, period + 1)
    wma = data['Close'].rolling(window=period).apply(
        lambda x: np.sum(weights * x) / np.sum(weights), raw=False
    )
    return wma

def calculate_rsi(data, period=14):
    """Relative Strength Index"""
    if len(data) < period:
        return pd.Series(dtype=float)
    close = data['Close']
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_macd(data, fast=12, slow=26, signal=9):
    """MACD Indicator"""
    if len(data) < slow:
        return pd.Series(dtype=float), pd.Series(dtype=float), pd.Series(dtype=float)
    ema_fast = data['Close'].ewm(span=fast).mean()
    ema_slow = data['Close'].ewm(span=slow).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def calculate_bollinger_bands(data, period=20, std_dev=2):
    """Bollinger Bands"""
    if len(data) < period:
        return pd.Series(dtype=float), pd.Series(dtype=float), pd.Series(dtype=float)
    ma = data['Close'].rolling(period).mean()
    std = data['Close'].rolling(period).std()
    upper = ma + (std * std_dev)
    lower = ma - (std * std_dev)
    return upper, ma, lower

# ============================================================================
# NEWS & SENTIMENT
# ============================================================================

def fetch_news_from_rss():
    """Fetch news from free RSS feeds"""
    feeds = [
        "https://feeds.economictimes.indiatimes.com/markets/stocks",
        "https://www.moneycontrol.com/rss/stocks.xml",
    ]
    
    all_news = []
    for feed_url in feeds:
        try:
            parsed = feedparser.parse(feed_url)
            for entry in parsed.entries[:5]:
                all_news.append({
                    "title": entry.get("title", ""),
                    "summary": entry.get("summary", "")[:150],
                    "source": feed_url.split("/")[2]
                })
        except:
            pass
    
    return all_news[:12]

def analyze_sentiment(text):
    """Sentiment analysis using keywords"""
    text_lower = text.lower()
    
    positive_keywords = {
        "breakout": 3, "surge": 3, "growth": 2, "profit": 3, "beats": 3,
        "bullish": 3, "strong": 2, "rally": 3, "up": 1, "gain": 2
    }
    
    negative_keywords = {
        "crash": 3, "falls": 2, "drop": 2, "weak": 2, "miss": 3,
        "bearish": 3, "selloff": 3, "decline": 2, "loss": 2
    }
    
    score = 0
    for word, weight in positive_keywords.items():
        if word in text_lower:
            score += weight
    for word, weight in negative_keywords.items():
        if word in text_lower:
            score -= weight
    
    score = max(-10, min(10, score))
    
    if score >= 4:
        return {"score": score, "sentiment": "BULLISH", "color": "sentiment-positive"}
    elif score <= -4:
        return {"score": score, "sentiment": "BEARISH", "color": "sentiment-negative"}
    else:
        return {"score": score, "sentiment": "NEUTRAL", "color": "sentiment-neutral"}

# ============================================================================
# BACKTESTING
# ============================================================================

def backtest_strategy(data):
    """Simple backtest"""
    if len(data) < 30:
        return None
    
    wma = calculate_wma(data, 20)
    rsi = calculate_rsi(data, 14)
    
    wma = wma.dropna()
    rsi = rsi.dropna()
    
    if len(wma) == 0 or len(rsi) == 0:
        return None
    
    signals = []
    returns = []
    
    for i in range(20, len(data) - 1):
        close = data['Close'].iloc[i]
        wma_val = wma.iloc[i - 20] if i - 20 >= 0 and i - 20 < len(wma) else close
        rsi_val = rsi.iloc[i - 20] if i - 20 >= 0 and i - 20 < len(rsi) else 50
        
        if close > wma_val and rsi_val < 70:
            signal = 1
        elif close < wma_val and rsi_val > 30:
            signal = -1
        else:
            signal = 0
        
        signals.append(signal)
        next_close = data['Close'].iloc[i + 1]
        ret = (next_close - close) / close
        
        if signal == 1:
            returns.append(ret)
        elif signal == -1:
            returns.append(-ret)
        else:
            returns.append(0)
    
    if not returns:
        return None
    
    total_return = sum(returns)
    win_count = sum(1 for r in returns if r > 0)
    win_rate = win_count / len(returns)
    max_dd = min(np.cumsum(returns)) if returns else 0
    
    return {
        "total_return": total_return,
        "win_rate": win_rate,
        "max_drawdown": max_dd,
        "trades": len([s for s in signals if s != 0]),
        "avg_return": np.mean(returns)
    }

# ============================================================================
# SIDEBAR
# ============================================================================

with st.sidebar:
    st.markdown("""
    <div style="margin-bottom: 30px;">
        <div style="font-family: 'Poppins', sans-serif; font-size: 28px; font-weight: 800;
        background: linear-gradient(135deg, #6366f1, #a78bfa);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;">Market Pulse</div>
        <div class="subtitle">Sentiment + Technical</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("### 📰 News & Sentiment")
    
    input_method = st.radio(
        "Input method:",
        ["Fetch Live News", "Paste Headline"],
        label_visibility="collapsed",
        key="input_radio"
    )
    st.session_state.input_method = input_method
    
    if input_method == "Fetch Live News":
        if st.button("🔄 Fetch Latest News", use_container_width=True):
            with st.spinner("Fetching..."):
                st.session_state.news_cache = fetch_news_from_rss()
    else:
        st.session_state.user_headline = st.text_area(
            "Paste headline:",
            value=st.session_state.user_headline,
            height=120,
            label_visibility="collapsed"
        )

# ============================================================================
# MAIN UI
# ============================================================================

st.markdown('<div class="main-title">Market Pulse</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Real-time Sentiment + Technical Analysis for Nifty50</div>', unsafe_allow_html=True)

st.markdown("""
<div class="disclaimer">
⚠️ <strong>EDUCATIONAL ONLY:</strong> This is an educational tool using delayed data (15-20 min) 
and keyword-based sentiment (60-65% accurate). Not for real trading. Always consult financial advisors.
</div>
""", unsafe_allow_html=True)

# Market Overview
st.markdown('<div class="section-title">📊 Market Overview</div>', unsafe_allow_html=True)

try:
    nifty_data = fetch_nifty_data(90)
    if nifty_data is not None and len(nifty_data) > 0:
        current = nifty_data['Close'].iloc[-1]
        prev = nifty_data['Close'].iloc[-2] if len(nifty_data) > 1 else current
        change = current - prev
        pct = (change / prev * 100) if prev != 0 else 0
        high_52w = nifty_data['Close'].max()
        low_52w = nifty_data['Close'].min()
        avg_vol = nifty_data['Volume'].mean()
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"""
            <div class="metric-box">
                <div class="metric-label">Nifty50</div>
                <div class="metric-value">{current:,.0f}</div>
                <div style="font-size:12px; color:{'#6ee7b7' if change > 0 else '#fca5a5'}; margin-top:4px;">
                {'▲' if change > 0 else '▼'} {abs(pct):.2f}%
                </div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class="metric-box">
                <div class="metric-label">52W High</div>
                <div class="metric-value">{high_52w:,.0f}</div>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
            <div class="metric-box">
                <div class="metric-label">52W Low</div>
                <div class="metric-value">{low_52w:,.0f}</div>
            </div>
            """, unsafe_allow_html=True)
        with col4:
            st.markdown(f"""
            <div class="metric-box">
                <div class="metric-label">Avg Volume</div>
                <div class="metric-value">{avg_vol/1e6:.1f}M</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.warning("Market data unavailable. Retrying...")
except Exception as e:
    st.error(f"Market data error: {str(e)}")

st.markdown("---")

# Technical Analysis
st.markdown('<div class="section-title">📈 Technical Analysis</div>', unsafe_allow_html=True)

try:
    nifty_data = fetch_nifty_data(90)
    if nifty_data is not None and len(nifty_data) >= 30:
        wma = calculate_wma(nifty_data, 20).dropna()
        rsi = calculate_rsi(nifty_data, 14).dropna()
        macd_line, signal_line, hist = calculate_macd(nifty_data)
        macd_line = macd_line.dropna()
        signal_line = signal_line.dropna()
        upper_bb, middle_bb, lower_bb = calculate_bollinger_bands(nifty_data)
        
        if len(rsi) > 0 and len(wma) > 0:
            fig = make_subplots(
                rows=3, cols=1, shared_xaxes=True,
                subplot_titles=("Price & Indicators", "RSI (14)", "MACD"),
                row_heights=[0.5, 0.25, 0.25],
                vertical_spacing=0.08
            )
            
            fig.add_trace(
                go.Scatter(x=nifty_data.index, y=nifty_data['Close'], name='Close',
                          line=dict(color='#a5b4fc', width=2)),
                row=1, col=1
            )
            fig.add_trace(
                go.Scatter(x=wma.index, y=wma, name='WMA(20)',
                          line=dict(color='#ec4899', width=1, dash='dash')),
                row=1, col=1
            )
            fig.add_trace(
                go.Scatter(x=rsi.index, y=rsi, name='RSI',
                          line=dict(color='#6ee7b7', width=2)),
                row=2, col=1
            )
            fig.add_hline(y=70, line_dash="dash", line_color="rgba(252, 165, 165, 0.5)", row=2, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="rgba(110, 231, 183, 0.5)", row=2, col=1)
            
            if len(macd_line) > 0 and len(signal_line) > 0:
                fig.add_trace(
                    go.Scatter(x=macd_line.index, y=macd_line, name='MACD',
                              line=dict(color='#6366f1', width=2)),
                    row=3, col=1
                )
                fig.add_trace(
                    go.Scatter(x=signal_line.index, y=signal_line, name='Signal',
                              line=dict(color='#a78bfa', width=1, dash='dash')),
                    row=3, col=1
                )
            
            fig.update_layout(
                height=800,
                hovermode='x unified',
                plot_bgcolor='rgba(30, 27, 75, 0.3)',
                paper_bgcolor='rgba(10, 14, 39, 0)',
                font=dict(color='#a5b4fc'),
                margin=dict(l=50, r=20, t=40, b=20)
            )
            fig.update_xaxes(gridcolor='rgba(99, 102, 241, 0.1)')
            fig.update_yaxes(gridcolor='rgba(99, 102, 241, 0.1)')
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Insights
            col1, col2, col3 = st.columns(3)
            with col1:
                latest_rsi = rsi.iloc[-1] if len(rsi) > 0 else 50
                if latest_rsi > 70:
                    status, color = "Overbought", "#fca5a5"
                elif latest_rsi < 30:
                    status, color = "Oversold", "#6ee7b7"
                else:
                    status, color = "Neutral", "#a5b4fc"
                st.markdown(f"""
                <div class="pulse-card">
                    <div class="metric-label">RSI Status</div>
                    <div style="color: {color}; font-size: 16px; font-weight: 700; margin-top: 8px;">{status}</div>
                    <div style="font-size: 12px; color: #a5b4fc; margin-top: 4px;">Value: {latest_rsi:.1f}</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                latest_close = nifty_data['Close'].iloc[-1]
                latest_wma = wma.iloc[-1] if len(wma) > 0 else latest_close
                if latest_close > latest_wma:
                    status, color = "Above WMA ▲", "#6ee7b7"
                else:
                    status, color = "Below WMA ▼", "#fca5a5"
                st.markdown(f"""
                <div class="pulse-card">
                    <div class="metric-label">Price vs WMA(20)</div>
                    <div style="color: {color}; font-size: 16px; font-weight: 700; margin-top: 8px;">{status}</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                if len(macd_line) > 0 and len(signal_line) > 0:
                    macd_val = macd_line.iloc[-1]
                    signal_val = signal_line.iloc[-1]
                    if macd_val > signal_val:
                        status, color = "Bullish ▲", "#6ee7b7"
                    else:
                        status, color = "Bearish ▼", "#fca5a5"
                else:
                    status, color = "No data", "#a5b4fc"
                st.markdown(f"""
                <div class="pulse-card">
                    <div class="metric-label">MACD Signal</div>
                    <div style="color: {color}; font-size: 16px; font-weight: 700; margin-top: 8px;">{status}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.warning("Insufficient indicator data. Retrying...")
    else:
        st.warning("Insufficient market data. Please try again in a few seconds.")
except Exception as e:
    st.error(f"Technical analysis error: {str(e)}")

st.markdown("---")

# Sentiment Analysis
st.markdown('<div class="section-title">💭 Sentiment Analysis</div>', unsafe_allow_html=True)

headlines = []
if st.session_state.input_method == "Fetch Live News" and st.session_state.news_cache:
    headlines = st.session_state.news_cache
elif st.session_state.input_method == "Paste Headline" and st.session_state.user_headline.strip():
    headlines = [{"title": st.session_state.user_headline, "source": "Manual", "summary": ""}]

if headlines:
    sentiments = [analyze_sentiment(h["title"] + " " + h.get("summary", "")) for h in headlines]
    
    if sentiments:
        avg_score = np.mean([s["score"] for s in sentiments])
        
        if avg_score >= 4:
            overall, card_class = "BUY", "signal-buy"
        elif avg_score <= -4:
            overall, card_class = "SELL", "signal-sell"
        else:
            overall, card_class = "HOLD", "signal-hold"
        
        col1, col2 = st.columns([1.5, 2])
        with col1:
            st.markdown(f"""
            <div class="pulse-card {card_class}">
                <div style="font-size: 12px; opacity: 0.8; text-transform: uppercase;">Market Consensus</div>
                <div class="signal-value">{overall}</div>
                <div style="font-size: 13px; margin-top: 4px;">Score: {avg_score:+.1f}/10</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            bullish = sum(1 for s in sentiments if s["sentiment"] == "BULLISH")
            neutral = sum(1 for s in sentiments if s["sentiment"] == "NEUTRAL")
            bearish = sum(1 for s in sentiments if s["sentiment"] == "BEARISH")
            
            st.markdown(f"""
            <div class="pulse-card">
                <div style="font-size: 12px; color: #a5b4fc; text-transform: uppercase; margin-bottom: 12px;">Sentiment Distribution</div>
                <div style="display: flex; gap: 12px;">
                    <div style="flex: 1; text-align: center;">
                        <div style="color: #6ee7b7; font-size: 20px; font-weight: 700;">{bullish}</div>
                        <div style="color: #a5b4fc; font-size: 11px;">Bullish</div>
                    </div>
                    <div style="flex: 1; text-align: center;">
                        <div style="color: #fcd34d; font-size: 20px; font-weight: 700;">{neutral}</div>
                        <div style="color: #a5b4fc; font-size: 11px;">Neutral</div>
                    </div>
                    <div style="flex: 1; text-align: center;">
                        <div style="color: #fca5a5; font-size: 20px; font-weight: 700;">{bearish}</div>
                        <div style="color: #a5b4fc; font-size: 11px;">Bearish</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("#### Headlines Analyzed")
        for h, s in zip(headlines[:10], sentiments[:10]):
            color = "#6ee7b7" if s["sentiment"] == "BULLISH" else "#fca5a5" if s["sentiment"] == "BEARISH" else "#fcd34d"
            st.markdown(f"""
            <div style="background: rgba(30, 27, 75, 0.5); border-left: 3px solid {color}; border-radius: 8px; padding: 12px; margin-bottom: 10px;">
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <div style="flex: 1;">
                        <div style="color: #e0e7ff; font-weight: 600; font-size: 14px;">{h['title']}</div>
                        <div style="font-size: 11px; color: #a5b4fc; margin-top: 4px;">📍 {h['source']}</div>
                    </div>
                    <div style="text-align: right; margin-left: 12px;">
                        <div style="color: {color}; font-weight: 700;">{s['sentiment']}</div>
                        <div style="font-size: 11px; color: #a5b4fc;">Score: {s['score']:+.1f}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
else:
    st.info("👈 Use sidebar to fetch news or paste a headline")

st.markdown("---")

# Backtesting
st.markdown('<div class="section-title">🧪 Strategy Backtest (3 Months)</div>', unsafe_allow_html=True)

col1, col2 = st.columns([3, 1])
with col1:
    st.markdown("**Signal Rule:** Price > WMA(20) + RSI < 70 = BUY | Price < WMA(20) + RSI > 30 = SELL")
with col2:
    if st.button("Run Backtest", use_container_width=True):
        with st.spinner("Testing..."):
            bt_data = fetch_nifty_data(90)
            if bt_data is not None:
                result = backtest_strategy(bt_data)
                st.session_state.backtest_result = result

if st.session_state.backtest_result:
    r = st.session_state.backtest_result
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="pulse-card">
            <div class="metric-label">Total Return</div>
            <div class="metric-value" style="color: {'#6ee7b7' if r['total_return'] > 0 else '#fca5a5'};">
            {r['total_return']*100:.2f}%
            </div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="pulse-card">
            <div class="metric-label">Win Rate</div>
            <div class="metric-value">{r['win_rate']*100:.1f}%</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="pulse-card">
            <div class="metric-label">Max Drawdown</div>
            <div class="metric-value" style="color: #fca5a5;">{r['max_drawdown']*100:.2f}%</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="pulse-card">
            <div class="metric-label">Signals</div>
            <div class="metric-value">{r['trades']}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")
st.markdown("""
<div style="text-align: center; padding: 20px; color: #a5b4fc; font-size: 11px; letter-spacing: 1px;">
MARKET PULSE • EDUCATIONAL TOOL • NOT FINANCIAL ADVICE
</div>
""", unsafe_allow_html=True)
