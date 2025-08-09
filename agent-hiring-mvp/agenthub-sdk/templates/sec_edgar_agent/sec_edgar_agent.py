#!/usr/bin/env python3
"""
SEC EDGAR Data Extraction Agent

A comprehensive agent that extracts financial data, filings, and reports from the SEC EDGAR database
using the official SEC APIs. This agent can fetch company information, financial statements,
XBRL data, and filing history for comprehensive financial analysis.
"""

import json
import os
import sys
import time
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np
import requests
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

class SECEdgarAgent:
    """Comprehensive SEC EDGAR data extraction and analysis agent."""
    
    def __init__(self, openai_api_key: Optional[str] = None):
        """Initialize the SEC EDGAR agent."""
        self.openai_client = OpenAI(api_key=openai_api_key or os.getenv('OPENAI_API_KEY'))
        self.session = requests.Session()
        
        # SEC API base URLs
        self.sec_base_url = "https://data.sec.gov"
        self.submissions_url = f"{self.sec_base_url}/submissions"
        self.xbrl_url = f"{self.sec_base_url}/api/xbrl"
        
        # Set headers for SEC API compliance
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0'
        })
        
        # Rate limiting - SEC recommends reasonable delays
        self.request_delay = 0.1  # 100ms between requests
        
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
    
    def _format_cik(self, cik: str) -> str:
        """Format CIK to 10-digit format with leading zeros."""
        # Remove any non-digit characters
        cik_clean = re.sub(r'\D', '', str(cik))
        # Pad with leading zeros to 10 digits
        return cik_clean.zfill(10)
    
    def _make_sec_request(self, url: str) -> Dict[str, Any]:
        """Make a request to SEC API with proper error handling and rate limiting."""
        try:
            time.sleep(self.request_delay)  # Rate limiting
            response = self.session.get(url, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                logger.warning(f"Data not found for URL: {url}")
                return {'error': 'Data not found'}
            elif response.status_code == 429:
                logger.warning(f"Rate limited by SEC API: {url}")
                time.sleep(1)  # Wait longer for rate limiting
                return {'error': 'Rate limited'}
            else:
                logger.error(f"SEC API error {response.status_code}: {url}")
                return {'error': f'API error {response.status_code}'}
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {url}: {e}")
            return {'error': str(e)}
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error for {url}: {e}")
            return {'error': 'Invalid JSON response'}
    
    def get_company_info(self, cik: str) -> Dict[str, Any]:
        """Get company information and filing history from SEC submissions API."""
        try:
            formatted_cik = self._format_cik(cik)
            url = f"{self.submissions_url}/CIK{formatted_cik}.json"
            
            logger.info(f"Fetching company info for CIK: {formatted_cik}")
            data = self._make_sec_request(url)
            
            if 'error' in data:
                return data
            
            # Extract key information
            company_info = {
                'cik': formatted_cik,
                'name': data.get('name', 'Unknown'),
                'tickers': data.get('tickers', []),
                'exchanges': data.get('exchanges', []),
                'sic': data.get('sic', ''),
                'sicDescription': data.get('sicDescription', ''),
                'category': data.get('category', ''),
                'former_names': data.get('formerNames', []),
                'filing_count': len(data.get('filings', {}).get('recent', {}).get('form', [])),
                'latest_filing_date': data.get('filings', {}).get('recent', {}).get('filingDate', [])[0] if data.get('filings', {}).get('recent', {}).get('filingDate') else None,
                'latest_form': data.get('filings', {}).get('recent', {}).get('form', [])[0] if data.get('filings', {}).get('recent', {}).get('form') else None
            }
            
            # Get recent filings (last 20)
            recent_filings = []
            filings_data = data.get('filings', {}).get('recent', {})
            
            if filings_data:
                forms = filings_data.get('form', [])
                filing_dates = filings_data.get('filingDate', [])
                accession_numbers = filings_data.get('accessionNumber', [])
                primary_documents = filings_data.get('primaryDocument', [])
                
                for i in range(min(20, len(forms))):
                    recent_filings.append({
                        'form': forms[i] if i < len(forms) else '',
                        'filing_date': filing_dates[i] if i < len(filing_dates) else '',
                        'accession_number': accession_numbers[i] if i < len(accession_numbers) else '',
                        'primary_document': primary_documents[i] if i < len(primary_documents) else ''
                    })
            
            company_info['recent_filings'] = recent_filings
            return company_info
            
        except Exception as e:
            logger.error(f"Error fetching company info for CIK {cik}: {e}")
            return {'error': str(e)}
    
    def get_company_facts(self, cik: str) -> Dict[str, Any]:
        """Get all XBRL company facts for a company."""
        try:
            formatted_cik = self._format_cik(cik)
            url = f"{self.xbrl_url}/companyfacts/CIK{formatted_cik}.json"
            
            logger.info(f"Fetching company facts for CIK: {formatted_cik}")
            data = self._make_sec_request(url)
            
            if 'error' in data:
                return data
            
            # Extract key financial metrics
            facts = data.get('facts', {})
            
            # Common financial concepts to extract
            key_concepts = {
                'us-gaap': {
                    'Assets': 'Total Assets',
                    'Liabilities': 'Total Liabilities',
                    'StockholdersEquity': 'Stockholders Equity',
                    'Revenues': 'Total Revenue',
                    'NetIncomeLoss': 'Net Income',
                    'CashAndCashEquivalentsAtCarryingValue': 'Cash and Cash Equivalents',
                    'LongTermDebt': 'Long Term Debt',
                    'EarningsPerShareBasic': 'EPS Basic',
                    'EarningsPerShareDiluted': 'EPS Diluted',
                    'CommonStockSharesOutstanding': 'Shares Outstanding'
                }
            }
            
            extracted_facts = {}
            
            for taxonomy, concepts in key_concepts.items():
                if taxonomy in facts:
                    taxonomy_facts = facts[taxonomy]
                    for concept_key, concept_name in concepts.items():
                        if concept_key in taxonomy_facts:
                            concept_data = taxonomy_facts[concept_key]
                            units = concept_data.get('units', {})
                            
                            # Get the most recent values for each unit
                            for unit, values in units.items():
                                if values and len(values) > 0:
                                    # Sort by end date and get the most recent
                                    sorted_values = sorted(values, key=lambda x: x.get('end', ''), reverse=True)
                                    latest_value = sorted_values[0]
                                    
                                    extracted_facts[f"{concept_name}_{unit}"] = {
                                        'value': latest_value.get('val'),
                                        'end_date': latest_value.get('end'),
                                        'start_date': latest_value.get('start'),
                                        'form': latest_value.get('form'),
                                        'filed': latest_value.get('filed'),
                                        'unit': unit
                                    }
            
            return {
                'cik': formatted_cik,
                'company_name': data.get('entityName', 'Unknown'),
                'facts_count': len(facts),
                'extracted_facts': extracted_facts,
                'available_taxonomies': list(facts.keys())
            }
            
        except Exception as e:
            logger.error(f"Error fetching company facts for CIK {cik}: {e}")
            return {'error': str(e)}
    
    def get_company_concept(self, cik: str, taxonomy: str, concept: str) -> Dict[str, Any]:
        """Get specific XBRL concept data for a company."""
        try:
            formatted_cik = self._format_cik(cik)
            url = f"{self.xbrl_url}/companyconcept/CIK{formatted_cik}/{taxonomy}/{concept}.json"
            
            logger.info(f"Fetching concept {concept} for CIK: {formatted_cik}")
            data = self._make_sec_request(url)
            
            if 'error' in data:
                return data
            
            # Process the concept data
            concept_data = {
                'cik': formatted_cik,
                'taxonomy': taxonomy,
                'concept': concept,
                'company_name': data.get('entityName', 'Unknown'),
                'units': {}
            }
            
            units = data.get('units', {})
            for unit, values in units.items():
                # Sort by end date (most recent first)
                sorted_values = sorted(values, key=lambda x: x.get('end', ''), reverse=True)
                concept_data['units'][unit] = sorted_values[:10]  # Get last 10 values
            
            return concept_data
            
        except Exception as e:
            logger.error(f"Error fetching concept {concept} for CIK {cik}: {e}")
            return {'error': str(e)}
    
    def get_frame_data(self, taxonomy: str, concept: str, unit: str, period: str) -> Dict[str, Any]:
        """Get XBRL frame data for comparing companies across a specific concept and period."""
        try:
            url = f"{self.xbrl_url}/frames/{taxonomy}/{concept}/{unit}/{period}.json"
            
            logger.info(f"Fetching frame data for {concept} - {period}")
            data = self._make_sec_request(url)
            
            if 'error' in data:
                return data
            
            # Process frame data
            frame_data = {
                'taxonomy': taxonomy,
                'concept': concept,
                'unit': unit,
                'period': period,
                'companies_count': len(data.get('data', [])),
                'companies': []
            }
            
            companies = data.get('data', [])
            for company in companies[:50]:  # Limit to top 50 companies
                frame_data['companies'].append({
                    'cik': company.get('cik'),
                    'entity_name': company.get('entityName'),
                    'value': company.get('val'),
                    'end_date': company.get('end'),
                    'start_date': company.get('start'),
                    'form': company.get('form'),
                    'filed': company.get('filed')
                })
            
            return frame_data
            
        except Exception as e:
            logger.error(f"Error fetching frame data for {concept} - {period}: {e}")
            return {'error': str(e)}
    
    def search_companies(self, query: str) -> Dict[str, Any]:
        """Search for companies by name or ticker symbol."""
        try:
            # This would require a company lookup API or database
            # For now, we'll provide a basic implementation
            # In a real implementation, you might use a company database or SEC company list
            
            logger.info(f"Searching for companies matching: {query}")
            
            # Common company mappings (this could be expanded with a proper database)
            company_mappings = {
                'AAPL': '0000320193',  # Apple Inc.
                'MSFT': '0000789019',  # Microsoft Corporation
                'GOOGL': '0001652044', # Alphabet Inc.
                'AMZN': '0001018724',  # Amazon.com Inc.
                'TSLA': '0001318605',  # Tesla Inc.
                'META': '0001326801',  # Meta Platforms Inc.
                'NVDA': '0001045810',  # NVIDIA Corporation
                'NFLX': '0001065280',  # Netflix Inc.
                'INTC': '0000050863',  # Intel Corporation
                'AMD': '0000002488',   # Advanced Micro Devices Inc.
            }
            
            query_upper = query.upper()
            results = []
            
            # Check for exact ticker matches
            if query_upper in company_mappings:
                cik = company_mappings[query_upper]
                company_info = self.get_company_info(cik)
                if 'error' not in company_info:
                    results.append({
                        'ticker': query_upper,
                        'cik': cik,
                        'name': company_info.get('name', 'Unknown'),
                        'confidence': 'exact_match'
                    })
            
            # Check for partial matches in tickers
            for ticker, cik in company_mappings.items():
                if query_upper in ticker:
                    company_info = self.get_company_info(cik)
                    if 'error' not in company_info:
                        results.append({
                            'ticker': ticker,
                            'cik': cik,
                            'name': company_info.get('name', 'Unknown'),
                            'confidence': 'partial_match'
                        })
            
            return {
                'query': query,
                'results_count': len(results),
                'results': results
            }
            
        except Exception as e:
            logger.error(f"Error searching for companies: {e}")
            return {'error': str(e)}
    
    def analyze_financial_metrics(self, cik: str) -> Dict[str, Any]:
        """Analyze key financial metrics for a company."""
        try:
            logger.info(f"Analyzing financial metrics for CIK: {cik}")
            
            # Get company facts
            facts_data = self.get_company_facts(cik)
            if 'error' in facts_data:
                return facts_data
            
            extracted_facts = facts_data.get('extracted_facts', {})
            
            # Calculate key ratios and metrics
            analysis = {
                'cik': cik,
                'company_name': facts_data.get('company_name', 'Unknown'),
                'analysis_date': datetime.now().isoformat(),
                'key_metrics': {},
                'financial_ratios': {},
                'trends': {}
            }
            
            # Extract key metrics
            total_assets = extracted_facts.get('Total Assets_USD', {}).get('value')
            total_liabilities = extracted_facts.get('Total Liabilities_USD', {}).get('value')
            stockholders_equity = extracted_facts.get('Stockholders Equity_USD', {}).get('value')
            total_revenue = extracted_facts.get('Total Revenue_USD', {}).get('value')
            net_income = extracted_facts.get('Net Income_USD', {}).get('value')
            cash_equivalents = extracted_facts.get('Cash and Cash Equivalents_USD', {}).get('value')
            long_term_debt = extracted_facts.get('Long Term Debt_USD', {}).get('value')
            shares_outstanding = extracted_facts.get('Shares Outstanding_shares', {}).get('value')
            
            # Store key metrics
            analysis['key_metrics'] = {
                'total_assets': total_assets,
                'total_liabilities': total_liabilities,
                'stockholders_equity': stockholders_equity,
                'total_revenue': total_revenue,
                'net_income': net_income,
                'cash_and_equivalents': cash_equivalents,
                'long_term_debt': long_term_debt,
                'shares_outstanding': shares_outstanding
            }
            
            # Calculate financial ratios
            if total_assets and total_assets > 0:
                analysis['financial_ratios']['debt_to_assets'] = (total_liabilities or 0) / total_assets
                analysis['financial_ratios']['equity_to_assets'] = (stockholders_equity or 0) / total_assets
            
            if stockholders_equity and stockholders_equity > 0:
                analysis['financial_ratios']['debt_to_equity'] = (total_liabilities or 0) / stockholders_equity
            
            if total_revenue and total_revenue > 0:
                analysis['financial_ratios']['profit_margin'] = (net_income or 0) / total_revenue
            
            if shares_outstanding and shares_outstanding > 0:
                analysis['financial_ratios']['book_value_per_share'] = (stockholders_equity or 0) / shares_outstanding
                if net_income:
                    analysis['financial_ratios']['earnings_per_share'] = net_income / shares_outstanding
            
            if total_assets and total_assets > 0:
                analysis['financial_ratios']['return_on_assets'] = (net_income or 0) / total_assets
            
            if stockholders_equity and stockholders_equity > 0:
                analysis['financial_ratios']['return_on_equity'] = (net_income or 0) / stockholders_equity
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing financial metrics for CIK {cik}: {e}")
            return {'error': str(e)}
    
    def compare_companies(self, ciks: List[str], concept: str = 'NetIncomeLoss') -> Dict[str, Any]:
        """Compare multiple companies on a specific financial concept."""
        try:
            logger.info(f"Comparing companies {ciks} on concept: {concept}")
            
            comparison = {
                'concept': concept,
                'companies': [],
                'comparison_date': datetime.now().isoformat()
            }
            
            for cik in ciks:
                company_data = self.get_company_concept(cik, 'us-gaap', concept)
                if 'error' not in company_data:
                    # Get the most recent value
                    latest_value = None
                    for unit, values in company_data.get('units', {}).items():
                        if values and len(values) > 0:
                            latest_value = values[0]
                            break
                    
                    comparison['companies'].append({
                        'cik': cik,
                        'company_name': company_data.get('company_name', 'Unknown'),
                        'latest_value': latest_value.get('val') if latest_value else None,
                        'latest_date': latest_value.get('end') if latest_value else None,
                        'unit': latest_value.get('unit') if latest_value else None
                    })
            
            # Sort by latest value (descending)
            comparison['companies'].sort(key=lambda x: x['latest_value'] or 0, reverse=True)
            
            return comparison
            
        except Exception as e:
            logger.error(f"Error comparing companies: {e}")
            return {'error': str(e)}
    
    def generate_financial_report(self, cik: str, report_type: str = 'comprehensive') -> Dict[str, Any]:
        """Generate a comprehensive financial report for a company."""
        try:
            logger.info(f"Generating {report_type} financial report for CIK: {cik}")
            
            # Get company information
            company_info = self.get_company_info(cik)
            if 'error' in company_info:
                return company_info
            
            # Get financial analysis
            financial_analysis = self.analyze_financial_metrics(cik)
            if 'error' in financial_analysis:
                return financial_analysis
            
            # Get recent filings
            recent_filings = company_info.get('recent_filings', [])
            
            # Generate AI-powered insights
            insights = self._generate_ai_insights(company_info, financial_analysis)
            
            report = {
                'report_type': report_type,
                'generated_date': datetime.now().isoformat(),
                'company_overview': {
                    'name': company_info.get('name'),
                    'cik': cik,
                    'tickers': company_info.get('tickers'),
                    'exchanges': company_info.get('exchanges'),
                    'industry': company_info.get('sicDescription'),
                    'filing_count': company_info.get('filing_count')
                },
                'financial_analysis': financial_analysis,
                'recent_filings': recent_filings[:10],  # Last 10 filings
                'ai_insights': insights,
                'risk_assessment': self._assess_financial_risk(financial_analysis),
                'recommendations': self._generate_recommendations(financial_analysis)
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating financial report for CIK {cik}: {e}")
            return {'error': str(e)}
    
    def _generate_ai_insights(self, company_info: Dict[str, Any], financial_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate AI-powered insights about the company's financial health."""
        try:
            if not self.openai_client:
                return {'insights': 'AI insights not available - OpenAI API key required'}
            
            # Prepare context for AI analysis
            context = f"""
            Company: {company_info.get('name', 'Unknown')}
            Industry: {company_info.get('sicDescription', 'Unknown')}
            
            Key Financial Metrics:
            - Total Assets: ${financial_analysis.get('key_metrics', {}).get('total_assets', 'N/A'):,.0f}
            - Total Revenue: ${financial_analysis.get('key_metrics', {}).get('total_revenue', 'N/A'):,.0f}
            - Net Income: ${financial_analysis.get('key_metrics', {}).get('net_income', 'N/A'):,.0f}
            - Debt to Equity: {financial_analysis.get('financial_ratios', {}).get('debt_to_equity', 'N/A'):.2f}
            - Return on Equity: {financial_analysis.get('financial_ratios', {}).get('return_on_equity', 'N/A'):.2%}
            """
            
            prompt = f"""
            Based on the following financial data for {company_info.get('name', 'Unknown')}, provide a brief analysis of:
            1. Financial health and stability
            2. Key strengths and potential concerns
            3. Industry positioning
            4. Overall assessment
            
            {context}
            
            Please provide a concise, professional analysis suitable for investors.
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.3
            )
            
            return {
                'analysis': response.choices[0].message.content,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating AI insights: {e}")
            return {'insights': f'Error generating insights: {str(e)}'}
    
    def _assess_financial_risk(self, financial_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Assess financial risk based on key ratios and metrics."""
        try:
            ratios = financial_analysis.get('financial_ratios', {})
            
            risk_assessment = {
                'overall_risk': 'medium',
                'risk_factors': [],
                'risk_score': 50  # 0-100 scale
            }
            
            # Debt analysis
            debt_to_equity = ratios.get('debt_to_equity', 0)
            if debt_to_equity > 2.0:
                risk_assessment['risk_factors'].append('High debt-to-equity ratio')
                risk_assessment['risk_score'] += 20
            elif debt_to_equity > 1.0:
                risk_assessment['risk_factors'].append('Moderate debt levels')
                risk_assessment['risk_score'] += 10
            
            # Profitability analysis
            profit_margin = ratios.get('profit_margin', 0)
            if profit_margin < 0.05:
                risk_assessment['risk_factors'].append('Low profit margins')
                risk_assessment['risk_score'] += 15
            elif profit_margin < 0.10:
                risk_assessment['risk_factors'].append('Moderate profit margins')
                risk_assessment['risk_score'] += 5
            
            # Return on equity analysis
            roe = ratios.get('return_on_equity', 0)
            if roe < 0.10:
                risk_assessment['risk_factors'].append('Low return on equity')
                risk_assessment['risk_score'] += 10
            
            # Determine overall risk level
            if risk_assessment['risk_score'] >= 70:
                risk_assessment['overall_risk'] = 'high'
            elif risk_assessment['risk_score'] >= 40:
                risk_assessment['overall_risk'] = 'medium'
            else:
                risk_assessment['overall_risk'] = 'low'
            
            return risk_assessment
            
        except Exception as e:
            logger.error(f"Error assessing financial risk: {e}")
            return {'overall_risk': 'unknown', 'error': str(e)}
    
    def _generate_recommendations(self, financial_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate investment recommendations based on financial analysis."""
        try:
            ratios = financial_analysis.get('financial_ratios', {})
            
            recommendations = {
                'investment_rating': 'hold',
                'recommendations': [],
                'key_considerations': []
            }
            
            # Analyze key metrics for recommendations
            debt_to_equity = ratios.get('debt_to_equity', 0)
            profit_margin = ratios.get('profit_margin', 0)
            roe = ratios.get('return_on_equity', 0)
            
            # Generate recommendations based on metrics
            if debt_to_equity < 0.5 and profit_margin > 0.15 and roe > 0.15:
                recommendations['investment_rating'] = 'strong_buy'
                recommendations['recommendations'].append('Strong financial position with low debt and high profitability')
            elif debt_to_equity < 1.0 and profit_margin > 0.10 and roe > 0.10:
                recommendations['investment_rating'] = 'buy'
                recommendations['recommendations'].append('Good financial fundamentals with reasonable debt levels')
            elif debt_to_equity > 2.0 or profit_margin < 0.05:
                recommendations['investment_rating'] = 'sell'
                recommendations['recommendations'].append('Concerning financial metrics - high debt or low profitability')
            else:
                recommendations['investment_rating'] = 'hold'
                recommendations['recommendations'].append('Mixed financial indicators - monitor for improvements')
            
            # Add key considerations
            if debt_to_equity > 1.0:
                recommendations['key_considerations'].append('Monitor debt levels')
            if profit_margin < 0.10:
                recommendations['key_considerations'].append('Focus on profitability improvement')
            if roe < 0.10:
                recommendations['key_considerations'].append('Evaluate capital efficiency')
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return {'investment_rating': 'unknown', 'error': str(e)}

def main(input_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main function for the SEC EDGAR Data Extraction Agent.
    
    Args:
        input_data: Dictionary containing:
            - operation: Type of operation ('company_info', 'financial_analysis', 'compare_companies', 'search_companies', 'generate_report')
            - cik: Company CIK number (for single company operations)
            - ciks: List of CIK numbers (for comparison operations)
            - query: Search query (for search operations)
            - concept: XBRL concept to analyze (optional)
            - taxonomy: XBRL taxonomy (default: 'us-gaap')
            - report_type: Type of report to generate (default: 'comprehensive')
            - include_ai_insights: Boolean for AI-powered insights (default: True)
    
    Returns:
        Dictionary containing SEC EDGAR data and analysis
    """
    
    # Initialize agent
    agent = SECEdgarAgent()
    
    # Extract and validate parameters
    operation = input_data.get('operation', '').strip()
    if not operation:
        return {'error': 'Operation is required'}
    
    # Boolean parameters
    include_ai_insights = agent.ensure_boolean(input_data.get('include_ai_insights', True))
    
    logger.info(f"Starting SEC EDGAR operation: {operation}")
    
    try:
        if operation == 'company_info':
            cik = input_data.get('cik', '').strip()
            if not cik:
                return {'error': 'CIK is required for company_info operation'}
            return agent.get_company_info(cik)
            
        elif operation == 'financial_analysis':
            cik = input_data.get('cik', '').strip()
            if not cik:
                return {'error': 'CIK is required for financial_analysis operation'}
            return agent.analyze_financial_metrics(cik)
            
        elif operation == 'company_facts':
            cik = input_data.get('cik', '').strip()
            if not cik:
                return {'error': 'CIK is required for company_facts operation'}
            return agent.get_company_facts(cik)
            
        elif operation == 'company_concept':
            cik = input_data.get('cik', '').strip()
            concept = input_data.get('concept', 'NetIncomeLoss').strip()
            taxonomy = input_data.get('taxonomy', 'us-gaap').strip()
            if not cik:
                return {'error': 'CIK is required for company_concept operation'}
            return agent.get_company_concept(cik, taxonomy, concept)
            
        elif operation == 'frame_data':
            concept = input_data.get('concept', 'NetIncomeLoss').strip()
            unit = input_data.get('unit', 'USD').strip()
            period = input_data.get('period', 'CY2023').strip()
            taxonomy = input_data.get('taxonomy', 'us-gaap').strip()
            return agent.get_frame_data(taxonomy, concept, unit, period)
            
        elif operation == 'search_companies':
            query = input_data.get('query', '').strip()
            if not query:
                return {'error': 'Query is required for search_companies operation'}
            return agent.search_companies(query)
            
        elif operation == 'compare_companies':
            ciks = input_data.get('ciks', [])
            concept = input_data.get('concept', 'NetIncomeLoss').strip()
            if not ciks or not isinstance(ciks, list):
                return {'error': 'List of CIKs is required for compare_companies operation'}
            return agent.compare_companies(ciks, concept)
            
        elif operation == 'generate_report':
            cik = input_data.get('cik', '').strip()
            report_type = input_data.get('report_type', 'comprehensive').strip()
            if not cik:
                return {'error': 'CIK is required for generate_report operation'}
            return agent.generate_financial_report(cik, report_type)
            
        else:
            return {'error': f'Unknown operation: {operation}'}
        
    except Exception as e:
        logger.error(f"Error in main SEC EDGAR operation: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'operation': operation
        }

if __name__ == "__main__":
    # Test the agent
    test_input = {
        'operation': 'generate_report',
        'cik': '0000320193'  # Apple Inc.
    }
    
    result = main(test_input, {})
    print(json.dumps(result, indent=2, cls=NumpyEncoder)) 