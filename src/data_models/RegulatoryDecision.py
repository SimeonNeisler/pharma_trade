from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class RegulatoryDecision:
    company_name: str
    ticker_symbol: str
    drug_name: str
    pdufa_date: datetime
    decision: Optional[str] = None
    description: str = ""
    status: str = "pending"
    USEU: Optional[str] = "US"  # Default to US, can be 'EU' or 'US' based on the decision type

    def __str__(self):
        return (f"RegulatoryDecision(company_name={self.company_name}, \n"
                f"ticker_symbol={self.ticker_symbol}, \ndrug_name={self.drug_name}, \n"
                f"pdufa_date={self.pdufa_date}, \ndecision={self.decision}, \n"
                f"description={self.description}, \nstatus={self.status}, \nUSEU={self.USEU})\n")