# SEC EDGAR Data Extraction Agent

A comprehensive agent that extracts financial data, filings, and reports from the SEC EDGAR database using official SEC APIs. This agent provides access to real-time financial data, XBRL filings, and comprehensive financial analysis capabilities.

## Features

### 🔍 **Data Extraction**
- **Company Information**: Fetch basic company details, filing history, and metadata
- **Financial Statements**: Extract XBRL data from 10-K, 10-Q, 8-K, and other filings
- **XBRL Concepts**: Access specific financial metrics and historical trends
- **Filing History**: Track all SEC filings with dates, forms, and accession numbers

### 📊 **Financial Analysis**
- **Key Metrics**: Total assets, liabilities, revenue, net income, cash flow
- **Financial Ratios**: Debt-to-equity, profit margins, ROE, ROA, book value per share
- **Trend Analysis**: Historical performance tracking and trend identification
- **Risk Assessment**: Automated financial risk evaluation and scoring

### 🤖 **AI-Powered Insights**
- **Financial Health Analysis**: AI-generated insights on company financial stability
- **Investment Recommendations**: Data-driven investment ratings and suggestions
- **Risk Factors**: Identification of potential financial risks and concerns
- **Industry Positioning**: Comparative analysis within industry context

### 🔄 **Comparison Tools**
- **Multi-Company Analysis**: Compare financial metrics across multiple companies
- **Industry Benchmarks**: Frame data for industry-wide comparisons
- **Peer Analysis**: Side-by-side financial performance evaluation

## Supported Operations

### 1. **Company Information** (`company_info`)
Fetch basic company details and filing history.

```json
{
  "operation": "company_info",
  "cik": "0000320193"
}
```

### 2. **Financial Analysis** (`financial_analysis`)
Analyze key financial metrics and calculate ratios.

```json
{
  "operation": "financial_analysis",
  "cik": "0000789019"
}
```

### 3. **Company Facts** (`company_facts`)
Get all XBRL facts for a company.

```json
{
  "operation": "company_facts",
  "cik": "0000320193"
}
```

### 4. **Company Concept** (`company_concept`)
Get specific XBRL concept data.

```json
{
  "operation": "company_concept",
  "cik": "0000320193",
  "concept": "Assets",
  "taxonomy": "us-gaap"
}
```

### 5. **Frame Data** (`frame_data`)
Compare companies across a specific concept and period.

```json
{
  "operation": "frame_data",
  "concept": "NetIncomeLoss",
  "unit": "USD",
  "period": "CY2023"
}
```

### 6. **Search Companies** (`search_companies`)
Search for companies by ticker or name.

```json
{
  "operation": "search_companies",
  "query": "AAPL"
}
```

### 7. **Compare Companies** (`compare_companies`)
Compare multiple companies on a specific metric.

```json
{
  "operation": "compare_companies",
  "ciks": ["0000320193", "0000789019", "0001652044"],
  "concept": "NetIncomeLoss"
}
```

### 8. **Generate Report** (`generate_report`)
Create comprehensive financial reports with AI insights.

```json
{
  "operation": "generate_report",
  "cik": "0000320193",
  "report_type": "comprehensive",
  "include_ai_insights": true
}
```

## Common CIK Numbers

| Company | Ticker | CIK |
|---------|--------|-----|
| Apple Inc. | AAPL | 0000320193 |
| Microsoft Corporation | MSFT | 0000789019 |
| Alphabet Inc. | GOOGL | 0001652044 |
| Amazon.com Inc. | AMZN | 0001018724 |
| Tesla Inc. | TSLA | 0001318605 |
| Meta Platforms Inc. | META | 0001326801 |
| NVIDIA Corporation | NVDA | 0001045810 |
| Netflix Inc. | NFLX | 0001065280 |
| Intel Corporation | INTC | 0000050863 |
| Advanced Micro Devices Inc. | AMD | 0000002488 |

## Key XBRL Concepts

### Financial Statement Concepts
- `Assets` - Total Assets
- `Liabilities` - Total Liabilities
- `StockholdersEquity` - Stockholders Equity
- `Revenues` - Total Revenue
- `NetIncomeLoss` - Net Income/Loss
- `CashAndCashEquivalentsAtCarryingValue` - Cash and Cash Equivalents
- `LongTermDebt` - Long Term Debt

### Earnings Concepts
- `EarningsPerShareBasic` - Basic EPS
- `EarningsPerShareDiluted` - Diluted EPS
- `CommonStockSharesOutstanding` - Shares Outstanding

### Cash Flow Concepts
- `NetCashProvidedByUsedInOperatingActivities` - Operating Cash Flow
- `NetCashProvidedByUsedInInvestingActivities` - Investing Cash Flow
- `NetCashProvidedByUsedInFinancingActivities` - Financing Cash Flow

## Financial Ratios Calculated

### Liquidity Ratios
- **Current Ratio**: Current Assets / Current Liabilities
- **Quick Ratio**: (Current Assets - Inventory) / Current Liabilities

### Solvency Ratios
- **Debt-to-Equity**: Total Liabilities / Stockholders Equity
- **Debt-to-Assets**: Total Liabilities / Total Assets
- **Equity Ratio**: Stockholders Equity / Total Assets

### Profitability Ratios
- **Profit Margin**: Net Income / Total Revenue
- **Return on Assets (ROA)**: Net Income / Total Assets
- **Return on Equity (ROE)**: Net Income / Stockholders Equity

### Per-Share Metrics
- **Book Value Per Share**: Stockholders Equity / Shares Outstanding
- **Earnings Per Share**: Net Income / Shares Outstanding

## API Rate Limiting

The SEC API has rate limiting requirements:
- **Request Delay**: 100ms between requests (automatically handled)
- **Processing Delay**: Data may be delayed by up to 1 minute after filing
- **Real-time Updates**: Submissions API updates in less than 1 second
- **XBRL Updates**: XBRL APIs update within 1 minute

## Error Handling

The agent handles various error scenarios:
- **404 Errors**: Data not found for the specified CIK or concept
- **429 Errors**: Rate limiting - automatic retry with longer delays
- **Network Errors**: Connection timeouts and retry logic
- **JSON Errors**: Invalid response parsing with fallback handling

## Setup and Installation

### Prerequisites
- Python 3.8+
- OpenAI API key (for AI insights)

### Installation
```bash
pip install -r requirements.txt
```

### Environment Variables
Create a `.env` file:
```env
OPENAI_API_KEY=your_openai_api_key_here
```

## Usage Examples

### Basic Company Information
```python
from sec_edgar_agent import main

result = main({
    "operation": "company_info",
    "cik": "0000320193"
}, {})
```

### Financial Analysis
```python
result = main({
    "operation": "financial_analysis",
    "cik": "0000789019"
}, {})
```

### Company Comparison
```python
result = main({
    "operation": "compare_companies",
    "ciks": ["0000320193", "0000789019", "0001652044"],
    "concept": "NetIncomeLoss"
}, {})
```

### Comprehensive Report
```python
result = main({
    "operation": "generate_report",
    "cik": "0000320193",
    "report_type": "comprehensive",
    "include_ai_insights": true
}, {})
```

## Output Format

### Company Information Response
```json
{
  "cik": "0000320193",
  "name": "Apple Inc.",
  "tickers": ["AAPL"],
  "exchanges": ["Nasdaq"],
  "sic": "3571",
  "sicDescription": "ELECTRONIC COMPUTERS",
  "filing_count": 150,
  "recent_filings": [
    {
      "form": "10-K",
      "filing_date": "2023-10-27",
      "accession_number": "0000320193-23-000077",
      "primary_document": "aapl-20230930.htm"
    }
  ]
}
```

### Financial Analysis Response
```json
{
  "cik": "0000320193",
  "company_name": "Apple Inc.",
  "key_metrics": {
    "total_assets": 352755000000,
    "total_revenue": 394328000000,
    "net_income": 96995000000
  },
  "financial_ratios": {
    "debt_to_equity": 1.45,
    "profit_margin": 0.246,
    "return_on_equity": 0.147
  },
  "risk_assessment": {
    "overall_risk": "low",
    "risk_score": 25
  }
}
```

## Limitations

1. **CIK Requirement**: Most operations require valid CIK numbers
2. **Rate Limiting**: SEC API enforces rate limits
3. **Data Delays**: Some data may be delayed by up to 1 minute
4. **AI Dependencies**: AI insights require OpenAI API key
5. **Public Data Only**: Limited to publicly available SEC data

## SEC API Documentation

For more information about the SEC EDGAR APIs:
- [SEC EDGAR APIs Documentation](https://www.sec.gov/edgar/sec-api-documentation)
- [XBRL Data APIs](https://www.sec.gov/edgar/xbrl/xbrl-variables)
- [Developer FAQs](https://www.sec.gov/developer-faq)

## Support

For technical support or questions about the SEC EDGAR agent:
- Check the SEC API documentation for data availability
- Verify CIK numbers are correct and up-to-date
- Ensure proper rate limiting compliance
- Contact support for agent-specific issues

## License

This agent is provided as-is for educational and research purposes. Please comply with SEC's Privacy and Security Policy when using the data. 