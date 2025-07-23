import requests
from time import sleep
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import re
from typing import Dict, List, Optional

from data_models import RegulatoryDecision

class PDUFAScraper:
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def scrape_rtt_news_calendar(self) -> List[RegulatoryDecision]:
        records = []
        for page in range(1, 7):
            try:
                url = f"https://www.rttnews.com/corpinfo/fdacalendar.aspx?PageNum={page}"
                response = self.session.get(url)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')

                print(f"Response status: {response.status_code}")
                print(f"Page title: {soup.title.string if soup.title else 'No title'}")

                # RTT News changed their format - now uses text blocks instead of tables
            
                # Look for calendar data using data-th attributes
                print("Searching for calendar entries using data-th attributes")
                
                # Find all divs with the specific data-th attributes
                company_divs = soup.find_all('div', attrs={'data-th': 'Company Name'})
                drug_divs = soup.find_all('div', attrs={'data-th': 'Drug'})
                event_divs = soup.find_all('div', attrs={'data-th': 'Event'})
                outcome_divs = soup.find_all('div', attrs={'data-th': 'Outcome'})
                
                
                #print(f"Found {len(company_divs)} company entries, {len(drug_divs)} drug entries")
                #print(f"Found {len(event_divs)} event entries, {len(outcome_divs)} outcome entries")
                
                # Group entries by row (assuming they appear in the same order)
                min_length = min(len(company_divs), len(drug_divs), len(event_divs), len(outcome_divs))
                
                for i in range(min_length):
                    try:
                        record = self._parse_data_th_entry(
                            company_divs[i], 
                            drug_divs[i], 
                            event_divs[i], 
                            outcome_divs[i]
                        )
                        if record:
                            records.append(record)
                    except Exception as e:
                        print(f"Error parsing entry {i}: {e}")
                        continue

            except Exception as e:
                print(f"Error scraping RTT News: {e}")
                import traceback
                traceback.print_exc()
            
            sleep(0.2)  # Respectful scraping delay
        
        return records
    
    def _parse_data_th_entry(self, company_div, drug_div, event_div, outcome_div) -> Optional[RegulatoryDecision]:
        """Parse calendar entry from data-th attribute divs"""
        try:
            # Extract text from each div
            company_text = company_div.get_text(strip=True)
            drug_name = drug_div.get_text(strip=True)
            event_text = event_div.get_text(strip=True)
            outcome_text = outcome_div.get_text(strip=True)
            
            # Extract company name and ticker from company text
            company_name, ticker = self._extract_company_and_ticker(company_text)
            
            # Parse date from event text (PDUFA dates are usually in the event description)
            pdufa_date = self._parse_date(event_text)
            if not pdufa_date:
                # Try parsing from outcome text as fallback
                pdufa_date = self._parse_date(outcome_text)
            
            if not pdufa_date:
                print(f"No valid date found for {company_name} - {drug_name}")
                return None
            
            # Determine decision and status from outcome text
            decision = None
            status = "pending"
            outcome_lower = outcome_text.lower()
            
            if "approved" in outcome_lower:
                decision = "approved"
                status = "decided"
            elif any(word in outcome_lower for word in ["denied", "rejected", "declined", "not approved"]):
                decision = "denied"
                status = "decided"
            elif "pending" in outcome_lower or not outcome_text:
                status = "pending"
            
            # Combine event and outcome for description
            description = f"{event_text}. Outcome: {outcome_text}".strip()
            
            return RegulatoryDecision(
                company_name=company_name,
                ticker_symbol=ticker,
                drug_name=drug_name,
                pdufa_date=pdufa_date,
                decision=decision,
                description=description,
                status=status
            )
            
        except Exception as e:
            print(f"Error parsing data-th entry: {e}")
            return None
    
    def _extract_company_and_ticker(self, company_text: str) -> tuple:
        ticker_match = re.search(r'\(([A-Z]{1,5})\)', company_text)
        if ticker_match:
            ticker = ticker_match.group(1)
            company_name = company_text.replace(f'({ticker})', '').strip()
        else:
            ticker_matches = re.findall(r'\b[A-Z]{2,5}\b', company_text)
            if ticker_matches:
                ticker = ticker_matches[-1]
                company_name = company_text.replace(ticker, '').strip()
            else:
                ticker = ""
                company_name = company_text
        
        return company_name, ticker
    
    def _parse_date(self, date_text: str) -> Optional[datetime]:
        date_text = date_text.strip()
        
        patterns = [
            r'(\d{1,2})/(\d{1,2})/(\d{4})',
            r'(\d{4})-(\d{1,2})-(\d{1,2})',
            r'(\w+)\s+(\d{1,2}),?\s+(\d{4})',
            r'Q(\d)\s+(\d{4})',
            r'(\w+)\s+(\d{4})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, date_text)
            if match:
                try:
                    if 'Q' in pattern:
                        quarter = int(match.group(1))
                        year = int(match.group(2))
                        month = (quarter - 1) * 3 + 2
                        return datetime(year, month, 15)
                    elif len(match.groups()) == 2:
                        month_name = match.group(1)
                        year = int(match.group(2))
                        month_num = self._month_name_to_number(month_name)
                        if month_num:
                            return datetime(year, month_num, 15)
                    elif len(match.groups()) == 3:
                        if match.group(1).isdigit():
                            month = int(match.group(1))
                            day = int(match.group(2))
                            year = int(match.group(3))
                            return datetime(year, month, day)
                        else:
                            month_name = match.group(1)
                            day = int(match.group(2))
                            year = int(match.group(3))
                            month_num = self._month_name_to_number(month_name)
                            if month_num:
                                return datetime(year, month_num, day)
                except ValueError:
                    continue
        
        return None
    
    def _month_name_to_number(self, month_name: str) -> Optional[int]:
        months = {
            'january': 1, 'february': 2, 'march': 3, 'april': 4,
            'may': 5, 'june': 6, 'july': 7, 'august': 8,
            'september': 9, 'october': 10, 'november': 11, 'december': 12,
            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
            'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
        }
        return months.get(month_name.lower())
    
    def scrape_multiple_sources(self) -> List[RegulatoryDecision]:
        all_records = []
        
        rtt_records = self.scrape_rtt_news_calendar()
        all_records.extend(rtt_records)
        
        return self._deduplicate_records(all_records)
    
    def _deduplicate_records(self, records: List[RegulatoryDecision]) -> List[RegulatoryDecision]:
        seen = set()
        unique_records = []
        
        for record in records:
            key = (record.ticker_symbol, record.drug_name, record.pdufa_date.strftime('%Y-%m-%d'))
            if key not in seen:
                seen.add(key)
                unique_records.append(record)
        
        return unique_records
    
    def _record_to_dict(self, record: RegulatoryDecision) -> Dict:
        return {
            'company_name': record.company_name,
            'ticker_symbol': record.ticker_symbol,
            'drug_name': record.drug_name,
            'pdufa_date': record.pdufa_date.isoformat(),
            'decision': record.decision,
            'description': record.description,
            'status': record.status
        }
    
    def run_full_scrape(self) -> Dict[str, int]:
        print("Starting PDUFA data scraping...")
        
        records = self.scrape_multiple_sources()
        print(f"Scraped {len(records)} unique PDUFA records")
        
        return records

if __name__ == "__main__":
    scraper = PDUFAScraper()
    result = scraper.run_full_scrape()
    print(f"Scraping completed: {result}")