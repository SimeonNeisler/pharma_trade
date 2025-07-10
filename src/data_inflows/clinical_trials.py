import re
import requests
import json
import pandas as pd
from datetime import datetime, timedelta
import psycopg as ppg

import config.config as dbConfig
import data_models.Study as Study

# Constants
BASE_URL = "https://clinicaltrials.gov/api/v2/studies"
FIELDS = [
    "NCTId",
    "BriefTitle",
    "OverallStatus",
    "Phase",
    "PrimaryCompletionDate",
    "StartDate",
    "LastUpdatePostDate",
    "LeadSponsorName",
    "CollaboratorName",
    "Condition"
]

# Date range
TODAY = datetime.today()
WINDOW_DAYS = 60
END_DATE = TODAY + timedelta(days=WINDOW_DAYS)

class ClinicalTrialsAggregator:

    def __init__(self, dbConfig):
        print(dbConfig)
        self.conn = ppg.connect(dbname=dbConfig.DB_NAME,
                                user=dbConfig.DB_USER,
                                host=dbConfig.DB_HOST)
        self.cursor = self.conn.cursor()

    def __del__(self):
        #Close DB connection when object is deleted
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()

    def parse_study(self, study):
        """Parse a single study entry into a Study object."""
        protocol = study.get("protocolSection", {})
        design = protocol.get("designModule", {})
        status = protocol.get("statusModule", {})
        idmod = protocol.get("identificationModule", {})
        
        nctID = idmod.get("nctId", "")
        sponsor_mod = protocol.get("sponsorCollaboratorsModule", {})
        lead_sponsor = sponsor_mod.get("leadSponsor", {})
        cond_mod = protocol.get("conditionsModule", {})

        phases = design.get("phases", [])
        phase = phases[0] if phases else ""
        pcd_str = status.get("primaryCompletionDateStruct", {}).get("date", "")
        
        year_month_regex = r"^\d{4}-\d{2}$"
        if re.match(year_month_regex, pcd_str):
            pcd_str += "-01"
        if not phase or not pcd_str:
            return None
        
        date = self.parse_date(pcd_str)

        study = Study(
            nctid = nctID,
            title = idmod.get("briefTitle", ""),
            phase = phase,
            pcd = date,
            primary_sponsor=lead_sponsor.get("name", ""),
            conditions=", ".join(cond_mod.get("conditions", []))
        )
       #print(study)
        return study

    def parse_date(self, date_str):
        """Parse dates from API (ISO 8601 or fallback)."""
        try:
            return datetime.fromisoformat(date_str.split("T")[0])
        except Exception:
            return None


    def write_to_db(self, study):
        """Write a Study object to the database."""
        try:
            self.cursor.execute(
                """
                INSERT INTO clinical_trials (nctid, title, phase, pcd, primary_sponsor, conditions)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (nctid) DO NOTHING
                """,
                (study.nctid, study.title, study.phase, study.pcd, study.primary_sponsor, study.conditions)
            )
            self.conn.commit()
        except Exception as e:
            print(f"Error writing to DB: {e}")
            self.conn.rollback()
        
    def fetch_upcoming_trials_v2(self, companies, window_days=60, output_csv="clinical_trials_pipeline_output_v2.csv"):
        """Fetch Phase 2/3 trials with primary completion dates in next X days using V2 API."""
        
        
        for company in companies:
            
            params = {
                'format': 'json',
                'filter.overallStatus': 'RECRUITING,ACTIVE_NOT_RECRUITING',
                'filter.advanced': 'AREA[Phase]PHASE3,AREA[LeadSponsorClass]INDUSTRY,AREA[LeadSponsorName]{}'.format(company),
                'fields': ','.join(FIELDS)
            }
            
            page_token = None
            while True:
                if page_token:
                    params["pageToken"] = page_token
                
                try:
                    response = requests.get(BASE_URL, params=params)
                    with open('../data/studies.json', 'w') as f:
                        json.dump(response.json(), f, indent=2) # indent=4 specifies 4 spaces for indentation
                    data = response.json()
                    response.raise_for_status()
                    
                except Exception as e:
                    print(f"Error fetching trials for {company}: {e}")
                    break
                
                # Process each study (updated for studies.json structure)
                for study in data["studies"]:
                    study = self.parse_study(study)
                    if not study:
                        continue

                    if study.phase not in ["PHASE2", "PHASE3", "PHASE2/PHASE3"]:
                        continue
                    
                    # Filter date window
                    if TODAY <= study.pcd <= (TODAY + timedelta(days=window_days)):
                        self.write_to_db(study)
                
                # Check for next page
                page_token = data.get("nextPageToken")
                if not page_token:
                    break


