from typing import List
import json
from datetime import datetime
from typing import List

import psycopg as ppg

from .pdufa_scraper import PDUFAScraper
from data_models import RegulatoryDecision


class PDUFAManager:
    
    def __init__(self, db_settings):
        self.scraper = PDUFAScraper()
        self.conn = ppg.connect(dbname=db_settings.DB_NAME,
                                user=db_settings.DB_USER,
                                host=db_settings.DB_HOST,
                                password=db_settings.DB_PASSWORD)
        self.cursor = self.conn.cursor()
    
    def get_records(self):
        print("Updating PDUFA data from web sources...")
        records = self.scraper.run_full_scrape()
        return records

    
    def sort_records(self, records):
        today = datetime.now()
        
        previous_decisions = []
        impending_decisions = []
        companies = set()
        
        for record in records:
            if record.pdufa_date < today or record.status == "decided":
                previous_decisions.append(record)
            else:
                impending_decisions.append(record)
            companies.add(record.ticker_symbol)
        
        
        result = {
            'total_records': len(records),
            'records': records,
            'companies': companies,
            'previous_decisions': previous_decisions,
            'impending_decisions': impending_decisions
        }
        return result
    
    
    def get_impending_decisions(self):
        self.cursor.execute("SELECT * FROM regulatory_decisions WHERE status = 'pending'")
        rows = self.cursor.fetchall()
        records = []
        for row in rows:
            record = RegulatoryDecision(
                company_name=row[1],
                ticker_symbol=row[2],
                drug_name=row[3],
                pdufa_date=row[4],
                decision=row[5],
                description=row[6],
                status=row[7]
            )
            records.append(record)
        return records

    
    def get_previous_decisions(self):
        self.cursor.execute("SELECT * FROM regulatory_decisions WHERE status != 'pending'")
        rows = self.cursor.fetchall()
        records = []
        for row in rows:
            record = RegulatoryDecision(
                company_name=row[1],
                ticker_symbol=row[2],
                drug_name=row[3],
                pdufa_date=row[4],
                decision=row[5],
                description=row[6],
                status=row[7]
            )
            records.append(record)
        return records
    
    def get_upcoming_by_ticker(self, ticker: str):
        impending = self.get_impending_decisions()
        return [record for record in impending if record.get('ticker_symbol', '').upper() == ticker.upper()]
    
    def get_decisions_by_date_range(self, start_date: str, end_date: str):
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
        
        all_records = self.get_impending_decisions() + self.get_previous_decisions()
        filtered = []
        
        for record in all_records:
            record_date = datetime.fromisoformat(record['pdufa_date'])
            if start <= record_date <= end:
                filtered.append(record)
        
        return sorted(filtered, key=lambda x: x['pdufa_date'])
    
    
    def write_records_to_db(self, records: List[RegulatoryDecision]):
        for record in records:
            self.cursor.execute(
                """
                INSERT INTO regulatory_decisions(useu, ticker, drug_name, date, status, decision)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (ticker, drug_name, date) DO NOTHING
                """,
                (record.USEU, record.ticker_symbol, record.drug_name, record.pdufa_date, record.status, record.decision)
            )
            self.conn.commit()
    
    def print_summary(self):
        impending = self.get_impending_decisions()
        previous = self.get_previous_decisions()
        
        print(f"\n=== PDUFA Data Summary ===")
        print(f"Impending decisions: {len(impending)}")
        print(f"Previous decisions: {len(previous)}")
        
        if impending:
            print(f"\nNext 5 upcoming PDUFA dates:")
            sorted_impending = sorted(impending, key=lambda x: x['pdufa_date'])[:5]
            for record in sorted_impending:
                print(f"  {record['pdufa_date']}: {record['ticker_symbol']} - {record['drug_name']}")

    def verify_decisions(self, records: List[RegulatoryDecision]) -> None:
        """
        Check drug approval status against openFDA API.
        Updates record status to 'decided' and decision to 'Approved' if drug is found.
        Modifies records in place.
        """
        import requests
        from time import sleep
        
        for record in records:
            try:
                # Search openFDA drug approvals API
                url = "https://api.fda.gov/drug/drugsfda.json"
                params = {
                    'search': f'openfda.brand_name:"{record.drug_name}" OR openfda.generic_name:"{record.drug_name}"',
                    'limit': 1
                }
                
                response = requests.get(url, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get('results') and len(data['results']) > 0:
                        # Drug found in FDA approvals database
                        print(f"Found approved drug: {record.drug_name}")
                        record.status = "decided"
                        record.decision = "Approved"
                    else:
                        print(f"Drug not found in FDA database: {record.drug_name}")
                        
                elif response.status_code == 404:
                    # No results found
                    print(f"No FDA approval found for: {record.drug_name}")
                    
                else:
                    print(f"FDA API error for {record.drug_name}: {response.status_code}")
                    
            except Exception as e:
                print(f"Error checking FDA status for {record.drug_name}: {e}")
            
            # Be respectful to the API
            sleep(0.3)

    def pull_records(self):
        records = self.get_records()
        self.verify_decisions(records)
        return self.sort_records(records)
    
