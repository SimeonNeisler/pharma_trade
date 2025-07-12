import psycopg as ppg
from datetime import datetime, timedelta
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.trading.requests import GetOptionContractsRequest
import yfinance as yf

class AlpacaTradingClient:
    def __init__(self, db_config, alpaca_config):
        """
        Initialize database and trading connections
        """
        # Database connection
        self.conn = ppg.connect(
            dbname=db_config.DB_NAME,
            user=db_config.DB_USER,
            host=db_config.DB_HOST,
            password=db_config.DB_PASSWORD
        )
        self.cursor = self.conn.cursor()

        # Alpaca client
        self.trading_client = TradingClient(
            alpaca_config.ALPACA_API_KEY,
            alpaca_config.ALPACA_SECRET_KEY,
            paper=True  # Use paper trading
        )

    def __del__(self):
        """
        Clean up connections
        """
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()

    def get_upcoming_studies(self):
        """
        Get studies from database where primary completion date is within 2 weeks
        """
        two_months = datetime.now() + timedelta(days=60)
        
        self.cursor.execute("""
            SELECT nctid, title, phase, pcd, primary_sponsor, primary_sponsor_ticker, conditions 
            FROM clinical_trials 
            WHERE pcd <= %s
            ORDER BY pcd ASC
        """, (two_months,))
        
        return self.cursor.fetchall()
    '''
    def get_ticker_symbol(self, company_name):
        """
        Convert company name to stock ticker symbol.
        This is a simplified version - in production you'd want a more robust mapping.
        """
        # Basic mapping of company names to tickers
        company_map = {
            'Pfizer': 'PFE',
            'Moderna': 'MRNA',
            'Eli Lilly': 'LLY',
            'Eli Lilly and Company': 'LLY',
            'CRISPR': 'CRSP',
            'Verve': 'VERV',
            'Editas': 'EDIT',
            'Beam': 'BEAM',
            'Intellia': 'NTLA'
        }
        
        return company_map.get(company_name)
    '''
    def get_stock_price(self, ticker):
        """
        Get the closest strike price to current stock price
        """
        try:
            # Get current stock price using yfinance
            stock = yf.Ticker(ticker)
            current_price = stock.info['regularMarketPrice']
            
            return current_price
            # Find closest strike to current price
            atm_strike = min(strikes, key=lambda x: abs(x - current_price))
            return atm_strike
            
        except Exception as e:
            print(f"Error getting stock price for {ticker}: {e}")
            return None

    def get_best_contract(self, ticker, target_date):
            
            stock_price = self.get_stock_price(ticker)

            strike_price_lower_bound = stock_price - 5
            strike_price_upper_bound = stock_price + 5
            
            date_lower_bound = target_date - timedelta(days=7)
            date_upper_bound = target_date + timedelta(days=7)

            optionContractsRequest = GetOptionContractsRequest(root_symbol=ticker, style="american", type="call", expiration_date_gte=date_lower_bound.strftime('%Y-%m-%d'), expiration_date_lte=date_upper_bound.strftime('%Y-%m-%d'), strike_price_gte=str(strike_price_lower_bound), strike_price_lte=str(strike_price_upper_bound))
            optionResponse = self.trading_client.get_option_contracts(optionContractsRequest)
            print("Option Contracts: ", optionResponse.option_contracts)
            if not optionResponse.option_contracts:
                print(f"No option contracts found for {ticker} within the specified bounds.")
                return None, None
            
            atm_strike = min([float(option.strike_price) for option in optionResponse.option_contracts if option.strike_price is not None], key=lambda x: abs(x - stock_price))

            best_date = min(optionResponse.option_contracts, key=lambda x: abs(x.expiration_date - target_date)).expiration_date
            print("Best Date: ", best_date)
            print("Best Date type: ", type(best_date))

            best_options = self.trading_client.get_option_contracts(GetOptionContractsRequest(root_symbol=ticker, expiration_date=best_date, style="american", strike_price_gte=str(atm_strike), strike_price_lte=str(atm_strike)))
            #best_put = self.tradient_client.get_option_contracts(GetOptionContractsRequest(root_symbol=ticker, expiration_date=best_date, style="american", strike_price_gte=str(atm_strike), strike_price_lte=str(atm_strike)))
            #print("Contracts lengths: ", len(best_call.option_contracts))
            print("Contracts: ", best_options.option_contracts)
            return best_options.option_contracts[0].symbol, best_options.option_contracts[1].symbol

    def place_option_orders(self, study):
        """
        Place at-the-money call and put orders for a given study
        """
        ticker = study[5] 
        if not ticker:
            print(f"No ticker found for company: {study[4]}")
            return

        # Get ATM strike

        # Calculate option expiration (60 days after primary completion date)
        pcd = study[3]  # study[3] is pcd
        target_date = pcd + timedelta(days=60)
        target_date_str = target_date.strftime('%Y-%m-%d')

        best_call, best_put = self.get_best_contract(ticker, target_date)
        if not best_call or not best_put:
            print(f"No suitable options found for {ticker} on {target_date_str}")
            return
        try:
            # Place call order
            call_order = MarketOrderRequest(
                symbol=best_call,
                qty=1,
                side=OrderSide.BUY,
                time_in_force=TimeInForce.DAY
            )
            call_result = self.trading_client.submit_order(call_order)
            
            # Place put order
            put_order = MarketOrderRequest(
                symbol=best_put,
                qty=1,
                side=OrderSide.BUY,
                time_in_force=TimeInForce.DAY
            )
            put_result = self.trading_client.submit_order(put_order)
            
            print(f"Placed orders for {ticker} study {study[0]}:")
            print(f"Call order: {call_result.id}")
            print(f"Put order: {put_result.id}")
            
        except Exception as e:
            print(f"Error placing orders for {ticker}: {e}")

    def run(self):
        """
        Main method to run the order placement process
        """
        try:
            # Get upcoming studies
            studies = self.get_upcoming_studies()
            if not studies:
                print("No upcoming studies found within 2 months")
                return

            print(f"Found {len(studies)} upcoming studies")
            
            # Place orders for each study
            for study in studies:
                print(f"\nProcessing study {study[0]} for {study[4]}")
                self.place_option_orders(study)
                
        except Exception as e:
            print(f"Error in run process: {e}")

if __name__ == "__main__":
    from config.config import dbConfig, alpacaConfig
    
    # Initialize and run the order placer
    order_placer = AlpacaTradingClient(dbConfig, alpacaConfig)
    order_placer.run()
