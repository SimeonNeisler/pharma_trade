#!/usr/bin/env python3
"""
Biotech Company Screener
Generates a list of publicly traded biotech companies and filters by Alpaca API tradability
"""


from config.config import alpacaConfig, dbConfig
from data_models.Company import Company
from .add_clinical_trials_tags import enhance_with_clinical_trials_tags

import yfinance as yf
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetAssetsRequest
from alpaca.trading.enums import AssetClass, AssetStatus
import psycopg as ppg

import json
import time
from typing import Set, List

class BiotechScreener:
    def __init__(self):
        """Initialize the screener with Alpaca client"""
        self.conn = ppg.connect(
            dbname=dbConfig.DB_NAME,
            user=dbConfig.DB_USER,
            host=dbConfig.DB_HOST,
            password=dbConfig.DB_PASSWORD
        )
        self.cursor = self.conn.cursor()
        self.trading_client = TradingClient(
            alpacaConfig.ALPACA_API_KEY,
            alpacaConfig.ALPACA_SECRET_KEY,
            paper=True
        )
        
        # Comprehensive list of biotech ticker symbols (small to mid-cap focus)
    def get_company_info(self, ticker):
        """Get company information using yfinance"""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            return {
                'ticker': ticker,
                'company_name': info.get('longName', 'N/A'),
                'market_cap': info.get('marketCap', 0),
                'sector': info.get('sector', 'N/A'),
                'industry': info.get('industry', 'N/A'),
                'current_price': info.get('regularMarketPrice', 0),
                'volume': info.get('volume', 0),
                'exchange': info.get('exchange', 'N/A')
            }
        except Exception as e:
            print(f"Error getting info for {ticker}: {e}")
            return None
        
    def filter_already_in_db(self, tickers: set[str]):
        """Check if tickers are already in the database"""
        self.cursor.execute("SELECT ticker FROM companies")
        existing_tickers = self.cursor.fetchall()
        
        for tick in existing_tickers:
            if tick in tickers:
                tickers.remove(tick)

        return tickers
    
    def check_alpaca_tradability(self, ticker):
        """Check if a ticker is tradable on Alpaca"""
        try:
            # Get asset information from Alpaca
            search_request = GetAssetsRequest(
                status=AssetStatus.ACTIVE,
                asset_class=AssetClass.US_EQUITY
            )
            assets = self.trading_client.get_all_assets(search_request)
            
            # Check if ticker exists in Alpaca assets
            for asset in assets:
                if asset.symbol == ticker:
                    return {
                        'tradable': True,
                        'shortable': asset.shortable,
                        'marginable': asset.marginable,
                        'fractionable': asset.fractionable,
                        'options_trading': getattr(asset, 'options_trading', False)
                    }
            
            return {'tradable': False}
            
        except Exception as e:
            print(f"Error checking Alpaca tradability for {ticker}: {e}")
            return {'tradable': False, 'error': str(e)}
    
    def categorize_by_market_cap(self, market_cap):
        """Categorize company by market cap"""
        if market_cap == 0:
            return "Unknown"
        elif market_cap < 300_000_000:
            return "Micro-cap"
        elif market_cap < 2_000_000_000:
            return "Small-cap"
        elif market_cap < 10_000_000_000:
            return "Mid-cap"
        else:
            return "Large-cap"
    
    def screen_biotech_companies(self, tickers):
        """Main screening function"""
        results = []
        tradable_companies = []

        tickers = self.filter_already_in_db(tickers)
        
        print("Screening biotech companies...")
        print(f"Total tickers to check: {len(tickers)}")
        
        for i, ticker in enumerate(tickers, 1):
            print(f"Processing {i}/{len(tickers)}: {ticker}")
            
            # Get company info
            company_info = self.get_company_info(ticker)
            if not company_info:
                continue
            
            # Check Alpaca tradability
            alpaca_info = self.check_alpaca_tradability(ticker)
            
            # Combine information
           
            result = Company(
                ticker_symbol=company_info['ticker'],
                company_name=company_info['company_name'],
                sector=company_info['sector'],
                industry=company_info['industry'],
                market_cap=company_info['market_cap'],
                exchange=company_info['exchange'],
                market_cap_category=self.categorize_by_market_cap(company_info['market_cap']),
                alpaca_tradable = alpaca_info.get('tradable', False),
                alpaca_shortable = alpaca_info.get('shortable', False),
                alpaca_marginable = alpaca_info.get('marginable', False),
                alpaca_fractionable = alpaca_info.get('fractionable', False),
            )

            # Set search phrases for clinical trials
            result = enhance_with_clinical_trials_tags(result)
            
            self.write_company_to_db(result)
            
            # Small delay to avoid rate limiting
            time.sleep(0.1)
        
        return results, tradable_companies
    
    def write_company_to_db(self, company: Company):
        """Insert or update the company in the database"""
        try:
            self.cursor.execute(
                """
                INSERT INTO companies (ticker, company_name, sector, industry, exchange, market_cap_category, alpaca_tradable, alpaca_shortable, alpaca_marginable, alpaca_fractionable, clinical_trials_search_phrases, primary_search_phrase)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    company.ticker_symbol,
                    company.company_name,
                    company.sector,
                    company.industry,
                    company.exchange,
                    company.market_cap_category,
                    company.alpaca_tradable,
                    company.alpaca_shortable,
                    company.alpaca_marginable,
                    company.alpaca_fractionable,
                    ','.join(company.search_phrases),
                    company.primary_search_phrase
                ))
            self.conn.commit()
        except Exception as e:
            print(f"Error writing {company.ticker_symbol} to database: {e}")
            self.conn.rollback()
    
    def print_summary(self, all_results, tradable_results):
        """Print summary of results"""
        print(f"\n{'='*60}")
        print("BIOTECH COMPANY SCREENING SUMMARY")
        print(f"{'='*60}")
        print(f"Total companies analyzed: {len(all_results)}")
        print(f"Companies tradable on Alpaca: {len(tradable_results)}")
        print(f"Alpaca tradability rate: {len(tradable_results)/len(all_results)*100:.1f}%")
        
        # Market cap breakdown for tradable companies
        cap_categories = {}
        for company in tradable_results:
            category = company['market_cap_category']
            cap_categories[category] = cap_categories.get(category, 0) + 1
        
        print(f"\nTradable companies by market cap:")
        for category, count in cap_categories.items():
            print(f"  {category}: {count} companies")
        
        # Top 10 tradable companies by market cap
        tradable_sorted = sorted(tradable_results, key=lambda x: x['market_cap'], reverse=True)
        print(f"\nTop 10 tradable biotech companies by market cap:")
        for i, company in enumerate(tradable_sorted[:10], 1):
            market_cap_b = company['market_cap'] / 1_000_000_000
            print(f"  {i:2d}. {company['ticker']:4s} - {company['company_name'][:40]:40s} ${market_cap_b:5.1f}B")

def main():
    screener = BiotechScreener()
    all_results, tradable_results = screener.screen_biotech_companies()
    
    screener.save_results(all_results, tradable_results)
    screener.print_summary(all_results, tradable_results)

if __name__ == "__main__":
    main()