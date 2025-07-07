import requests
import json
import pandas as pd
from datetime import datetime, timedelta

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

def parse_date(date_str):
    """Parse dates from API (ISO 8601 or fallback)."""
    try:
        return datetime.fromisoformat(date_str.split("T")[0])
    except Exception:
        return None

def fetch_upcoming_trials_v2(companies, window_days=60, output_csv="clinical_trials_pipeline_output_v2.csv"):
    """Fetch Phase 2/3 trials with primary completion dates in next X days using V2 API."""
    
    all_trials = []
    
    for company in companies:
        print(f"\nFetching trials for: {company}")
        
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
                print(f"JSON data successfully saved to studies.json with pretty-printing.")
                data = response.json()
                response.raise_for_status()
                
            except Exception as e:
                print(f"Error fetching trials for {company}: {e}")
                break
            
            # Process each study
            for study in data["studies"]:
                #print(study)
                phase = study.get("phase", "")
                status = study.get("studyStatus", "")
                pcd_str = study.get("primaryCompletionDate", "")
                print(pcd_str)
                pcd_date = parse_date(pcd_str)
                
                # Filter Phase / Status
                if phase not in ["Phase 2", "Phase 3"]:
                    continue
                if pcd_date is None:
                    continue
                
                # Filter date window
                if TODAY <= pcd_date <= (TODAY + timedelta(days=window_days)):
                    trial_entry = {
                        "Company": company,
                        "nctId": study.get("nctId", ""),
                        "briefTitle": study.get("briefTitle", ""),
                        "conditions": ", ".join(study.get("conditions", [])),
                        "phase": phase,
                        "studyStatus": status,
                        "primaryCompletionDate": pcd_date.strftime("%Y-%m-%d"),
                        "sponsor": study.get("sponsor", ""),
                        "startDate": study.get("startDate", "")
                    }
                    all_trials.append(trial_entry)
            
            # Check for next page
            page_token = data.get("nextPageToken")
            if not page_token:
                break
    
    # Create DataFrame
    df = pd.DataFrame(all_trials)
    print(f"\n=== Total Trials Found (Next {window_days} Days): {len(df)} ===\n")
    
    # Save CSV
    df.to_csv(output_csv, index=False)
    print(f"\nResults saved to {output_csv}")
    
    return df

# --- Example usage ---

COMPANIES = [
    "Pfizer",
    "Moderna",
    "Eli Lilly",
    "CRISPR",
    "Verve",
    "Editas",
    "Beam",
    "Intellia"
]

if __name__ == "__main__":
    df = fetch_upcoming_trials_v2(COMPANIES, window_days=60)
    print(df)
