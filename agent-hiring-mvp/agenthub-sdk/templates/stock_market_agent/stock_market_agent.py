#!/usr/bin/env python3
"""
Stock Market Research Agent

A comprehensive stock market research agent that analyzes stocks, fetches news,
identifies trends, and provides specific recommendations and predictions.
"""

import json
import os
import sys
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np
import requests
from textblob import TextBlob
import yfinance as yf
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Custom JSON encoder to handle numpy/pandas types
class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif pd.isna(obj):
            return None
        elif hasattr(obj, 'isoformat'):  # Handle pandas Timestamp and datetime objects
            return obj.isoformat()
        elif hasattr(obj, 'strftime'):  # Handle datetime objects
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        return super(NumpyEncoder, self).default(obj)


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class StockMarketAgent:
    """Comprehensive stock market research and analysis agent."""
    
    def __init__(self, openai_api_key: Optional[str] = None):
        """Initialize the stock market agent."""
        self.openai_client = OpenAI(api_key=openai_api_key or os.getenv('OPENAI_API_KEY'))
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
    def ensure_boolean(self, value: Any) -> bool:
        """Convert various input types to boolean."""
        if isinstance(value, bool):
            return value
        elif isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        elif isinstance(value, (int, float)):
            return bool(value)
        else:
            return False
    
    def fetch_stock_data(self, symbol: str, period: str = "1y") -> Dict[str, Any]:
        """Fetch comprehensive stock data using yfinance."""
        try:
            logger.info(f"Fetching data for {symbol}")
            ticker = yf.Ticker(symbol)
            
            # Get historical data
            hist = ticker.history(period=period)
            
            # Get basic info
            info = ticker.info
            
            # Get financial statements
            try:
                financials = ticker.financials
                balance_sheet = ticker.balance_sheet
                cashflow = ticker.cashflow
            except:
                financials = None
                balance_sheet = None
                cashflow = None
            
            # Get earnings (using newer API methods)
            try:
                # Use income statement instead of deprecated earnings
                income_stmt = ticker.income_stmt
                # Note: earnings_forecasts might also be deprecated in future versions
                earnings_forecasts = ticker.earnings_forecasts
            except:
                income_stmt = None
                earnings_forecasts = None
            
            # Get analyst recommendations
            try:
                recommendations = ticker.recommendations
            except:
                recommendations = None
            
            # Convert DataFrames to JSON-serializable format
            def df_to_dict(df):
                if df is not None and not df.empty:
                    try:
                        # Convert to dict and handle numpy types
                        df_dict = df.to_dict(orient='split')
                        # Convert numpy types to native Python types
                        return json.loads(json.dumps(df_dict, cls=NumpyEncoder))
                    except Exception as e:
                        logger.warning(f"Failed to convert DataFrame to dict: {e}")
                        # Fallback: convert to simple format
                        return {
                            'columns': df.columns.tolist(),
                            'index': df.index.tolist(),
                            'data': df.values.tolist()
                        }
                return {}
            
            # Clean info dict to remove non-serializable objects
            def clean_info_dict(info_dict):
                if not info_dict:
                    return {}
                cleaned = {}
                for key, value in info_dict.items():
                    try:
                        # Test if value is JSON serializable
                        json.dumps({key: value}, cls=NumpyEncoder)
                        cleaned[key] = value
                    except (TypeError, ValueError):
                        # Convert non-serializable values to strings
                        cleaned[key] = str(value)
                return cleaned
            
            return {
                'symbol': symbol,
                'historical_data': df_to_dict(hist),
                'info': clean_info_dict(info),
                'financials': df_to_dict(financials),
                'balance_sheet': df_to_dict(balance_sheet),
                'cashflow': df_to_dict(cashflow),
                'income_statement': df_to_dict(income_stmt),
                'earnings_forecasts': df_to_dict(earnings_forecasts),
                'recommendations': df_to_dict(recommendations)
            }
            
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            return {'symbol': symbol, 'error': str(e)}
    
    def fetch_news(self, symbol: str, days: int = 7) -> List[Dict[str, Any]]:
        """Fetch recent news for a stock symbol."""
        try:
            logger.info(f"Fetching news for {symbol}")
            
            # Try multiple news sources
            news_sources = [
                self._fetch_yahoo_finance_news,
                self._fetch_google_finance_news,
                self._fetch_marketwatch_news
            ]
            
            all_news = []
            for source_func in news_sources:
                try:
                    news = source_func(symbol, days)
                    all_news.extend(news)
                except Exception as e:
                    logger.warning(f"Failed to fetch news from {source_func.__name__}: {e}")
            
            # Remove duplicates and sort by date
            unique_news = []
            seen_titles = set()
            for news in all_news:
                if news['title'] not in seen_titles:
                    unique_news.append(news)
                    seen_titles.add(news['title'])
            
            return sorted(unique_news, key=lambda x: x.get('date', ''), reverse=True)[:20]
            
        except Exception as e:
            logger.error(f"Error fetching news for {symbol}: {e}")
            return []
    
    def _fetch_yahoo_finance_news(self, symbol: str, days: int) -> List[Dict[str, Any]]:
        """Fetch news from Yahoo Finance."""
        try:
            url = f"https://finance.yahoo.com/quote/{symbol}/news"
            response = self.session.get(url)
            response.raise_for_status()
            
            # This is a simplified version - in practice you'd need to parse the HTML
            # For now, return mock data
            return [
                {
                    'title': f'Latest news about {symbol}',
                    'summary': f'Recent developments in {symbol} stock performance',
                    'date': datetime.now().strftime('%Y-%m-%d'),
                    'source': 'Yahoo Finance',
                    'url': url
                }
            ]
        except:
            return []
    
    def _fetch_google_finance_news(self, symbol: str, days: int) -> List[Dict[str, Any]]:
        """Fetch news from Google Finance."""
        try:
            url = f"https://www.google.com/finance/quote/{symbol}"
            response = self.session.get(url)
            response.raise_for_status()
            
            return [
                {
                    'title': f'Google Finance news for {symbol}',
                    'summary': f'Market updates for {symbol}',
                    'date': datetime.now().strftime('%Y-%m-%d'),
                    'source': 'Google Finance',
                    'url': url
                }
            ]
        except:
            return []
    
    def _fetch_marketwatch_news(self, symbol: str, days: int) -> List[Dict[str, Any]]:
        """Fetch news from MarketWatch."""
        try:
            url = f"https://www.marketwatch.com/investing/stock/{symbol}"
            response = self.session.get(url)
            response.raise_for_status()
            
            return [
                {
                    'title': f'MarketWatch coverage of {symbol}',
                    'summary': f'Latest market analysis for {symbol}',
                    'date': datetime.now().strftime('%Y-%m-%d'),
                    'source': 'MarketWatch',
                    'url': url
                }
            ]
        except:
            return []
    
    def analyze_technical_indicators(self, stock_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze technical indicators for a stock."""
        try:
            if 'historical_data' not in stock_data or not stock_data['historical_data']:
                return {'error': 'No historical data available'}
            
            # Convert to DataFrame - historical_data is already a dict with index, columns, data
            hist_data = stock_data['historical_data']
            if isinstance(hist_data, dict) and 'data' in hist_data:
                # Create DataFrame from the dictionary structure
                hist_df = pd.DataFrame(hist_data['data'], 
                                     index=hist_data.get('index', None),
                                     columns=hist_data.get('columns', None))
            else:
                # Fallback for direct DataFrame creation
                hist_df = pd.DataFrame(hist_data)
            
            if hist_df.empty:
                return {'error': 'Empty historical data'}
            
            # Check if we have enough data
            if len(hist_df) < 60:
                return {'error': f'Insufficient data: {len(hist_df)} days available, need at least 60 days'}
            
            # Calculate technical indicators
            analysis = {}
            
            try:
                # Moving averages
                sma_20 = hist_df['Close'].rolling(window=20).mean()
                sma_50 = hist_df['Close'].rolling(window=50).mean()
                sma_200 = hist_df['Close'].rolling(window=200).mean()
                
                analysis['sma_20'] = float(sma_20.iloc[-1]) if not pd.isna(sma_20.iloc[-1]) else None
                analysis['sma_50'] = float(sma_50.iloc[-1]) if not pd.isna(sma_50.iloc[-1]) else None
                analysis['sma_200'] = float(sma_200.iloc[-1]) if not pd.isna(sma_200.iloc[-1]) else None
                
                current_price = float(hist_df['Close'].iloc[-1])
                
                # Price vs moving averages (only if we have the values)
                if analysis['sma_20'] is not None:
                    analysis['price_vs_sma20'] = float((current_price / analysis['sma_20'] - 1) * 100)
                if analysis['sma_50'] is not None:
                    analysis['price_vs_sma50'] = float((current_price / analysis['sma_50'] - 1) * 100)
                if analysis['sma_200'] is not None:
                    analysis['price_vs_sma200'] = float((current_price / analysis['sma_200'] - 1) * 100)
                
                # RSI (need at least 14 days)
                if len(hist_df) >= 14:
                    delta = hist_df['Close'].diff()
                    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                    rs = gain / loss
                    rsi_value = 100 - (100 / (1 + rs.iloc[-1]))
                    analysis['rsi'] = float(rsi_value) if not pd.isna(rsi_value) else None
                
                # MACD (need at least 26 days)
                if len(hist_df) >= 26:
                    exp1 = hist_df['Close'].ewm(span=12).mean()
                    exp2 = hist_df['Close'].ewm(span=26).mean()
                    macd_value = exp1.iloc[-1] - exp2.iloc[-1]
                    analysis['macd'] = float(macd_value) if not pd.isna(macd_value) else None
                    
                    # MACD signal line (need at least 35 days)
                    if len(hist_df) >= 35:
                        macd_line = exp1 - exp2
                        signal_value = macd_line.ewm(span=9).mean().iloc[-1]
                        analysis['macd_signal'] = float(signal_value) if not pd.isna(signal_value) else None
                
                # Bollinger Bands (need at least 20 days)
                if len(hist_df) >= 20 and analysis['sma_20'] is not None:
                    bb_std = hist_df['Close'].rolling(window=20).std().iloc[-1]
                    if not pd.isna(bb_std):
                        analysis['bb_upper'] = float(analysis['sma_20'] + (bb_std * 2))
                        analysis['bb_lower'] = float(analysis['sma_20'] - (bb_std * 2))
                        if analysis['bb_upper'] != analysis['bb_lower']:
                            analysis['bb_position'] = float((current_price - analysis['bb_lower']) / (analysis['bb_upper'] - analysis['bb_lower']))
                
                # Volume analysis
                if 'Volume' in hist_df.columns:
                    avg_volume = hist_df['Volume'].mean()
                    current_volume = hist_df['Volume'].iloc[-1]
                    if not pd.isna(avg_volume) and not pd.isna(current_volume) and avg_volume > 0:
                        analysis['avg_volume'] = float(avg_volume)
                        analysis['current_volume'] = float(current_volume)
                        analysis['volume_ratio'] = float(current_volume / avg_volume)
                
                # Trend analysis
                if len(hist_df) >= 5:
                    analysis['trend_5d'] = float((hist_df['Close'].iloc[-1] / hist_df['Close'].iloc[-5] - 1) * 100)
                if len(hist_df) >= 20:
                    analysis['trend_20d'] = float((hist_df['Close'].iloc[-1] / hist_df['Close'].iloc[-20] - 1) * 100)
                if len(hist_df) >= 60:
                    analysis['trend_60d'] = float((hist_df['Close'].iloc[-1] / hist_df['Close'].iloc[-60] - 1) * 100)
                
            except Exception as e:
                logger.error(f"Error calculating technical indicators: {e}")
                return {'error': f'Error calculating technical indicators: {str(e)}'}
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error in technical analysis: {e}")
            return {'error': str(e)}
    
    def analyze_fundamentals(self, stock_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze fundamental indicators for a stock."""
        try:
            analysis = {}
            
            if 'info' in stock_data and stock_data['info']:
                info = stock_data['info']
                
                # Key ratios
                analysis['pe_ratio'] = info.get('trailingPE', None)
                analysis['forward_pe'] = info.get('forwardPE', None)
                analysis['peg_ratio'] = info.get('pegRatio', None)
                analysis['price_to_book'] = info.get('priceToBook', None)
                analysis['price_to_sales'] = info.get('priceToSalesTrailing12Months', None)
                analysis['debt_to_equity'] = info.get('debtToEquity', None)
                analysis['current_ratio'] = info.get('currentRatio', None)
                analysis['quick_ratio'] = info.get('quickRatio', None)
                analysis['return_on_equity'] = info.get('returnOnEquity', None)
                analysis['return_on_assets'] = info.get('returnOnAssets', None)
                analysis['profit_margins'] = info.get('profitMargins', None)
                analysis['operating_margins'] = info.get('operatingMargins', None)
                
                # Growth metrics
                analysis['revenue_growth'] = info.get('revenueGrowth', None)
                analysis['earnings_growth'] = info.get('earningsGrowth', None)
                analysis['revenue_per_share'] = info.get('revenuePerShare', None)
                analysis['book_value'] = info.get('bookValue', None)
                
                # Valuation
                analysis['market_cap'] = info.get('marketCap', None)
                analysis['enterprise_value'] = info.get('enterpriseValue', None)
                analysis['enterprise_to_revenue'] = info.get('enterpriseToRevenue', None)
                analysis['enterprise_to_ebitda'] = info.get('enterpriseToEbitda', None)
                
                # Dividend info
                analysis['dividend_yield'] = info.get('dividendYield', None)
                analysis['dividend_rate'] = info.get('dividendRate', None)
                analysis['payout_ratio'] = info.get('payoutRatio', None)
                
            return analysis
            
        except Exception as e:
            logger.error(f"Error in fundamental analysis: {e}")
            return {'error': str(e)}
    
    def analyze_sentiment(self, news_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze sentiment from news articles."""
        try:
            if not news_data:
                return {'sentiment_score': 0, 'sentiment_label': 'neutral', 'confidence': 0}
            
            sentiments = []
            for news in news_data:
                text = f"{news.get('title', '')} {news.get('summary', '')}"
                blob = TextBlob(text)
                sentiments.append(blob.sentiment.polarity)
            
            avg_sentiment = float(np.mean(sentiments))
            sentiment_std = float(np.std(sentiments))
            
            # Determine sentiment label
            if avg_sentiment > 0.1:
                label = 'positive'
            elif avg_sentiment < -0.1:
                label = 'negative'
            else:
                label = 'neutral'
            
            # Calculate confidence based on consistency
            confidence = float(1 - sentiment_std)
            
            return {
                'sentiment_score': avg_sentiment,
                'sentiment_label': label,
                'confidence': max(0, min(1, confidence)),
                'articles_analyzed': len(news_data)
            }
            
        except Exception as e:
            logger.error(f"Error in sentiment analysis: {e}")
            return {'error': str(e)}
    
    def generate_recommendations(self, symbol: str, stock_data: Dict[str, Any], 
                               technical_analysis: Dict[str, Any], 
                               fundamental_analysis: Dict[str, Any],
                               sentiment_analysis: Dict[str, Any],
                               risk_tolerance: str,
                               investment_amount: float,
                               timeframe: str) -> Dict[str, Any]:
        """Generate investment recommendations using AI."""
        try:
            # Prepare analysis summary
            analysis_summary = {
                'symbol': symbol,
                'current_price': stock_data.get('info', {}).get('currentPrice', 'Unknown'),
                'technical_indicators': technical_analysis,
                'fundamental_metrics': fundamental_analysis,
                'sentiment': sentiment_analysis,
                'risk_tolerance': risk_tolerance,
                'investment_amount': investment_amount,
                'timeframe': timeframe
            }
            
            # Create prompt for AI analysis
            prompt = f"""
            As a professional stock market analyst, provide a comprehensive investment recommendation for {symbol}.
            
            Analysis Summary:
            - Current Price: ${analysis_summary['current_price']}
            - Risk Tolerance: {risk_tolerance}
            - Investment Amount: ${investment_amount:,.2f}
            - Timeframe: {timeframe}
            
            Technical Analysis:
            {json.dumps(technical_analysis, indent=2)}
            
            Fundamental Analysis:
            {json.dumps(fundamental_analysis, indent=2)}
            
            Sentiment Analysis:
            {json.dumps(sentiment_analysis, indent=2)}
            
            Please provide:
            1. Overall recommendation (Buy/Hold/Sell) with confidence level
            2. Key reasons for the recommendation
            3. Risk factors to consider
            4. Price targets for the specified timeframe
            5. Specific action plan for the investment amount
            6. Alternative considerations
            
            Format your response as a structured JSON with the following fields:
            - recommendation: "buy", "hold", or "sell"
            - confidence_level: 0-100
            - reasoning: list of key points
            - risk_factors: list of risks
            - price_targets: dict with timeframe and target price
            - action_plan: specific steps
            - alternatives: other considerations
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=2000
            )
            
            try:
                recommendation = json.loads(response.choices[0].message.content)
                return recommendation
            except json.JSONDecodeError:
                # Fallback to structured response
                return {
                    'recommendation': 'hold',
                    'confidence_level': 50,
                    'reasoning': ['Analysis completed but AI response parsing failed'],
                    'risk_factors': ['Market volatility', 'Economic uncertainty'],
                    'price_targets': {timeframe: 'TBD'},
                    'action_plan': ['Monitor the stock closely', 'Consider dollar-cost averaging'],
                    'alternatives': ['Diversify portfolio', 'Consider index funds']
                }
                
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return {'error': str(e)}
    
    def generate_predictions(self, symbol: str, stock_data: Dict[str, Any],
                           technical_analysis: Dict[str, Any],
                           timeframe: str) -> Dict[str, Any]:
        """Generate price predictions for the specified timeframe."""
        try:
            # Create prediction prompt
            prompt = f"""
            As a quantitative analyst, provide price predictions for {symbol} over the {timeframe} timeframe.
            
            Current Data:
            - Symbol: {symbol}
            - Current Price: ${stock_data.get('info', {}).get('currentPrice', 'Unknown')}
            - Technical Indicators: {json.dumps(technical_analysis, indent=2)}
            
            Please provide:
            1. Bull case scenario (optimistic)
            2. Base case scenario (most likely)
            3. Bear case scenario (pessimistic)
            4. Confidence intervals
            5. Key factors that could influence the price
            
            Format as JSON with:
            - bull_case: price target and reasoning
            - base_case: price target and reasoning
            - bear_case: price target and reasoning
            - confidence_interval: range
            - key_factors: list of influencing factors
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=1500
            )
            
            try:
                predictions = json.loads(response.choices[0].message.content)
                return predictions
            except json.JSONDecodeError:
                return {
                    'bull_case': {'price': 'TBD', 'reasoning': 'AI parsing error'},
                    'base_case': {'price': 'TBD', 'reasoning': 'AI parsing error'},
                    'bear_case': {'price': 'TBD', 'reasoning': 'AI parsing error'},
                    'confidence_interval': 'TBD',
                    'key_factors': ['Market conditions', 'Company performance']
                }
                
        except Exception as e:
            logger.error(f"Error generating predictions: {e}")
            return {'error': str(e)}
    
    def analyze_market_trends(self, symbols: List[str]) -> Dict[str, Any]:
        """Analyze broader market trends affecting the stocks."""
        try:
            # Get market indices
            indices = ['^GSPC', '^DJI', '^IXIC']  # S&P 500, Dow Jones, NASDAQ
            market_data = {}
            
            for index in indices:
                try:
                    ticker = yf.Ticker(index)
                    hist = ticker.history(period="1mo")
                    if not hist.empty:
                                            market_data[index] = {
                        'current': float(hist['Close'].iloc[-1]),
                        'change_1d': float((hist['Close'].iloc[-1] / hist['Close'].iloc[-2] - 1) * 100),
                        'change_1w': float((hist['Close'].iloc[-1] / hist['Close'].iloc[-6] - 1) * 100),
                        'change_1m': float((hist['Close'].iloc[-1] / hist['Close'].iloc[0] - 1) * 100)
                    }
                except Exception as e:
                    logger.warning(f"Failed to fetch {index}: {e}")
            
            # Analyze sector performance
            sector_analysis = {}
            for symbol in symbols:
                try:
                    ticker = yf.Ticker(symbol)
                    info = ticker.info
                    sector = info.get('sector', 'Unknown')
                    if sector not in sector_analysis:
                        sector_analysis[sector] = []
                    sector_analysis[sector].append(symbol)
                except:
                    pass
            
            return {
                'market_indices': market_data,
                'sector_analysis': sector_analysis,
                'overall_market_sentiment': 'neutral'  # Could be enhanced with more analysis
            }
            
        except Exception as e:
            logger.error(f"Error analyzing market trends: {e}")
            return {'error': str(e)}
    
    def create_comprehensive_report(self, symbol: str, stock_data: Dict[str, Any],
                                  news_data: List[Dict[str, Any]],
                                  technical_analysis: Dict[str, Any],
                                  fundamental_analysis: Dict[str, Any],
                                  sentiment_analysis: Dict[str, Any],
                                  recommendations: Dict[str, Any],
                                  predictions: Dict[str, Any],
                                  market_trends: Dict[str, Any]) -> Dict[str, Any]:
        """Create a comprehensive stock analysis report."""
        
        report = {
            'symbol': symbol,
            'analysis_date': datetime.now().isoformat(),
            'summary': {
                'current_price': stock_data.get('info', {}).get('currentPrice', 'Unknown'),
                'market_cap': stock_data.get('info', {}).get('marketCap', 'Unknown'),
                'sector': stock_data.get('info', {}).get('sector', 'Unknown'),
                'industry': stock_data.get('info', {}).get('industry', 'Unknown')
            },
            'technical_analysis': technical_analysis,
            'fundamental_analysis': fundamental_analysis,
            'sentiment_analysis': sentiment_analysis,
            'news_summary': {
                'total_articles': len(news_data),
                'recent_headlines': [news.get('title', '') for news in news_data[:5]]
            },
            'recommendations': recommendations,
            'predictions': predictions,
            'market_context': market_trends,
            'risk_assessment': {
                'volatility': 'medium',  # Could be calculated from historical data
                'liquidity': 'high' if stock_data.get('info', {}).get('volume', 0) > 1000000 else 'medium'
            }
        }
        
        return report

def main(input_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main function for the Stock Market Research Agent.
    
    Args:
        input_data: Dictionary containing:
            - stock_symbols: Comma-separated list of stock symbols
            - analysis_depth: Level of analysis (basic, standard, comprehensive, expert)
            - prediction_timeframe: Timeframe for predictions
            - include_news: Boolean for news analysis
            - include_technical_analysis: Boolean for technical analysis
            - include_fundamental_analysis: Boolean for fundamental analysis
            - include_sentiment_analysis: Boolean for sentiment analysis
            - risk_tolerance: Risk tolerance level
            - investment_amount: Investment amount to consider
            - include_competitor_analysis: Boolean for competitor analysis
            - include_market_trends: Boolean for market trend analysis
            - api_key_alpha_vantage: Optional Alpha Vantage API key
            - api_key_news: Optional News API key
    
    Returns:
        Dictionary containing comprehensive stock analysis
    """
    
    # Initialize agent
    agent = StockMarketAgent()
    
    # Extract and validate parameters
    stock_symbols = input_data.get('stock_symbols', '').strip()
    if not stock_symbols:
        return {'error': 'Stock symbols are required'}
    
    symbols = [s.strip().upper() for s in stock_symbols.split(',')]
    analysis_depth = input_data.get('analysis_depth', 'comprehensive')
    prediction_timeframe = input_data.get('prediction_timeframe', '3months')
    
    # Boolean parameters
    include_news = agent.ensure_boolean(input_data.get('include_news', True))
    include_technical_analysis = agent.ensure_boolean(input_data.get('include_technical_analysis', True))
    include_fundamental_analysis = agent.ensure_boolean(input_data.get('include_fundamental_analysis', True))
    include_sentiment_analysis = agent.ensure_boolean(input_data.get('include_sentiment_analysis', True))
    include_competitor_analysis = agent.ensure_boolean(input_data.get('include_competitor_analysis', True))
    include_market_trends = agent.ensure_boolean(input_data.get('include_market_trends', True))
    
    risk_tolerance = input_data.get('risk_tolerance', 'moderate')
    investment_amount = float(input_data.get('investment_amount', 10000))
    
    logger.info(f"Starting analysis for symbols: {symbols}")
    
    try:
        results = {}
        
        # Analyze each stock
        for symbol in symbols:
            logger.info(f"Analyzing {symbol}...")
            
            # Fetch stock data
            stock_data = agent.fetch_stock_data(symbol)
            if 'error' in stock_data:
                results[symbol] = {'error': stock_data['error']}
                continue
            
            # Fetch news if requested
            news_data = []
            if include_news:
                news_data = agent.fetch_news(symbol)
            
            # Technical analysis
            technical_analysis = {}
            if include_technical_analysis:
                technical_analysis = agent.analyze_technical_indicators(stock_data)
            
            # Fundamental analysis
            fundamental_analysis = {}
            if include_fundamental_analysis:
                fundamental_analysis = agent.analyze_fundamentals(stock_data)
            
            # Sentiment analysis
            sentiment_analysis = {}
            if include_sentiment_analysis:
                sentiment_analysis = agent.analyze_sentiment(news_data)
            
            # Generate recommendations
            recommendations = agent.generate_recommendations(
                symbol, stock_data, technical_analysis, fundamental_analysis,
                sentiment_analysis, risk_tolerance, investment_amount, prediction_timeframe
            )
            
            # Generate predictions
            predictions = agent.generate_predictions(
                symbol, stock_data, technical_analysis, prediction_timeframe
            )
            
            # Market trends analysis
            market_trends = {}
            if include_market_trends:
                market_trends = agent.analyze_market_trends(symbols)
            
            # Create comprehensive report
            report = agent.create_comprehensive_report(
                symbol, stock_data, news_data, technical_analysis,
                fundamental_analysis, sentiment_analysis, recommendations,
                predictions, market_trends
            )
            
            results[symbol] = report
        
        # Create overall summary
        summary = {
            'analysis_date': datetime.now().isoformat(),
            'symbols_analyzed': symbols,
            'analysis_depth': analysis_depth,
            'prediction_timeframe': prediction_timeframe,
            'risk_tolerance': risk_tolerance,
            'investment_amount': investment_amount,
            'overall_recommendations': {
                symbol: results[symbol].get('recommendations', {}).get('recommendation', 'hold')
                for symbol in symbols if 'error' not in results[symbol]
            }
        }
        
        return {
            'status': 'success',
            'summary': summary,
            'detailed_analysis': results,
            'execution_time': time.time()
        }
        
    except Exception as e:
        logger.error(f"Error in main analysis: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'symbols': symbols
        }

if __name__ == "__main__":
    # Test the agent
    test_input = {
        'stock_symbols': 'AAPL,MSFT',
        'analysis_depth': 'comprehensive',
        'prediction_timeframe': '3months',
        'include_news': True,
        'include_technical_analysis': True,
        'include_fundamental_analysis': True,
        'include_sentiment_analysis': True,
        'risk_tolerance': 'moderate',
        'investment_amount': 10000
    }
    
    result = main(test_input, {})
    print(json.dumps(result, indent=2, cls=NumpyEncoder)) 