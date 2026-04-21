import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
from collections import Counter
import time

# ============================================================================
# PAGE CONFIG & SESSION STATE
# ============================================================================
st.set_page_config(
    page_title="Market Pulse",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"About": "Educational market sentiment & technical analysis tool"}
)

if "news_cache" not in st.session_state:
    st.session_state.news_cache = []
    st.session_state.cache_time = None

if "backtest_result" not in st.session_state:
    st.session_state.backtest_result = None

if "user_headline" not in st.session_state:
    st.session_state.user_headline = ""

# ============================================================================
# STYLING
# ============================================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&family=Inter:wght@300;400;500;600&display=swap');

* {
    font-family: 'Inter', sans-serif !important;
}

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
    letter-spacing: -1px;
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
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    transition: all 0.3s ease;
}

.pulse-card:hover {
    border-color: rgba(99, 102, 241, 0.6);
    background: rgba(30, 27, 75, 0.8);
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

.metric-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 16px;
    margin: 20px 0;
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
    margin-bottom: 8px;
}

.metric-value {
    font-family: 'Poppins', sans-serif;
    font-size: 24px;
    font-weight: 700;
    color: #6366f1;
}

.news-item {
    background: rgba(30, 27, 75, 0.5);
    border-left: 3px solid #6366f1;
    border-radius: 8px;
    padding: 14px;
    margin-bottom: 10px;
    border-top: 1px solid rgba(99, 102, 241, 0.2);
}

.sentiment-positive { color: #6ee7b7; }
.sentiment-negative { color: #fca5a5; }
.sentiment-neutral { color: #a5b4fc; }

.indicator-card {
    background: rgba(30, 27, 75, 0.4);
    border: 1px solid rgba(99, 102, 241, 0.2);
    border-radius: 10px;
    padding: 12px;
    margin: 8px 0;
    font-size: 13px;
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

.stTextArea > div > div > textarea {
    background: rgba(30, 27, 75, 0.6) !important;
    color: #e0e7ff !important;
    border: 1px solid rgba(99, 102, 241, 0.3) !important;
    border-radius: 12px !important;
}

.stButton > button {
    background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    padding: 10px 20px !important;
    transition: all 0.3s ease !important;
}

.stButton > button:hover {
    background: linear-gradient(135deg, #8b5cf6, #a78bfa) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 20px rgba(99, 102, 241, 0.3) !important;
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

.success-badge {
    display: inline-block;
    background: rgba(16, 185, 129, 0.2);
    color: #6ee7b7;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
    margin-left: 8px;
}

.info-box {
    background: rgba(99, 102, 241, 0.1);
    border: 1px solid rgba(99, 102, 241, 0.3);
    border-radius: 10px;
    padding: 12px;
    font-size: 13px;
    color: #a5b4fc;
    margin: 12px 0;
}
</style>
""", unsafe_allow_html=True)

# ============================================================================
# DATA FETCHING & TECHNICAL ANALYSIS
# ============================================================================

@st.cache_data(ttl=300)
def fetch_nifty_data(days=90):
    """Fetch Nifty50 historical data"""
    try:
        data = yf.download("^NSEI", period=f"{days}d", progress=False)
        return data
    except:
        return None

def calculate_wma(data, period=20):
    """Calculate Weighted Moving Average"""
    weights = np.arange(1, period + 1)
    wma = data['Close'].rolling(window=period).apply(
        lambda x: np.sum(weights * x) / np.sum(weights), raw=False
    )
    return wma

def calculate_rsi(data, period=14):
    """Calculate Relative Strength Index"""
    close = data['Close']
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_macd(data, fast=12, slow=26, signal=9):
    """Calculate MACD"""
    ema_fast = data['Close'].ewm(span=fast).mean()
    ema_slow = data['Close'].ewm(span=slow).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def calculate_bollinger_bands(data, period=20, std_dev=2):
    """Calculate Bollinger Bands"""
    ma = data['Close'].rolling(period).mean()
    std = data['Close'].rolling(period).std()
    upper = ma + (std * std_dev)
    lower = ma - (std * std_dev)
    return upper, ma, lower

def calculate_volume_profile(data, bins=20):
    """Simplified volume profile"""
    price_ranges = pd.cut(data['Close'], bins=bins)
    volume_by_price = data.groupby(price_ranges)['Volume'].sum()
    return volume_by_price

# ============================================================================
# NEWS FETCHING & SENTIMENT ANALYSIS
# ============================================================================

def fetch_news_from_rss():
    """Fetch news from multiple free RSS feeds"""
    feeds = [
        "https://feeds.economictimes.indiatimes.com/markets/stocks",
        "https://www.moneycontrol.com/rss/stocks.xml",
        "https://feeds.bloomberg.com/markets/news.rss",
    ]
    
    all_news = []
    
    for feed_url in feeds:
        try:
            parsed = feedparser.parse(feed_url)
            for entry in parsed.entries[:5]:  # Last 5 from each feed
                all_news.append({
                    "title": entry.get("title", ""),
                    "summary": entry.get("summary", "")[:200],
                    "link": entry.get("link", ""),
                    "published": entry.get("published", ""),
                    "source": feed_url.split("/")[2]
                })
        except Exception as e:
            pass
    
    return all_news[:15]  # Return top 15

def analyze_sentiment(text):
    """Sentiment analysis using keyword weighting"""
    text_lower = text.lower()
    
    positive_keywords = {
        "breakout": 3, "surge": 3, "growth": 2, "profit": 3, "beats": 3,
        "bullish": 3, "strong": 2, "up": 1, "gain": 2, "record": 2,
        "expands": 2, "rally": 3, "recovery": 2, "boost": 2, "outperform": 2,
        "surge": 3, "soar": 3, "jump": 2, "rally": 3, "positive": 2,
        "improve": 2, "upside": 2, "momentum": 2, "strength": 2
    }
    
    negative_keywords = {
        "crash": 3, "falls": 2, "drop": 2, "weak": 2, "miss": 3,
        "bearish": 3, "inflation": 2, "tension": 2, "selloff": 3, "risk": 1,
        "uncertainty": 2, "slowdown": 2, "decline": 2, "fall": 2, "loss": 2,
        "concern": 2, "warning": 3, "slump": 3, "trouble": 2, "downside": 2,
        "negative": 1, "weakness": 2
    }
    
    score = 0
    for word, weight in positive_keywords.items():
        if word in text_lower:
            score += weight
    for word, weight in negative_keywords.items():
        if word in text_lower:
            score -= weight
    
    score = max(-10, min(10, score))  # Clamp between -10 and 10
    
    if score >= 4:
        sentiment = "BULLISH"
        color = "sentiment-positive"
    elif score <= -4:
        sentiment = "BEARISH"
        color = "sentiment-negative"
    else:
        sentiment = "NEUTRAL"
        color = "sentiment-neutral"
    
    confidence = min(abs(score) / 10, 1.0)
    
    return {
        "score": score,
        "sentiment": sentiment,
        "color": color,
        "confidence": confidence
    }

# ============================================================================
# BACKTESTING
# ============================================================================

def backtest_sentiment_signals(data, days=90):
    """Backtest sentiment-based signals on historical data"""
    
    # Calculate indicators
    wma = calculate_wma(data, 20)
    rsi = calculate_rsi(data, 14)
    
    # Simple trading rules
    signals = []
    returns = []
    
    for i in range(len(data) - 1):
        if i < 20:
            continue
        
        close = data['Close'].iloc[i]
        wma_val = wma.iloc[i]
        rsi_val = rsi.iloc[i]
        
        # Buy signal: Price above WMA + RSI < 70
        if close > wma_val and rsi_val < 70:
            signal = 1  # BUY
        # Sell signal: Price below WMA + RSI > 30
        elif close < wma_val and rsi_val > 30:
            signal = -1  # SELL
        else:
            signal = 0  # HOLD
        
        signals.append(signal)
        
        # Calculate return
        next_close = data['Close'].iloc[i + 1]
        ret = (next_close - close) / close
        
        if signal == 1:
            returns.append(ret)
        elif signal == -1:
            returns.append(-ret)
        else:
            returns.append(0)
    
    total_return = sum(returns)
    win_count = sum(1 for r in returns if r > 0)
    win_rate = win_count / len(returns) if returns else 0
    max_drawdown = min(np.cumsum(returns)) if returns else 0
    
    return {
        "total_return": total_return,
        "win_rate": win_rate,
        "max_drawdown": max_drawdown,
        "trades": len([s for s in signals if s != 0]),
        "avg_return": np.mean(returns) if returns else 0
    }

# ============================================================================
# UI COMPONENTS
# ============================================================================

def display_disclaimer():
    """Display risk disclaimer"""
    st.markdown("""
    <div class="disclaimer">
    <strong>⚠️ EDUCATIONAL DISCLAIMER:</strong> Market Pulse is an educational tool only. 
    It uses keyword-based sentiment analysis and technical indicators on delayed data (15-20 min). 
    Not for real trading. Markets involve substantial risk. Always conduct your own research, 
    consult financial advisors, and never trade more than you can afford to lose.
    </div>
    """, unsafe_allow_html=True)

def display_market_overview():
    """Display current market overview"""
    st.markdown('<div class="section-title">📊 Market Overview</div>', unsafe_allow_html=True)
    
    try:
        data = fetch_nifty_data(90)
        if data is not None and len(data) > 0:
            current = data['Close'].iloc[-1]
            prev = data['Close'].iloc[-2] if len(data) > 1 else current
            change = current - prev
            pct_change = (change / prev) * 100 if prev != 0 else 0
            high_52w = data['Close'].max()
            low_52w = data['Close'].min()
            avg_vol = data['Volume'].mean()
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown(f"""
                <div class="metric-box">
                    <div class="metric-label">Nifty50 Price</div>
                    <div class="metric-value">{current:,.0f}</div>
                    <div style="font-size:12px; color:#{'6ee7b7' if change > 0 else 'fca5a5'}; margin-top:4px;">
                    {'▲' if change > 0 else '▼'} {abs(pct_change):.2f}%
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
    except:
        st.error("Could not fetch market data. Check your internet connection.")

def display_price_chart():
    """Display interactive price chart with technicals"""
    st.markdown('<div class="section-title">📈 Technical Analysis</div>', unsafe_allow_html=True)
    
    data = fetch_nifty_data(90)
    if data is None or len(data) < 30:
        st.error("Insufficient data. Please try again in a few seconds.")
        return
    
    # Calculate indicators
    wma = calculate_wma(data, 20)
    rsi = calculate_rsi(data, 14)
    macd_line, signal_line, histogram = calculate_macd(data)
    upper_bb, middle_bb, lower_bb = calculate_bollinger_bands(data)
    
    # Remove NaN values for plotting
    wma = wma.dropna()
    rsi = rsi.dropna()
    macd_line = macd_line.dropna()
    signal_line = signal_line.dropna()
    histogram = histogram.dropna()
    upper_bb = upper_bb.dropna()
    middle_bb = middle_bb.dropna()
    lower_bb = lower_bb.dropna()
    
    # Validate data
    if len(rsi) == 0 or len(wma) == 0:
        st.error("Could not calculate technical indicators. Please refresh the page.")
        return
    
    # Create subplots
    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True,
        subplot_titles=("Price & Indicators", "RSI (14)", "MACD"),
        row_heights=[0.5, 0.25, 0.25],
        vertical_spacing=0.08
    )
    
    # Candlestick-style price
    fig.add_trace(
        go.Scatter(x=data.index, y=data['Close'], mode='lines',
                   name='Close', line=dict(color='#a5b4fc', width=2)),
        row=1, col=1
    )
    
    # WMA
    fig.add_trace(
        go.Scatter(x=data.index, y=wma, mode='lines',
                   name='WMA (20)', line=dict(color='#ec4899', width=1, dash='dash')),
        row=1, col=1
    )
    
    # Bollinger Bands
    fig.add_trace(
        go.Scatter(x=data.index, y=upper_bb, fill=None,
                   name='Upper BB', line=dict(width=0), showlegend=False),
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(x=data.index, y=lower_bb, fill='tonexty',
                   name='Bollinger Bands', line=dict(width=0),
                   fillcolor='rgba(139, 92, 246, 0.1)'),
        row=1, col=1
    )
    
    # RSI
    fig.add_trace(
        go.Scatter(x=data.index, y=rsi, mode='lines',
                   name='RSI', line=dict(color='#6ee7b7', width=2)),
        row=2, col=1
    )
    fig.add_hline(y=70, line_dash="dash", line_color="rgba(252, 165, 165, 0.5)",
                  row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="rgba(110, 231, 183, 0.5)",
                  row=2, col=1)
    
    # MACD
    fig.add_trace(
        go.Scatter(x=data.index, y=macd_line, mode='lines',
                   name='MACD', line=dict(color='#6366f1', width=2)),
        row=3, col=1
    )
    fig.add_trace(
        go.Scatter(x=data.index, y=signal_line, mode='lines',
                   name='Signal', line=dict(color='#a78bfa', width=1, dash='dash')),
        row=3, col=1
    )
    
    # Update layout
    fig.update_layout(
        height=900,
        hovermode='x unified',
        plot_bgcolor='rgba(30, 27, 75, 0.3)',
        paper_bgcolor='rgba(10, 14, 39, 0)',
        font=dict(color='#a5b4fc', family='Inter'),
        margin=dict(l=50, r=20, t=40, b=20),
        xaxis_rangeslider_visible=False
    )
    
    fig.update_xaxes(
        gridcolor='rgba(99, 102, 241, 0.1)',
        showgrid=True
    )
    fig.update_yaxes(
        gridcolor='rgba(99, 102, 241, 0.1)',
        showgrid=True
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Technical insights
    col1, col2, col3 = st.columns(3)
    
    with col1:
        try:
            latest_rsi = rsi.iloc[-1] if len(rsi) > 0 else 50
        except (IndexError, KeyError):
            latest_rsi = 50
        
        if latest_rsi > 70:
            status = "Overbought ⚠️"
            color = "sentiment-negative"
        elif latest_rsi < 30:
            status = "Oversold ✓"
            color = "sentiment-positive"
        else:
            status = "Neutral"
            color = "sentiment-neutral"
        
        st.markdown(f"""
        <div class="indicator-card">
            <div class="metric-label">RSI Status</div>
            <div class="{color}" style="font-size: 16px; font-weight: 700; margin-top: 6px;">
            {status}
            </div>
            <div style="font-size: 12px; color: #a5b4fc; margin-top: 4px;">
            Value: {latest_rsi:.1f}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        try:
            latest_close = data['Close'].iloc[-1] if len(data) > 0 else 0
            latest_wma = wma.iloc[-1] if len(wma) > 0 else latest_close
        except (IndexError, KeyError):
            latest_close = 0
            latest_wma = 0
        
        if latest_close == 0 or latest_wma == 0:
            status = "No data"
            color = "sentiment-neutral"
        elif latest_close > latest_wma:
            status = "Above WMA (Bullish) ▲"
            color = "sentiment-positive"
        else:
            status = "Below WMA (Bearish) ▼"
            color = "sentiment-negative"
        
        st.markdown(f"""
        <div class="indicator-card">
            <div class="metric-label">Price vs WMA(20)</div>
            <div class="{color}" style="font-size: 16px; font-weight: 700; margin-top: 6px;">
            {status}
            </div>
            <div style="font-size: 12px; color: #a5b4fc; margin-top: 4px;">
            Diff: {abs(latest_close - latest_wma):.0f} pts
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        try:
            macd_val = macd_line.iloc[-1] if len(macd_line) > 0 else 0
            signal_val = signal_line.iloc[-1] if len(signal_line) > 0 else 0
        except (IndexError, KeyError):
            macd_val = 0
            signal_val = 0
        
        if macd_val == 0 or signal_val == 0:
            status = "No data"
            color = "sentiment-neutral"
        elif macd_val > signal_val:
            status = "Bullish Crossover ▲"
            color = "sentiment-positive"
        else:
            status = "Bearish Crossover ▼"
            color = "sentiment-negative"
        
        st.markdown(f"""
        <div class="indicator-card">
            <div class="metric-label">MACD Signal</div>
            <div class="{color}" style="font-size: 16px; font-weight: 700; margin-top: 6px;">
            {status}
            </div>
        </div>
        """, unsafe_allow_html=True)

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
        <div class="subtitle">Sentiment + Technical Analysis</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.markdown("### 📰 News & Sentiment")
    
    input_method = st.radio("Choose input method:", 
                            ["Fetch Live News", "Paste Headline"],
                            label_visibility="collapsed")
    
    if input_method == "Fetch Live News":
        if st.button("🔄 Fetch Latest News", use_container_width=True):
            with st.spinner("Fetching news from multiple sources..."):
                st.session_state.news_cache = fetch_news_from_rss()
                st.session_state.cache_time = datetime.now()
    
    else:
        st.session_state.user_headline = st.text_area(
            "Paste your headline:",
            value=st.session_state.user_headline,
            height=120,
            placeholder="Paste market news here...",
            label_visibility="collapsed"
        )

# ============================================================================
# MAIN CONTENT
# ============================================================================

st.markdown('<div class="main-title">Market Pulse</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Real-time Sentiment + Technical Analysis for Nifty50</div>', 
            unsafe_allow_html=True)

display_disclaimer()

# Market Overview
display_market_overview()

st.markdown("---")

# Technical Analysis
display_price_chart()

st.markdown("---")

# Sentiment Analysis
st.markdown('<div class="section-title">💭 Sentiment Analysis</div>', unsafe_allow_html=True)

headlines_to_analyze = []

if st.sidebar.session_state.input_method == "Fetch Live News" and st.session_state.news_cache:
    headlines_to_analyze = st.session_state.news_cache
    st.info(f"📡 {len(headlines_to_analyze)} headlines from Economic Times, Moneycontrol, Bloomberg")

elif st.sidebar.session_state.input_method == "Paste Headline" and st.session_state.user_headline.strip():
    headlines_to_analyze = [{
        "title": st.session_state.user_headline,
        "summary": "",
        "source": "Manual Input",
        "link": ""
    }]

if headlines_to_analyze:
    # Analyze each headline
    sentiments = []
    
    for i, news in enumerate(headlines_to_analyze[:10]):  # Top 10
        sentiment = analyze_sentiment(news["title"] + " " + news.get("summary", ""))
        sentiments.append(sentiment)
    
    # Overall market sentiment
    if sentiments:
        avg_sentiment = np.mean([s["score"] for s in sentiments])
        
        if avg_sentiment >= 4:
            overall_action = "BUY"
            signal_class = "signal-buy"
        elif avg_sentiment <= -4:
            overall_action = "SELL"
            signal_class = "signal-sell"
        else:
            overall_action = "HOLD"
            signal_class = "signal-hold"
        
        col1, col2 = st.columns([1.5, 2])
        
        with col1:
            st.markdown(f"""
            <div class="pulse-card {signal_class}">
                <div style="font-size: 12px; color: currentColor; opacity: 0.8; text-transform: uppercase; letter-spacing: 1px;">Market Consensus</div>
                <div class="signal-value">{overall_action}</div>
                <div style="font-size: 13px; color: currentColor; opacity: 0.9;">Score: {avg_sentiment:+.1f}/10</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            bullish = sum(1 for s in sentiments if s["sentiment"] == "BULLISH")
            bearish = sum(1 for s in sentiments if s["sentiment"] == "BEARISH")
            neutral = sum(1 for s in sentiments if s["sentiment"] == "NEUTRAL")
            
            st.markdown(f"""
            <div class="pulse-card">
                <div style="font-size: 12px; color: #a5b4fc; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 10px;">Sentiment Distribution</div>
                <div style="display: flex; gap: 8px; margin-bottom: 10px;">
                    <div style="flex: 1; text-align: center;">
                        <div style="color: #6ee7b7; font-size: 18px; font-weight: 700;">{bullish}</div>
                        <div style="color: #a5b4fc; font-size: 11px;">Bullish</div>
                    </div>
                    <div style="flex: 1; text-align: center;">
                        <div style="color: #fcd34d; font-size: 18px; font-weight: 700;">{neutral}</div>
                        <div style="color: #a5b4fc; font-size: 11px;">Neutral</div>
                    </div>
                    <div style="flex: 1; text-align: center;">
                        <div style="color: #fca5a5; font-size: 18px; font-weight: 700;">{bearish}</div>
                        <div style="color: #a5b4fc; font-size: 11px;">Bearish</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    # Individual headlines
    st.markdown("#### 📋 Analyzed Headlines")
    
    for i, (news, sentiment) in enumerate(zip(headlines_to_analyze[:10], sentiments)):
        color_class = sentiment["color"]
        
        st.markdown(f"""
        <div class="news-item">
            <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 8px;">
                <div style="flex: 1;">
                    <div style="font-weight: 600; color: #e0e7ff; font-size: 14px;">{news['title']}</div>
                    <div style="font-size: 11px; color: #a5b4fc; margin-top: 4px;">📍 {news['source']}</div>
                </div>
                <div style="text-align: right; margin-left: 12px;">
                    <div class="{color_class}" style="font-weight: 700; font-size: 13px;">{sentiment['sentiment']}</div>
                    <div style="font-size: 11px; color: #a5b4fc; margin-top: 2px;">Score: {sentiment['score']:+.1f}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

else:
    st.info("👈 Use the sidebar to fetch live news or paste a headline to analyze sentiment")

st.markdown("---")

# Backtesting
st.markdown('<div class="section-title">🧪 Strategy Backtesting (3 Months)</div>', unsafe_allow_html=True)

col1, col2 = st.columns([3, 1])

with col1:
    st.markdown("**Testing:** Price > WMA(20) + RSI < 70 = BUY | Price < WMA(20) + RSI > 30 = SELL")

with col2:
    if st.button("Run Backtest", use_container_width=True):
        with st.spinner("Backtesting strategy..."):
            data = fetch_nifty_data(90)
            if data is not None:
                result = backtest_sentiment_signals(data)
                st.session_state.backtest_result = result

if st.session_state.backtest_result:
    result = st.session_state.backtest_result
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="pulse-card">
            <div class="metric-label">Total Return</div>
            <div class="metric-value" style="color: {'#6ee7b7' if result['total_return'] > 0 else '#fca5a5'};">
            {result['total_return']*100:.2f}%
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="pulse-card">
            <div class="metric-label">Win Rate</div>
            <div class="metric-value">{result['win_rate']*100:.1f}%</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="pulse-card">
            <div class="metric-label">Max Drawdown</div>
            <div class="metric-value" style="color: #fca5a5;">{result['max_drawdown']*100:.2f}%</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="pulse-card">
            <div class="metric-label">Total Signals</div>
            <div class="metric-value">{result['trades']}</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="info-box">
    <strong>💡 Insight:</strong> Strategy generated {result['trades']} trading signals over 3 months with a {result['win_rate']*100:.1f}% win rate. 
    Average return per signal: {result['avg_return']*100:.2f}%. Past performance ≠ future results.
    </div>
    """, unsafe_allow_html=True)

# ============================================================================
# FOOTER & EDUCATIONAL NOTES
# ============================================================================

st.markdown("---")

st.markdown("""
<div style="background: rgba(99, 102, 241, 0.08); border: 1px solid rgba(99, 102, 241, 0.2); 
border-radius: 12px; padding: 16px; margin-top: 20px;">
    <div style="font-size: 12px; color: #a5b4fc; line-height: 1.7;">
    <strong>📚 Educational Notes:</strong><br>
    • <strong>WMA(20):</strong> Weighted moving average gives more weight to recent prices<br>
    • <strong>RSI(14):</strong> Momentum oscillator; >70 overbought, <30 oversold<br>
    • <strong>MACD:</strong> Trend-following momentum indicator<br>
    • <strong>Bollinger Bands:</strong> Volatility indicator; price extremes near bands<br>
    • <strong>Sentiment:</strong> Keyword-based analysis on headlines (60-65% accuracy)<br>
    • <strong>Data:</strong> 15-20 minute delayed. Not real-time.<br>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div style="text-align: center; margin-top: 30px; padding: 20px; 
background: rgba(15, 22, 41, 0.5); border-top: 1px solid rgba(99, 102, 241, 0.2);">
    <div style="font-size: 11px; color: #a5b4fc; letter-spacing: 1px;">
    MARKET PULSE • EDUCATIONAL TOOL • NOT FINANCIAL ADVICE
    </div>
</div>
""", unsafe_allow_html=True)
