from html import escape
from io import StringIO

import feedparser
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
from plotly.subplots import make_subplots


INDEX_URL = "https://www.niftyindices.com/IndexConstituent/ind_nifty500list.csv"
YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
STOCK_STOPWORDS = {
    "ltd", "limited", "india", "indian", "industries", "industry", "company", "corporation",
    "corp", "services", "service", "bank", "finance", "financial", "holdings", "holding",
    "the", "and", "of", "nse", "bse",
}

REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; MarketPulse/2.0)",
    "Accept": "text/csv,application/rss+xml,application/xml,text/xml,application/json,*/*",
}

FALLBACK_STOCKS = [
    {"Company Name": "Reliance Industries Ltd.", "Symbol": "RELIANCE", "Industry": "Oil Gas & Consumable Fuels"},
    {"Company Name": "HDFC Bank Ltd.", "Symbol": "HDFCBANK", "Industry": "Financial Services"},
    {"Company Name": "ICICI Bank Ltd.", "Symbol": "ICICIBANK", "Industry": "Financial Services"},
    {"Company Name": "Infosys Ltd.", "Symbol": "INFY", "Industry": "Information Technology"},
    {"Company Name": "Tata Consultancy Services Ltd.", "Symbol": "TCS", "Industry": "Information Technology"},
    {"Company Name": "Larsen & Toubro Ltd.", "Symbol": "LT", "Industry": "Construction"},
    {"Company Name": "State Bank of India", "Symbol": "SBIN", "Industry": "Financial Services"},
    {"Company Name": "Bharti Airtel Ltd.", "Symbol": "BHARTIARTL", "Industry": "Telecommunication"},
    {"Company Name": "ITC Ltd.", "Symbol": "ITC", "Industry": "Fast Moving Consumer Goods"},
    {"Company Name": "Axis Bank Ltd.", "Symbol": "AXISBANK", "Industry": "Financial Services"},
]


st.set_page_config(page_title="Nifty 500 Stock Impact", layout="wide")

for key, value in {
    "news": [],
    "selected_news_index": 0,
    "selected_news": None,
    "manual_headline": "",
    "news_message": "",
    "current_symbol": "",
}.items():
    if key not in st.session_state:
        st.session_state[key] = value

st.markdown(
    """
<style>
.stApp { background: #0a0e27; color: #e0e7ff; }
section[data-testid="stSidebar"] { background: #0f1629; }
.title { font-size: 44px; font-weight: 800; color: #a78bfa; line-height: 1.05; }
.subtitle { color: #a5b4fc; letter-spacing: 2px; font-size: 12px; text-transform: uppercase; }
.card { background: rgba(30,27,75,0.6); border: 1px solid rgba(99,102,241,0.3); border-radius: 8px; padding: 18px; }
.buy { border-color: rgba(16,185,129,0.65); color: #6ee7b7; }
.sell { border-color: rgba(239,68,68,0.65); color: #fca5a5; }
.hold { border-color: rgba(245,158,11,0.65); color: #fcd34d; }
.signal { font-size: 44px; font-weight: 800; margin: 8px 0; }
.section { font-size: 22px; font-weight: 700; color: #c7d2fe; margin: 24px 0 16px; border-bottom: 2px solid rgba(99,102,241,0.3); padding-bottom: 8px; }
.small-note { color: #a5b4fc; font-size: 13px; }
.news-box { background: rgba(30,27,75,0.5); border-left: 3px solid #fcd34d; padding: 14px; margin-top: 10px; border-radius: 8px; }
.stButton > button { background: linear-gradient(135deg, #6366f1, #8b5cf6) !important; }
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_data(ttl=24 * 60 * 60, show_spinner=False)
def load_nifty500():
    try:
        response = requests.get(INDEX_URL, headers=REQUEST_HEADERS, timeout=20)
        response.raise_for_status()
        data = pd.read_csv(StringIO(response.text))
        required = {"Company Name", "Symbol"}
        if not required.issubset(set(data.columns)):
            raise ValueError("Unexpected Nifty 500 CSV format.")
        columns = ["Company Name", "Symbol"]
        if "Industry" in data.columns:
            columns.append("Industry")
        data = data[columns].dropna(subset=["Symbol"]).copy()
        data["Symbol"] = data["Symbol"].astype(str).str.strip().str.upper()
        data["Company Name"] = data["Company Name"].astype(str).str.strip()
        if "Industry" not in data.columns:
            data["Industry"] = ""
        return data.sort_values("Company Name").reset_index(drop=True), True
    except Exception:
        return pd.DataFrame(FALLBACK_STOCKS), False


@st.cache_data(ttl=15 * 60, show_spinner=False)
def fetch_stock_data(symbol):
    ticker = f"{symbol}.NS"
    try:
        response = requests.get(
            YAHOO_CHART_URL.format(ticker=requests.utils.quote(ticker, safe="")),
            params={"range": "3y", "interval": "1d", "events": "history"},
            headers=REQUEST_HEADERS,
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
        return data if len(data) >= 200 else None
    except Exception:
        return None


def stock_terms(symbol, company_name):
    terms = {symbol.lower()}
    for raw_word in str(company_name).replace("&", " ").replace("-", " ").split():
        word = "".join(ch for ch in raw_word.lower() if ch.isalnum())
        if len(word) >= 4 and word not in STOCK_STOPWORDS:
            terms.add(word)
    return terms


def is_stock_specific(title, symbol, company_name):
    text = str(title).lower()
    return any(term in text for term in stock_terms(symbol, company_name))


@st.cache_data(ttl=10 * 60, show_spinner=False)
def fetch_stock_news(symbol, company_name):
    query = f'"{company_name}" stock OR "{symbol}" share price'
    feeds = [
        f"https://news.google.com/rss/search?q={requests.utils.quote(query)}&hl=en-IN&gl=IN&ceid=IN:en",
        f"https://news.google.com/rss/search?q={requests.utils.quote(company_name + ' results shares')}&hl=en-IN&gl=IN&ceid=IN:en",
    ]
    news = []
    seen = set()
    for url in feeds:
        try:
            response = requests.get(url, headers=REQUEST_HEADERS, timeout=15)
            response.raise_for_status()
            feed = feedparser.parse(response.content)
            for entry in feed.entries[:12]:
                title = str(entry.get("title", "")).strip()
                if not title or not is_stock_specific(title, symbol, company_name):
                    continue
                key = title.lower()
                if key in seen:
                    continue
                seen.add(key)
                source = entry.get("source", {})
                source_name = source.get("title", "Google News") if hasattr(source, "get") else "Google News"
                news.append({"title": title, "source": str(source_name)})
        except Exception:
            continue
    return news[:15]


def get_series(data, column):
    if data is None or column not in data:
        return None
    return pd.to_numeric(data[column].squeeze(), errors="coerce").dropna()


def wma(close, period):
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
    rs = gain / loss.replace(0, np.nan)
    return (100 - (100 / (1 + rs))).fillna(50)


def sentiment(text):
    text = str(text).lower()
    positives = [
        "beats", "beat", "profit", "growth", "surge", "rally", "upgrade", "wins", "order",
        "expansion", "record", "strong", "launch", "approval", "raises", "buyback",
    ]
    negatives = [
        "misses", "loss", "fall", "falls", "drop", "weak", "downgrade", "probe", "fraud",
        "penalty", "resigns", "debt", "default", "cuts", "selloff", "crash",
    ]
    pos = sum(text.count(word) for word in positives)
    neg = sum(text.count(word) for word in negatives)
    score = min(10, max(-10, (pos - neg) * 2))
    if score >= 4:
        return score, "BULLISH", "#6ee7b7"
    if score <= -4:
        return score, "BEARISH", "#fca5a5"
    return score, "NEUTRAL", "#fcd34d"


def technical_summary(data):
    close = get_series(data, "Close")
    if close is None or len(close) < 200:
        return None

    ma50 = wma(close, 50)
    ma200 = wma(close, 200)
    momentum = rsi(close, 14)
    latest_close = float(close.iloc[-1])
    previous_close = float(close.iloc[-2])
    latest_50 = float(ma50.iloc[-1])
    latest_200 = float(ma200.iloc[-1])
    latest_rsi = float(momentum.iloc[-1])
    one_year_close = close[close.index >= close.index[-1] - pd.Timedelta(days=365)]
    one_year_return = ((latest_close / float(one_year_close.iloc[0])) - 1) * 100 if len(one_year_close) > 1 else 0

    score = 0
    reasons = []
    if latest_close > latest_50:
        score += 1
        reasons.append("Price is above 50-day WMA")
    else:
        score -= 1
        reasons.append("Price is below 50-day WMA")

    if latest_close > latest_200:
        score += 1
        reasons.append("Price is above 200-day WMA")
    else:
        score -= 1
        reasons.append("Price is below 200-day WMA")

    if latest_50 > latest_200:
        score += 1
        reasons.append("50-day WMA is above 200-day WMA")
    else:
        score -= 1
        reasons.append("50-day WMA is below 200-day WMA")

    if latest_rsi > 70:
        score -= 1
        reasons.append("RSI is overbought")
    elif latest_rsi < 30:
        score += 1
        reasons.append("RSI is oversold")
    else:
        reasons.append("RSI is neutral")

    return {
        "close": latest_close,
        "previous_close": previous_close,
        "change": latest_close - previous_close,
        "change_pct": ((latest_close - previous_close) / previous_close) * 100 if previous_close else 0,
        "wma50": latest_50,
        "wma200": latest_200,
        "rsi": latest_rsi,
        "one_year_return": one_year_return,
        "score": score,
        "reasons": reasons,
        "close_series": close,
        "wma50_series": ma50,
        "wma200_series": ma200,
        "rsi_series": momentum,
    }


def final_recommendation(tech, news_item):
    if tech is None:
        return "HOLD", "hold", 0, ["Insufficient technical data"]

    score = tech["score"]
    reasons = list(tech["reasons"])
    if news_item:
        news_score, news_label, _ = sentiment(news_item["title"])
        score += news_score / 2
        reasons.append(f"Selected news impact is {news_label.lower()} ({news_score:+.1f})")
    else:
        reasons.append("No selected news impact included yet")

    if score >= 3:
        return "BUY", "buy", score, reasons
    if score <= -2:
        return "SELL", "sell", score, reasons
    return "HOLD", "hold", score, reasons


stocks, live_constituents = load_nifty500()
stocks["Label"] = stocks["Company Name"] + " (" + stocks["Symbol"] + ")"

with st.sidebar:
    st.markdown('<div class="title">Nifty 500<br>Impact</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Stock News + Technicals</div>', unsafe_allow_html=True)
    st.markdown("---")
    search_text = st.text_input("Search Nifty 500 Stock", value="", placeholder="Type company or symbol, e.g. Reliance")
    if search_text.strip():
        query = search_text.strip().lower()
        filtered_stocks = stocks[
            stocks["Label"].str.lower().str.contains(query, regex=False)
            | stocks["Symbol"].str.lower().str.contains(query, regex=False)
        ].copy()
    else:
        filtered_stocks = stocks.copy()

    if filtered_stocks.empty:
        st.warning("No matching Nifty 500 stock found. Clear the search and try again.")
        filtered_stocks = stocks.copy()

    selected_label = st.selectbox("Select From List", filtered_stocks["Label"].tolist(), index=0)
    selected_row = filtered_stocks.loc[filtered_stocks["Label"] == selected_label].iloc[0]
    symbol = selected_row["Symbol"]
    company_name = selected_row["Company Name"]
    st.caption("Live Nifty 500 list loaded." if live_constituents else "Fallback list loaded.")

    if st.session_state.current_symbol != symbol:
        st.session_state.current_symbol = symbol
        st.session_state.news = []
        st.session_state.selected_news = None
        st.session_state.selected_news_index = 0
        st.session_state.manual_headline = ""
        st.session_state.news_message = ""

    st.markdown("### Stock News")
    if st.button("Fetch Latest Stock News", width="stretch"):
        st.session_state.news = fetch_stock_news(symbol, company_name)
        st.session_state.selected_news = None
        st.session_state.selected_news_index = 0
        st.session_state.news_message = (
            f"Loaded {len(st.session_state.news)} headlines for {symbol}."
            if st.session_state.news
            else f"No fresh headlines found for {symbol}. Try a manual headline."
        )
    if st.session_state.news_message:
        st.caption(st.session_state.news_message)

    st.markdown("### Manual News")
    headline = st.text_area("Paste one stock headline", st.session_state.manual_headline, height=90, label_visibility="collapsed")
    if st.button("Analyze Pasted News", width="stretch"):
        st.session_state.manual_headline = headline.strip()
        st.session_state.selected_news = (
            {"title": st.session_state.manual_headline, "source": "Manual"}
            if st.session_state.manual_headline
            else None
        )
    if st.button("Clear News", width="stretch"):
        st.session_state.news = []
        st.session_state.selected_news = None
        st.session_state.selected_news_index = 0
        st.session_state.manual_headline = ""
        st.session_state.news_message = ""


data = fetch_stock_data(symbol)
tech = technical_summary(data)
recommendation, rec_class, rec_score, rec_reasons = final_recommendation(tech, st.session_state.selected_news)

st.markdown(f'<div class="title">{escape(company_name)}</div>', unsafe_allow_html=True)
st.markdown(f'<div class="subtitle">{escape(symbol)}.NS | Nifty 500 stock impact dashboard</div>', unsafe_allow_html=True)

c1, c2 = st.columns([1.2, 2.2])
with c1:
    st.markdown(
        f'<div class="card {rec_class}"><div>Recommendation</div><div class="signal">{recommendation}</div><div>Composite score: {rec_score:+.1f}</div></div>',
        unsafe_allow_html=True,
    )
with c2:
    reason_html = "<br>".join(escape(reason) for reason in rec_reasons[:5])
    st.markdown(
        f'<div class="card"><strong>Why this signal?</strong><div style="margin-top: 8px;" class="small-note">{reason_html}</div></div>',
        unsafe_allow_html=True,
    )

st.info("Educational only. This is a rules-based news and technical-impact tool, not investment advice.")

st.markdown('<div class="section">Technicals</div>', unsafe_allow_html=True)
if tech is None:
    st.warning(f"Could not load enough price data for {symbol}. Select the exact stock from the list, then try again.")
else:
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Price", f"Rs {tech['close']:,.2f}", f"{tech['change']:+.2f} ({tech['change_pct']:+.2f}%)")
    m2.metric("1Y Return", f"{tech['one_year_return']:+.1f}%")
    m3.metric("WMA 50", f"Rs {tech['wma50']:,.2f}")
    m4.metric("WMA 200", f"Rs {tech['wma200']:,.2f}")
    m5.metric("RSI", f"{tech['rsi']:.0f}", "Overbought" if tech["rsi"] > 70 else "Oversold" if tech["rsi"] < 30 else "Neutral")

    one_year_start = tech["close_series"].index[-1] - pd.Timedelta(days=365)
    close_1y = tech["close_series"][tech["close_series"].index >= one_year_start]
    wma50_1y = tech["wma50_series"][tech["wma50_series"].index >= one_year_start]
    wma200_1y = tech["wma200_series"][tech["wma200_series"].index >= one_year_start]
    rsi_1y = tech["rsi_series"][tech["rsi_series"].index >= one_year_start]

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.68, 0.32])
    fig.add_trace(go.Scatter(x=close_1y.index, y=close_1y, name="Close", line=dict(color="#a5b4fc", width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=wma50_1y.index, y=wma50_1y, name="WMA 50", line=dict(color="#6ee7b7", width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=wma200_1y.index, y=wma200_1y, name="WMA 200", line=dict(color="#fcd34d", width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=rsi_1y.index, y=rsi_1y, name="RSI", line=dict(color="#ec4899", width=2)), row=2, col=1)
    fig.add_hline(70, line_dash="dash", line_color="rgba(252,165,165,0.5)", row=2, col=1)
    fig.add_hline(30, line_dash="dash", line_color="rgba(110,231,183,0.5)", row=2, col=1)
    fig.update_layout(
        height=620,
        hovermode="x unified",
        plot_bgcolor="rgba(30,27,75,0.3)",
        paper_bgcolor="rgba(10,14,39,0)",
        font=dict(color="#a5b4fc"),
    )
    st.plotly_chart(fig, width="stretch")

st.markdown("---")
st.markdown('<div class="section">Stock-Specific News</div>', unsafe_allow_html=True)
if st.session_state.news:
    labels = [f'{i + 1}. {item["title"]} ({item["source"]})' for i, item in enumerate(st.session_state.news)]
    selected = st.radio(
        "Latest headlines",
        labels,
        index=min(st.session_state.selected_news_index, len(labels) - 1),
        label_visibility="visible",
    )
    st.session_state.selected_news_index = labels.index(selected)
    chosen = st.session_state.news[st.session_state.selected_news_index]

    if st.button("Analyze Selected News", width="stretch"):
        st.session_state.selected_news = chosen

elif not st.session_state.selected_news:
    st.info("Fetch latest stock news from the sidebar, select one headline, then analyze the impact.")

if st.session_state.selected_news:
    news_score, news_label, color = sentiment(st.session_state.selected_news["title"])
    title = escape(st.session_state.selected_news["title"])
    source = escape(st.session_state.selected_news["source"])
    st.markdown(
        f'<div class="news-box" style="border-left-color: {color};"><strong>{title}</strong><br><span class="small-note">Source: {source} | News impact: {news_label} ({news_score:+.1f})</span></div>',
        unsafe_allow_html=True,
    )

st.markdown("---")
st.markdown(
    '<div style="text-align: center; color: #a5b4fc; font-size: 10px; margin-top: 20px;">NIFTY 500 STOCK IMPACT - EDUCATIONAL ONLY</div>',
    unsafe_allow_html=True,
)
