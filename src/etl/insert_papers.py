"""
Insert PubMed Papers into Database
Elenta Suzan Jacob - Week 2
"""

import json
import sys
sys.path.append('database_files')
from database import FitFactDB

def insert_papers_from_json(json_file):
    """Insert papers from JSON file into database"""
    
    # Connect to database
    print("Connecting to database...")
    db = FitFactDB()
    
    # Load papers from JSON
    print(f"Loading papers from {json_file}...")
    with open(json_file, 'r', encoding='utf-8') as f:
        papers = json.load(f)
    
    print(f"Found {len(papers)} papers to insert\n")
    
    # Insert each paper
    success_count = 0
    for i, paper in enumerate(papers, 1):
        try:
            print(f"[{i}/{len(papers)}] Inserting PMID {paper['pmid']}...")
            
            # Use Satya's save_paper method
            db.save_paper(
                pmid=paper['pmid'],
                title=paper['title'],
                abstract=paper['abstract'],
                authors=paper['authors'],
                pub_date=paper['publication_date'],
                journal=paper['journal'],
                study_type='Research Article'  # Default type
            )
            
            print(f"  ✓ {paper['title'][:60]}...")
            success_count += 1
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
    
    # Summary
    print("\n" + "="*60)
    print("INSERTION COMPLETE!")
    print("="*60)
    print(f"✓ Successfully inserted: {success_count}/{len(papers)} papers")
    print("="*60)
    
    db.close()

if __name__ == "__main__":
    # Insert sample papers
    insert_papers_from_json("data/pubmed_papers_sample.json")