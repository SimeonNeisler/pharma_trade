from config.config import dbConfig, alpacaConfig
from data_inflows.clinical_trials import ClinicalTrialsAggregator
from trading.order_placer import AlpacaTradingClient

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
    aggregator.fetch_upcoming_trials_v2(companies, window_days=60)
    trader.run()


def test():
    trader = AlpacaTradingClient(dbConfig, alpacaConfig)
    optionRequest = GetOptionContractsRequest(root_symbol="PFE", expiration_date="2025-12-19", type="call", strike_price_gte="10.0", strike_price_lte="30.0", style="american")
    options_chain = trader.trading_client.get_option_contracts(optionRequest)
    print(options_chain)

if __name__ == "__main__":
    main()
    #test()
    print("Program finished successfully.")