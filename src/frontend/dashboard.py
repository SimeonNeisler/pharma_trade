import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import psycopg as ppg
import yfinance as yf
import numpy as np
from typing import List, Dict, Optional
import time
#import sys
#import os

# Add parent directory to path to import config
#sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import dbConfig, alpacaConfig
from alpaca.trading.client import TradingClient
from alpaca.data.live import StockDataStream
from alpaca.data.requests import StockLatestQuoteRequest
from alpaca.data.historical import StockHistoricalDataClient

# Page configuration
st.set_page_config(
    page_title="FDA-Linked Options Trading Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

class AlpacaDataManager:
    def __init__(self):
        """Initialize Alpaca clients for trading and market data"""
        self.trading_client = TradingClient(
            alpacaConfig.ALPACA_API_KEY,
            alpacaConfig.ALPACA_SECRET_KEY,
            paper=True
        )
        self.data_client = StockHistoricalDataClient(
            alpacaConfig.ALPACA_API_KEY,
            alpacaConfig.ALPACA_SECRET_KEY
        )
    
    def get_account_positions(self):
        """Get all current positions from Alpaca account"""
        try:
            positions = self.trading_client.get_all_positions()
            return positions
        except Exception as e:
            st.error(f"Error fetching positions from Alpaca: {e}")
            return []
    
    def get_current_quote(self, symbol: str):
        """Get current quote for a symbol"""
        try:
            request = StockLatestQuoteRequest(symbol_or_symbols=symbol)
            quotes = self.data_client.get_stock_latest_quote(request)
            return quotes[symbol] if symbol in quotes else None
        except Exception as e:
            st.error(f"Error fetching quote for {symbol}: {e}")
            return None
    
    def calculate_position_pnl(self, position):
        """Calculate P&L for a position using Alpaca data"""
        try:
            return {
                'symbol': position.symbol,
                'qty': float(position.qty),
                'market_value': float(position.market_value) if position.market_value else 0,
                'cost_basis': float(position.cost_basis) if position.cost_basis else 0,
                'unrealized_pl': float(position.unrealized_pl) if position.unrealized_pl else 0,
                'unrealized_plpc': float(position.unrealized_plpc) if position.unrealized_plpc else 0,
                'current_price': float(position.current_price) if position.current_price else 0,
                'avg_entry_price': float(position.avg_entry_price) if position.avg_entry_price else 0
            }
        except Exception as e:
            st.error(f"Error calculating P&L for {position.symbol}: {e}")
            return None
    
    def parse_option_symbol(self, symbol: str):
        """Parse option symbol to extract underlying, expiration, strike, and type"""
        try:
            # Example: AAPL240119C00185000
            # Format: [UNDERLYING][YYMMDD][C/P][STRIKE_PRICE]
            if len(symbol) < 15:
                return None
                
            # Find where the date starts (first digit after letters)
            underlying_end = 0
            for i, char in enumerate(symbol):
                if char.isdigit():
                    underlying_end = i
                    break
            
            underlying = symbol[:underlying_end]
            remainder = symbol[underlying_end:]
            
            # Extract date (YYMMDD)
            exp_date_str = remainder[:6]
            exp_year = 2000 + int(exp_date_str[:2])
            exp_month = int(exp_date_str[2:4])
            exp_day = int(exp_date_str[4:6])
            exp_date = datetime(exp_year, exp_month, exp_day).date()
            
            # Extract option type (C/P)
            option_type = remainder[6]
            
            # Extract strike price
            strike_str = remainder[7:]
            strike = float(strike_str) / 1000  # Strike is in millidollars
            
            return {
                'underlying': underlying,
                'expiration': exp_date,
                'option_type': 'CALL' if option_type == 'C' else 'PUT',
                'strike': strike,
                'days_to_expiration': (exp_date - datetime.now().date()).days
            }
        except Exception as e:
            st.error(f"Error parsing option symbol {symbol}: {e}")
            return None

class DatabaseManager:
    def __init__(self):
        self.conn = ppg.connect(
            dbname=dbConfig.DB_NAME,
            user=dbConfig.DB_USER,
            host=dbConfig.DB_HOST,
            password=dbConfig.DB_PASSWORD
        )
    
    def get_active_positions(self) -> pd.DataFrame:
        """Get all active options positions with linked events"""
        query = """
        SELECT 
            t.symbol,
            t.call_put,
            t.ticker,
            t.expiration,
            t.strike,
            t.cost as entry_price,
            t.quantity,
            COALESCE(ct.title, rd.drug_name) as linked_event,
            COALESCE(ct.pcd, rd.date) as event_date,
            'Clinical Trial' as event_type
        FROM trades t
        LEFT JOIN clinical_trials ct ON t.study_id = ct.nctid
        LEFT JOIN regulatory_decisions rd ON t.regulatory_id = rd.id
        WHERE t.symbol IS NOT NULL
        ORDER BY t.expiration DESC
        """
        
        return pd.read_sql(query, self.conn)
    
    def get_upcoming_opportunities(self) -> pd.DataFrame:
        """Get upcoming FDA/EMA decisions and clinical trials"""
        query = """
        SELECT 
            ticker,
            drug_name as event_name,
            'PDUFA Decision' as event_type,
            date as event_date,
            status,
            decision
        FROM regulatory_decisions 
        WHERE date >= CURRENT_DATE AND status = 'pending'
        
        UNION ALL
        
        SELECT 
            primary_sponsor_ticker as ticker,
            title as event_name,
            'Clinical Trial' as event_type,
            pcd as event_date,
            'pending' as status,
            NULL as decision
        FROM clinical_trials 
        WHERE pcd >= CURRENT_DATE AND traded = FALSE
        
        ORDER BY event_date ASC
        LIMIT 20
        """
        
        return pd.read_sql(query, self.conn)
    
    def get_trade_history(self) -> pd.DataFrame:
        """Get historical trades with performance metrics"""
        query = """
        SELECT 
            t.symbol,
            t.call_put,
            t.ticker,
            t.expiration,
            t.strike,
            t.cost as entry_price,
            t.quantity,
            COALESCE(ct.title, rd.drug_name) as linked_event,
            COALESCE(ct.pcd, rd.date) as event_date,
            CASE 
                WHEN ct.nctid IS NOT NULL THEN 'Clinical Trial'
                ELSE 'PDUFA Decision'
            END as event_type
        FROM trades t
        LEFT JOIN clinical_trials ct ON t.study_id = ct.nctid
        LEFT JOIN regulatory_decisions rd ON t.regulatory_id = rd.id
        ORDER BY t.expiration DESC
        """
        
        return pd.read_sql(query, self.conn)

@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_current_stock_price(ticker: str) -> Optional[float]:
    """Get current stock price using yfinance"""
    try:
        stock = yf.Ticker(ticker)
        return stock.info.get('regularMarketPrice')
    except:
        return None

@st.cache_data(ttl=300)
def get_option_iv(symbol: str) -> Optional[float]:
    """Mock function for implied volatility - replace with real data source"""
    # This would integrate with Polygon/Tradier for real IV data
    return np.random.uniform(0.3, 0.8)  # Mock IV between 30-80%

def calculate_option_pnl(entry_price: float, current_price: float, quantity: int) -> dict:
    """Calculate P&L for options position"""
    pnl = (current_price - entry_price) * quantity * 100  # Options are per 100 shares
    pnl_percent = ((current_price - entry_price) / entry_price) * 100
    
    return {
        'pnl': pnl,
        'pnl_percent': pnl_percent,
        'current_value': current_price * quantity * 100
    }

def create_payoff_diagram(strike: float, premium: float, option_type: str, current_stock_price: float):
    """Create options payoff diagram"""
    stock_prices = np.linspace(strike * 0.7, strike * 1.3, 100)
    
    if option_type.upper() == 'CALL':
        payoffs = np.maximum(stock_prices - strike, 0) - premium
    else:  # PUT
        payoffs = np.maximum(strike - stock_prices, 0) - premium
    
    fig = go.Figure()
    
    # Payoff line
    fig.add_trace(go.Scatter(
        x=stock_prices,
        y=payoffs,
        mode='lines',
        name=f'{option_type} Payoff',
        line=dict(color='blue', width=2)
    ))
    
    # Break-even line
    fig.add_hline(y=0, line_dash="dash", line_color="gray", annotation_text="Break-even")
    
    # Current stock price line
    fig.add_vline(x=current_stock_price, line_dash="dot", line_color="red", 
                  annotation_text=f"Current: ${current_stock_price:.2f}")
    
    # Strike price line
    fig.add_vline(x=strike, line_dash="dot", line_color="green", 
                  annotation_text=f"Strike: ${strike:.2f}")
    
    fig.update_layout(
        title=f'{option_type} Option Payoff Diagram',
        xaxis_title='Stock Price at Expiration',
        yaxis_title='Profit/Loss ($)',
        height=400
    )
    
    return fig

def main():
    st.title("📊 FDA-Linked Options Trading Dashboard")
    
    # Initialize database connection and Alpaca data manager
    db = DatabaseManager()
    alpaca = AlpacaDataManager()
    
    # Sidebar for navigation and filters
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox(
        "Select View",
        ["Active Positions", "Upcoming Opportunities", "Trade History", "Event Management"]
    )
    
    # Auto-refresh toggle
    auto_refresh = st.sidebar.checkbox("Auto-refresh (30s)", value=False)
    if auto_refresh:
        time.sleep(30)
        st.experimental_rerun()
    
    # Manual refresh button
    if st.sidebar.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.experimental_rerun()
    
    # Main content based on selected page
    if page == "Active Positions":
        render_active_positions(db, alpaca)
    elif page == "Upcoming Opportunities":
        render_upcoming_opportunities(db)
    elif page == "Trade History":
        render_trade_history(db)
    elif page == "Event Management":
        render_event_management(db)

def render_active_positions(db: DatabaseManager, alpaca: AlpacaDataManager):
    st.header("🎯 Active Positions")
    
    # Get live positions from Alpaca
    alpaca_positions = alpaca.get_account_positions()
    
    if not alpaca_positions:
        st.info("No active positions found in Alpaca account.")
        return
    
    # Get database positions for linking to events
    db_positions = db.get_active_positions()
    
    st.subheader("💼 Live Account Positions")
    
    # Create a summary metrics row
    total_market_value = sum(float(pos.market_value or 0) for pos in alpaca_positions)
    total_unrealized_pl = sum(float(pos.unrealized_pl or 0) for pos in alpaca_positions)
    total_cost_basis = sum(float(pos.cost_basis or 0) for pos in alpaca_positions)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Market Value", f"${total_market_value:,.2f}")
    with col2:
        st.metric("Total Unrealized P&L", f"${total_unrealized_pl:,.2f}", 
                 f"{(total_unrealized_pl/total_cost_basis)*100:.2f}%" if total_cost_basis != 0 else "0%")
    with col3:
        st.metric("Total Cost Basis", f"${total_cost_basis:,.2f}")
    with col4:
        st.metric("Active Positions", len(alpaca_positions))
    
    # Display each position
    for position in alpaca_positions:
        pnl_data = alpaca.calculate_position_pnl(position)
        if not pnl_data:
            continue
            
        # Check if this is an options position (contains option-like symbol)
        is_option = len(position.symbol) > 6 and any(c.isdigit() for c in position.symbol[-8:])
        
        with st.expander(f"{'📊' if is_option else '📈'} {position.symbol} - {'Option' if is_option else 'Stock'}", expanded=True):
            
            # Position details
            col1, col2, col3 = st.columns(3)
            with col1:
                st.write(f"**Symbol:** {pnl_data['symbol']}")
                st.write(f"**Quantity:** {pnl_data['qty']}")
                st.write(f"**Avg Entry Price:** ${pnl_data['avg_entry_price']:.2f}")
            with col2:
                st.write(f"**Current Price:** ${pnl_data['current_price']:.2f}")
                st.write(f"**Market Value:** ${pnl_data['market_value']:.2f}")
                st.write(f"**Cost Basis:** ${pnl_data['cost_basis']:.2f}")
            with col3:
                color = "green" if pnl_data['unrealized_pl'] >= 0 else "red"
                st.write(f"**Unrealized P&L:** :{color}[${pnl_data['unrealized_pl']:.2f}]")
                st.write(f"**P&L %:** :{color}[{pnl_data['unrealized_plpc']:.2%}]")
            
            # Try to link with database events
            linked_events = db_positions[db_positions['symbol'] == position.symbol]
            if not linked_events.empty:
                st.write("**🔗 Linked Events:**")
                for _, event in linked_events.iterrows():
                    st.write(f"- {event['linked_event']} ({event['event_date']})")
            
            # For options, show additional metrics and payoff diagram
            if is_option:
                option_details = alpaca.parse_option_symbol(position.symbol)
                if option_details:
                    st.write("**📊 Option Details:**")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.write(f"**Underlying:** {option_details['underlying']}")
                        st.write(f"**Strike:** ${option_details['strike']:.2f}")
                    with col2:
                        st.write(f"**Type:** {option_details['option_type']}")
                        st.write(f"**Expiration:** {option_details['expiration']}")
                    with col3:
                        days_left = option_details['days_to_expiration']
                        color = "red" if days_left < 7 else "orange" if days_left < 30 else "green"
                        st.write(f"**Days to Exp:** :{color}[{days_left}]")
                        
                        # Mock IV - in production, integrate with options data provider
                        mock_iv = np.random.uniform(0.2, 0.8)
                        st.write(f"**Implied Vol:** {mock_iv:.1%}")
                    
                    # Create payoff diagram
                    if option_details['underlying']:
                        underlying_price = get_current_stock_price(option_details['underlying'])
                        if underlying_price:
                            fig = create_payoff_diagram(
                                option_details['strike'],
                                pnl_data['avg_entry_price'],
                                option_details['option_type'],
                                underlying_price
                            )
                            st.plotly_chart(fig, use_container_width=True)
                else:
                    st.write("**Option symbol could not be parsed**")
            
            st.divider()

def render_upcoming_opportunities(db: DatabaseManager):
    st.header("🔮 Upcoming Opportunities")
    
    opportunities_df = db.get_upcoming_opportunities()
    
    if opportunities_df.empty:
        st.info("No upcoming opportunities found.")
        return
    
    # Filter controls
    col1, col2 = st.columns(2)
    with col1:
        event_filter = st.selectbox(
            "Filter by Event Type",
            ["All"] + list(opportunities_df['event_type'].unique())
        )
    with col2:
        days_ahead = st.slider("Days ahead to show", 1, 90, 30)
    
    # Apply filters
    filtered_df = opportunities_df.copy()
    if event_filter != "All":
        filtered_df = filtered_df[filtered_df['event_type'] == event_filter]
    
    # Filter by date range
    cutoff_date = datetime.now().date() + timedelta(days=days_ahead)
    filtered_df = filtered_df[pd.to_datetime(filtered_df['event_date']).dt.date <= cutoff_date]
    
    # Display opportunities
    for _, opp in filtered_df.iterrows():
        with st.container():
            col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
            
            with col1:
                st.write(f"**{opp['ticker']}** - {opp['event_name']}")
            with col2:
                st.write(f"📅 {opp['event_date']}")
            with col3:
                st.write(f"🏷️ {opp['event_type']}")
            with col4:
                current_price = get_current_stock_price(opp['ticker'])
                if current_price:
                    st.write(f"💰 ${current_price:.2f}")
            
            st.divider()

def render_trade_history(db: DatabaseManager):
    st.header("📚 Trade History")
    
    history_df = db.get_trade_history()
    
    if history_df.empty:
        st.info("No trade history found.")
        return
    
    # Filter controls
    col1, col2, col3 = st.columns(3)
    with col1:
        ticker_filter = st.selectbox(
            "Filter by Ticker",
            ["All"] + sorted(history_df['ticker'].dropna().unique())
        )
    with col2:
        event_type_filter = st.selectbox(
            "Filter by Event Type",
            ["All"] + list(history_df['event_type'].unique())
        )
    with col3:
        option_type_filter = st.selectbox(
            "Filter by Option Type",
            ["All", "CALL", "PUT"]
        )
    
    # Apply filters
    filtered_df = history_df.copy()
    if ticker_filter != "All":
        filtered_df = filtered_df[filtered_df['ticker'] == ticker_filter]
    if event_type_filter != "All":
        filtered_df = filtered_df[filtered_df['event_type'] == event_type_filter]
    if option_type_filter != "All":
        filtered_df = filtered_df[filtered_df['call_put'] == option_type_filter]
    
    # Display trade history table
    display_cols = ['ticker', 'symbol', 'call_put', 'strike', 'expiration', 'entry_price', 'quantity', 'linked_event', 'event_date']
    st.dataframe(filtered_df[display_cols], use_container_width=True)
    
    # Export to CSV
    if st.button("📥 Export to CSV"):
        csv = filtered_df.to_csv(index=False)
        st.download_button(
            label="Download CSV file",
            data=csv,
            file_name=f"trade_history_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

def render_event_management(db: DatabaseManager):
    st.header("⚙️ Event Management")
    st.info("This section allows manual management of events and trade linking.")
    
    # This would include forms for:
    # - Viewing/editing scraped events
    # - Manually linking events to trades
    # - Viewing source URLs and metadata
    
    st.write("🚧 Event management features coming soon...")

if __name__ == "__main__":
    main()