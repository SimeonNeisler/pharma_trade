#import json

from config import dbConfig, alpacaConfig
from data_inflows import ClinicalTrialsAggregator
from data_inflows import PDUFAManager, PDUFAScraper
from trading.order_placer import AlpacaTradingClient
from utils import BiotechScreener

#from alpaca.trading.requests import GetOptionContractsRequest

#import requests

def main():
    # Initialize the ClinicalTrialsAggregator with the database configuration
    aggregator = ClinicalTrialsAggregator(dbConfig)
    trader = AlpacaTradingClient(dbConfig, alpacaConfig)
    pdufa_manager = PDUFAManager(db_settings=dbConfig)
    biotech_screener = BiotechScreener()

    results = pdufa_manager.pull_records()
    companies = results['companies']

    companies = biotech_screener.screen_biotech_companies(companies)

    pdufa_manager.write_records_to_db(results['records'])

    # Define the companies to fetch trials for
    # Fetch upcoming trials and save to CSV
    aggregator.fetch_upcoming_trials_v2()
    trader.run()


def test():
    
    return


if __name__ == "__main__":
    #load_companies(dbConfig)
    main()
    #test()
    print("Program finished successfully.")