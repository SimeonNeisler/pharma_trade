class Company:
    def __init__(self, ticker_symbol, company_name, sector, industry, exchange, market_cap, market_cap_category="Unknown", alpaca_tradable=False, alpaca_shortable=False, alpaca_marginable=False, alpaca_fractionable=False):

        self.ticker_symbol = ticker_symbol
        self.company_name = company_name
        self.sector = sector
        self.industry = industry
        self.market_cap = market_cap
        self.market_cap_category = market_cap_category
        self.exchange = exchange
        self.alpaca_tradable = alpaca_tradable
        self.alpaca_shortable = alpaca_shortable
        self.alpaca_marginable = alpaca_marginable
        self.alpaca_fractionable = alpaca_fractionable
        self.search_phrases = []
        self.primary_search_phrase = ""


    def __repr__(self):
        return f"Company(ticker_symbol={self.ticker_symbol}, company_name={self.company_name}, sector={self.sector}, industry={self.industry}, market_cap={self.market_cap})"
    
    def set_search_phrases(self, phrases):
        """Add multiple search phrases to the company's list"""
        self.search_phrases = phrases
        self.primary_search_phrase = phrases[0] if phrases else self.company_name

    def get_search_phrases(self):
        """Return the list of search phrases"""
        return self.search_phrases
    
