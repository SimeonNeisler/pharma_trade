#!/usr/bin/env python3
"""
Add Clinical Trials Search Tags
Enhances the tradable biotech companies list with clinical trials.gov search phrases
"""
from data_models import Company
from typing import List
import json

def get_clinical_trials_search_phrases(company_name):
    """
    Generate search phrases for clinical trials.gov API based on company ticker and name
    Returns company name variations only (no drug/product names)
    """
    
    # Company name search mappings - only company names and variations
    # Add generic company name variations
    search_phrases = []
    if company_name and company_name != 'N/A':
        # Clean company name
        clean_name = company_name.replace(' Inc.', '').replace(' Corporation', '').replace(' Pharmaceuticals', '').replace(' Therapeutics', '').replace(' AG', '').replace(' Plc', '').replace(',', '')
        search_phrases.append(clean_name)
        
        # Add abbreviated versions
        if 'Pharmaceuticals' in company_name:
            search_phrases.append(clean_name + ' Pharma')
        if 'Therapeutics' in company_name:
            search_phrases.append(clean_name + ' Tx')
    
    # Remove duplicates and return
    return list(set(search_phrases))

def enhance_with_clinical_trials_tags(company: Company):
    """
    Load tradable companies and add clinical trials search phrases
    """
    
    # Load existing tradable companies data
    with open('/Users/simeonneisler/Projects/pharma_trade/data/biotech_companies_tradable.json', 'r') as f:
        companies = json.load(f)
    
    print(f"Enhancing {len(companies)} companies with clinical trials search phrases...")
    
    # Add clinical trials search phrases to each company
    company_name = company.company_name
    
    # Generate search phrases
    search_phrases = get_clinical_trials_search_phrases(company_name)
    
    # Add to company data
    company.set_search_phrases(search_phrases)
        
    
    # Save enhanced data
    return company

def print_search_phrases_summary(companies):
    """
    Print a summary of clinical trials search phrases for each company
    """
    print(f"\n{'='*80}")
    print("CLINICAL TRIALS SEARCH PHRASES SUMMARY")
    print(f"{'='*80}")
    
    for company in companies:
        ticker = company['ticker']
        company_name = company['company_name']
        phrases = company['clinical_trials_search_phrases']
        primary = company['primary_search_phrase']
        
        print(f"\n{ticker} - {company_name}")
        print(f"  Primary Search: '{primary}'")
        print(f"  All Phrases: {phrases}")

def main():
    companies = enhance_with_clinical_trials_tags()
    print_search_phrases_summary(companies)

if __name__ == "__main__":
    main()