import json

from config.config import dbConfig, alpacaConfig
from data_inflows.clinical_trials import ClinicalTrialsAggregator
from trading.order_placer import AlpacaTradingClient
from utils.load_companies import load_companies

from alpaca.trading.requests import GetOptionContractsRequest

def main():
    # Initialize the ClinicalTrialsAggregator with the database configuration
    print("Starting program... ")
    aggregator = ClinicalTrialsAggregator(dbConfig)
    trader = AlpacaTradingClient(dbConfig, alpacaConfig)
    # Define the companies to fetch trials for
    companies = [
        "Pfizer",
        "Moderna",
        "Eli Lilly",
        "CRISPR",
        "Verve",
        "Editas",
        "Beam",
        "Intellia"
    ]
    print("Fetching trials for companies")
    # Fetch upcoming trials and save to CSV
    aggregator.fetch_upcoming_trials_v2(window_days=15)
    trader.run()


def test():
    aggregator = ClinicalTrialsAggregator(dbConfig)
    # Fetch companies from the database
    aggregator.fetch_companies_from_db()



if __name__ == "__main__":
    #load_companies(dbConfig)
    main()
    #test()
    print("Program finished successfully.")