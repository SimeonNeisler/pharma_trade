# FDA-Linked Options Trading Dashboard

A Streamlit-based dashboard for monitoring options trades linked to FDA/EMA decisions and clinical trials.

## Features

- **Active Positions Panel**: Real-time P&L tracking with implied volatility and break-even charts
- **Upcoming Opportunities**: FDA/EMA decisions and clinical trial completion dates
- **Trade History**: Complete trade journal with filtering and CSV export
- **Event Management**: Manual event linking and data management

## Installation

1. Install dependencies:
```bash
cd src/frontend
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Ensure PostgreSQL database is running with the required tables:
   - `trades`
   - `clinical_trials` 
   - `regulatory_decisions`
   - `companies`

## Usage

Run the dashboard:
```bash
streamlit run dashboard.py
```

The dashboard will be available at http://localhost:8501

## Configuration

The dashboard uses your existing database configuration from `src/config/config.py`. Ensure your database connection is properly configured.

## Architecture

- **Frontend**: Streamlit with Plotly for interactive charts
- **Database**: PostgreSQL with existing schema
- **Real-time Data**: yfinance for stock prices (can be enhanced with Polygon/Tradier)
- **Caching**: Streamlit's built-in caching for performance

## Extending the Dashboard

To add real-time market data:
1. Integrate with Polygon or Tradier APIs for options data
2. Replace mock IV calculations with real implied volatility
3. Add WebSocket connections for live price feeds

To add notifications:
1. Implement Celery background jobs
2. Configure Twilio/SendGrid credentials
3. Set up alert thresholds and triggers