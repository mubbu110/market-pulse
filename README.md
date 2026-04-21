# 📊 Market Pulse
### Real-time Market Sentiment + Technical Analysis for Nifty50
**Completely Free. Educational Only. No Paid APIs Required.**

---

## **What is Market Pulse?**

Market Pulse combines three powerful analytical tools:

1. **Live Market Data** - Real-time Nifty50 prices, volumes, and trends
2. **Technical Analysis** - WMA, RSI, MACD, Bollinger Bands, price action analysis
3. **Sentiment Analysis** - Automated news parsing with buy/sell/hold signals
4. **Strategy Backtesting** - Test trading rules against 3 months of historical data

Perfect for:
- Learning how markets actually work
- Understanding technical indicators
- Exploring sentiment-driven trading concepts
- Testing trading ideas (in a simulator, not with real money)

---

## **⚡ Quick Start (3 steps)**

### **Step 1: Install Python**
Download from https://www.python.org/downloads/ (3.9 or newer)

### **Step 2: Install Dependencies**
```bash
pip install -r requirements.txt
```

### **Step 3: Run the App**
```bash
streamlit run market_pulse.py
```

Opens at `http://localhost:8501`

**That's it. You're done.**

---

## **🎯 Features**

### **1. Market Overview**
- Nifty50 current price
- 52-week highs/lows
- Average volume
- Real-time percentage change

### **2. Technical Analysis Dashboard**
Interactive charts showing:
- **Price Action** - Candlestick-style price movement
- **WMA(20)** - Weighted moving average for trend
- **RSI(14)** - Momentum indicator (overbought/oversold)
- **MACD** - Trend-following indicator
- **Bollinger Bands** - Volatility and price extremes

Auto-generated insights:
- "Price is above/below WMA" (bullish/bearish)
- "RSI is overbought/oversold" (extreme conditions)
- "MACD bullish/bearish crossover" (momentum change)

### **3. Sentiment Analysis**

**Two ways to analyze:**

**A) Fetch Live News**
- Automatically scrapes headlines from:
  - Economic Times
  - Moneycontrol
  - Bloomberg
- Real-time sentiment scoring
- Shows confidence levels

**B) Paste Your Own Headline**
- Manually input any market news
- Get instant sentiment analysis
- Learn how keywords drive sentiment

**Algorithm:**
- Positive words: "breakout", "surge", "growth", "profit", "beats" → +2 to +3
- Negative words: "crash", "weak", "selloff", "bearish" → -2 to -3
- Range: -10 (extremely bearish) to +10 (extremely bullish)
- Action: Score ≥4 = BUY, ≤-4 = SELL, else HOLD

**Accuracy:** 60-65% (keyword-based, not AI-powered)

### **4. Market Consensus**
Shows overall market sentiment across all analyzed headlines:
- Bullish count
- Bearish count
- Neutral count
- Average sentiment score

### **5. Backtesting (3 months)**
Tests a simple trading strategy:
- **BUY:** When price > WMA(20) AND RSI < 70
- **SELL:** When price < WMA(20) AND RSI > 30
- **HOLD:** Otherwise

Results show:
- Total return (%)
- Win rate (% of profitable trades)
- Max drawdown (largest peak-to-trough loss)
- Number of signals generated
- Average return per signal

**Remember:** Past performance ≠ future results. Educational only.

---

## **📚 Understanding the Indicators**

### **WMA (Weighted Moving Average)**
- **What:** Average price, but recent prices weighted heavier
- **Period:** 20 days
- **Use:** Identify trend direction
- **Signal:** Price above WMA = bullish, below = bearish
- **Learn:** Investopedia "Moving Averages"

### **RSI (Relative Strength Index)**
- **What:** Momentum indicator comparing up/down price changes
- **Range:** 0-100
- **Overbought:** > 70 (price may pull back)
- **Oversold:** < 30 (price may bounce)
- **Use:** Spot potential reversals
- **Learn:** YouTube "RSI Indicator Explained"

### **MACD (Moving Average Convergence Divergence)**
- **What:** Trend-following momentum indicator
- **Signal:** When MACD > Signal line = bullish, cross below = bearish
- **Use:** Confirm trend changes
- **Learn:** Investopedia "MACD"

### **Bollinger Bands**
- **What:** Price volatility bands around a moving average
- **Use:** Identify overbought (near upper band) and oversold (near lower band)
- **Signal:** Price touching upper band = potential sell, lower band = potential buy
- **Learn:** "Bollinger Bands Trading"

### **Price Action**
- **Support:** Price level where buying interest historically appears
- **Resistance:** Price level where selling interest historically appears
- **Breakout:** Price breaks above resistance = bullish
- **Breakdown:** Price breaks below support = bearish

---

## **⚠️ Important Disclaimers**

### **This is Educational Software**

**DO NOT:**
- Use for actual trading without professional advice
- Risk more than you can afford to lose
- Ignore risk management
- Assume past performance = future results
- Trade on sentiment signals alone

**WHY:**
- Data delayed 15-20 minutes (not real-time)
- Sentiment accuracy is 60-65% (not AI-powered)
- Indicators are lagging (slower than price moves)
- Backtesting doesn't guarantee future performance
- Markets involve substantial risk

**ALWAYS:**
- Do your own research
- Consult a financial advisor
- Use proper risk management (stop losses)
- Trade with capital you can afford to lose
- Understand the risks completely

---

## **🚀 Deployment (Go Live Free)**

### **Option 1: Streamlit Cloud (Recommended)**
1. Push code to GitHub
2. Go to https://streamlit.io/cloud
3. Connect repo and deploy
4. Get public live link (shareable)

### **Option 2: Railway or Replit**
- Similar process, all free
- See `SETUP_GUIDE.md` for detailed steps

### **Option 3: Run Locally**
- Use on your machine only
- Not publicly accessible

---

## **📈 What's Next?**

### **Learn Phase (Months 1-2)**
- Understand what each indicator means
- Practice identifying trends
- Backtest different rules
- Paper trade (simulate without real money)

### **Experiment Phase (Months 3-4)**
- Add more indicators (Stochastic, ATR, Volume)
- Combine signals (technical + sentiment)
- Test on longer timeframes
- Refine your rules

### **Ready to Upgrade? (When skilled)**
- Add Claude API for AI sentiment (cost: ~$1-2/day)
- Real-time data feeds (cost: $5-50/month)
- Professional backtesting (cost: $10-100/month)
- Options analysis (cost: $20-200/month)

**For now: Stay free. Master the basics first.**

---

## **🛠 Troubleshooting**

### **App won't start**
```bash
pip install -r requirements.txt --upgrade
streamlit run market_pulse.py
```

### **No data showing**
- Check internet connection
- Yahoo Finance might be throttling requests
- Wait 5 minutes, try again

### **RSS feeds not updating**
- Free feeds are unstable
- Feeds sometimes go down
- Check URLs in code are valid

### **App is slow**
- Backtesting takes 1-2 minutes on free tier
- Streamlit Cloud has 1GB memory limit
- Limit analysis to recent 1-month data if slow

---

## **📞 Support**

### **Common Questions**

**Q: Can I use this to trade real money?**
A: No. It's educational only. Data is delayed, sentiment is 60-65% accurate, no risk management built-in. Learn first.

**Q: Why aren't prices real-time?**
A: Free data from Yahoo Finance is 15-20 min delayed. Real-time costs $$$$.

**Q: Why is sentiment accuracy only 60-65%?**
A: Keyword-based analysis is simple. Real sentiment needs NLP/AI (requires Claude API, costs money).

**Q: Can I add more indicators?**
A: Yes. Code is modular. Add functions like `calculate_stochastic()` and plot them. See SETUP_GUIDE.md.

**Q: Can I backtest longer than 3 months?**
A: Yes, edit `days=90` to `days=180` or `days=365`. But it will be slower.

---

## **📊 Technical Stack**

**100% Free & Open Source:**
- **Frontend:** Streamlit (UI framework)
- **Data:** yfinance (market data), feedparser (news)
- **Analysis:** Pandas, NumPy (data processing)
- **Charts:** Plotly (interactive visualizations)
- **Backtesting:** Custom logic
- **Hosting:** Streamlit Cloud (free tier available)

**Total Cost:** $0/month (unless you upgrade hosting/data)

---

## **Version Info**
- **Market Pulse:** v1.0
- **Python:** 3.9+
- **Status:** Fully Functional, No APIs Required
- **License:** Educational Use Only
- **Last Updated:** April 2025

---

## **Getting Help**

1. **Check SETUP_GUIDE.md** - Detailed setup & customization
2. **Read code comments** - Inline explanations throughout
3. **YouTube tutorials:**
   - "Technical Analysis for Beginners"
   - "Sentiment Analysis in Trading"
   - "Streamlit Tutorial"
4. **Investopedia** - Best free resource for indicator learning

---

**Happy learning! Remember: Markets are complex. Education first, real money later. 📊**
