# Stock Market Research Agent

A comprehensive stock market research agent that analyzes stocks, fetches news, identifies trends, and provides specific recommendations and predictions.

## Features

### 📊 **Comprehensive Stock Analysis**
- **Technical Analysis**: Moving averages, RSI, MACD, Bollinger Bands, volume analysis
- **Fundamental Analysis**: P/E ratios, financial ratios, growth metrics, valuation indicators
- **Sentiment Analysis**: News sentiment analysis using NLP
- **Market Trends**: Broader market context and sector analysis

### 📰 **News Integration**
- Fetches news from multiple sources (Yahoo Finance, Google Finance, MarketWatch)
- Analyzes sentiment of news articles
- Provides recent headlines and summaries

### 🤖 **AI-Powered Recommendations**
- Uses OpenAI GPT-4 for intelligent analysis
- Generates specific buy/hold/sell recommendations
- Provides confidence levels and reasoning
- Creates price targets for different timeframes

### 📈 **Predictions & Forecasting**
- Bull, base, and bear case scenarios
- Confidence intervals for predictions
- Multiple timeframe analysis (1 week to 1 year)

### 🎯 **Risk Management**
- Risk tolerance-based recommendations
- Investment amount optimization
- Risk factor identification

## Parameters

### Required Parameters
- **`stock_symbols`**: Comma-separated list of stock symbols (e.g., "AAPL,MSFT,GOOGL")

### Analysis Configuration
- **`analysis_depth`**: Level of analysis (basic, standard, comprehensive, expert)
- **`prediction_timeframe`**: Timeframe for predictions (1week, 1month, 3months, 6months, 1year)
- **`risk_tolerance`**: Risk tolerance level (conservative, moderate, aggressive)
- **`investment_amount`**: Investment amount to consider (in USD)

### Analysis Options
- **`include_news`**: Include recent news analysis (default: true)
- **`include_technical_analysis`**: Include technical indicators (default: true)
- **`include_fundamental_analysis`**: Include financial ratios (default: true)
- **`include_sentiment_analysis`**: Include sentiment analysis (default: true)
- **`include_competitor_analysis`**: Include competitor analysis (default: true)
- **`include_market_trends`**: Include broader market analysis (default: true)

### Optional API Keys
- **`api_key_alpha_vantage`**: Alpha Vantage API key for enhanced data
- **`api_key_news`**: News API key for additional news sources

## Usage Example

```python
# Example input for the agent
input_data = {
    "stock_symbols": "AAPL,MSFT,GOOGL",
    "analysis_depth": "comprehensive",
    "prediction_timeframe": "3months",
    "include_news": True,
    "include_technical_analysis": True,
    "include_fundamental_analysis": True,
    "include_sentiment_analysis": True,
    "risk_tolerance": "moderate",
    "investment_amount": 10000,
    "include_competitor_analysis": True,
    "include_market_trends": True
}

# The agent will return comprehensive analysis for each stock
```

## Output Structure

The agent returns a comprehensive analysis with the following structure:

```json
{
  "status": "success",
  "summary": {
    "analysis_date": "2024-01-15T10:30:00",
    "symbols_analyzed": ["AAPL", "MSFT", "GOOGL"],
    "analysis_depth": "comprehensive",
    "prediction_timeframe": "3months",
    "risk_tolerance": "moderate",
    "investment_amount": 10000,
    "overall_recommendations": {
      "AAPL": "buy",
      "MSFT": "hold",
      "GOOGL": "buy"
    }
  },
  "detailed_analysis": {
    "AAPL": {
      "symbol": "AAPL",
      "analysis_date": "2024-01-15T10:30:00",
      "summary": {
        "current_price": 150.25,
        "market_cap": 2500000000000,
        "sector": "Technology",
        "industry": "Consumer Electronics"
      },
      "technical_analysis": {
        "sma_20": 148.50,
        "rsi": 65.2,
        "macd": 2.15,
        "trend_20d": 5.2
      },
      "fundamental_analysis": {
        "pe_ratio": 25.5,
        "price_to_book": 15.2,
        "return_on_equity": 0.18
      },
      "sentiment_analysis": {
        "sentiment_score": 0.15,
        "sentiment_label": "positive",
        "confidence": 0.75
      },
      "recommendations": {
        "recommendation": "buy",
        "confidence_level": 75,
        "reasoning": ["Strong technical indicators", "Positive sentiment", "Solid fundamentals"],
        "risk_factors": ["Market volatility", "Supply chain risks"],
        "price_targets": {"3months": 165.00},
        "action_plan": ["Consider dollar-cost averaging", "Set stop-loss at $140"]
      },
      "predictions": {
        "bull_case": {"price": 175.00, "reasoning": "Strong product cycle"},
        "base_case": {"price": 165.00, "reasoning": "Steady growth"},
        "bear_case": {"price": 140.00, "reasoning": "Market correction"}
      }
    }
  }
}
```

## Technical Indicators

The agent calculates and analyzes the following technical indicators:

### Moving Averages
- Simple Moving Average (SMA) 20, 50, 200 days
- Price vs moving average relationships

### Momentum Indicators
- Relative Strength Index (RSI)
- Moving Average Convergence Divergence (MACD)

### Volatility Indicators
- Bollinger Bands
- Price position within bands

### Volume Analysis
- Average volume vs current volume
- Volume trends

## Fundamental Metrics

### Valuation Ratios
- Price-to-Earnings (P/E) ratio
- Forward P/E ratio
- Price-to-Book (P/B) ratio
- Price-to-Sales (P/S) ratio
- PEG ratio

### Financial Health
- Debt-to-Equity ratio
- Current ratio
- Quick ratio
- Return on Equity (ROE)
- Return on Assets (ROA)

### Growth Metrics
- Revenue growth
- Earnings growth
- Profit margins
- Operating margins

## Sentiment Analysis

The agent performs sentiment analysis on news articles using:
- TextBlob for sentiment scoring
- Analysis of headlines and summaries
- Sentiment confidence levels
- Source diversity analysis

## Risk Assessment

The agent considers various risk factors:
- Market volatility
- Company-specific risks
- Sector risks
- Liquidity concerns
- Economic factors

## Installation

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables (optional):
```bash
export OPENAI_API_KEY="your_openai_api_key"
export ALPHA_VANTAGE_API_KEY="your_alpha_vantage_key"
export NEWS_API_KEY="your_news_api_key"
```

## Dependencies

- **yfinance**: Yahoo Finance data fetching
- **pandas**: Data manipulation and analysis
- **numpy**: Numerical computations
- **requests**: HTTP requests for news fetching
- **textblob**: Sentiment analysis
- **openai**: AI-powered analysis
- **plotly**: Data visualization (for future enhancements)
- **ta**: Technical analysis indicators

## Limitations

1. **Data Sources**: Relies on Yahoo Finance for stock data, which may have rate limits
2. **News Sources**: News fetching is limited to publicly accessible sources
3. **Predictions**: All predictions are estimates and should not be considered financial advice
4. **API Keys**: Some enhanced features require API keys for external services

## Disclaimer

This agent is for educational and research purposes only. The recommendations and predictions provided should not be considered as financial advice. Always consult with a qualified financial advisor before making investment decisions. Past performance does not guarantee future results.

## Future Enhancements

- Real-time data streaming
- Advanced charting and visualization
- Portfolio optimization
- Options analysis
- Cryptocurrency support
- Machine learning-based predictions
- Integration with trading platforms 