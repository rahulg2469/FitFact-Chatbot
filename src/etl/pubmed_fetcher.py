"""
PubMed Article Fetcher - Elenta Suzan Jacob
Fetches research papers on fitness topics from PubMed
Uses requests library with XML parsing
"""

import os
import json
import time
import requests
from datetime import datetime
from dotenv import load_dotenv
import xml.etree.ElementTree as ET
import sys
sys.path.append('database_files')
from database import FitFactDB

load_dotenv()

PUBMED_API_KEY = os.getenv('PUBMED_API_KEY')
PUBMED_EMAIL = os.getenv('PUBMED_EMAIL')

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

SEARCH_TOPICS = [
    "resistance training muscle hypertrophy",
    "cardiovascular exercise fitness",
    "protein supplementation muscle",
    "creatine supplementation performance",
    "HIIT high intensity interval training"
]

def search_pubmed(query, max_results=10):
    print(f"Searching: {query} (max {max_results} papers)...")
    
    params = {
        'db': 'pubmed',
        'term': query,
        'retmax': max_results,
        'retmode': 'xml',
        'api_key': PUBMED_API_KEY,
        'email': PUBMED_EMAIL
    }
    
    try:
        response = requests.get(ESEARCH_URL, params=params)
        response.raise_for_status()
        
        root = ET.fromstring(response.content)
        id_list = root.find('.//IdList')
        
        if id_list is None:
            return []
        
        pmids = [id_elem.text for id_elem in id_list.findall('Id')]
        print(f"  ✓ Found {len(pmids)} papers")
        
        time.sleep(0.34)
        return pmids
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return []

def fetch_paper_details(pmid):
    params = {
        'db': 'pubmed',
        'id': pmid,
        'rettype': 'abstract',
        'retmode': 'xml',
        'api_key': PUBMED_API_KEY,
        'email': PUBMED_EMAIL
    }
    
    try:
        response = requests.get(EFETCH_URL, params=params)
        response.raise_for_status()
        
        root = ET.fromstring(response.content)
        article = root.find('.//Article')
        
        if article is None:
            return None
        
        title_elem = article.find('.//ArticleTitle')
        title = title_elem.text if title_elem is not None else "No title"
        
        abstract_parts = article.findall('.//AbstractText')
        abstract = " ".join([part.text or "" for part in abstract_parts]) if abstract_parts else "No abstract"
        
        journal_elem = article.find('.//Journal/Title')
        journal = journal_elem.text if journal_elem is not None else "Unknown journal"
        
        pub_date = article.find('.//Journal/JournalIssue/PubDate')
        year = "Unknown"
        month = "01"
        day = "01"
        
        if pub_date is not None:
            year_elem = pub_date.find('Year')
            month_elem = pub_date.find('Month')
            day_elem = pub_date.find('Day')
            
            year = year_elem.text if year_elem is not None else "Unknown"
            month = month_elem.text if month_elem is not None else "01"
            day = day_elem.text if day_elem is not None else "01"
        
        authors = []
        author_list = article.findall('.//Author')
        for author in author_list[:3]:
            lastname = author.find('LastName')
            initials = author.find('Initials')
            if lastname is not None and initials is not None:
                authors.append(f"{lastname.text} {initials.text}")
        
        mesh_terms = []
        mesh_list = root.findall('.//MeshHeading/DescriptorName')
        for mesh in mesh_list[:5]:
            if mesh.text:
                mesh_terms.append(mesh.text)
        
        paper_info = {
            'pmid': pmid,
            'title': title,
            'abstract': abstract,
            'journal': journal,
            'publication_date': f"{year}-{month}-{day}",
            'authors': authors,
            'keywords': mesh_terms,
            'fetched_at': datetime.now().isoformat()
        }
        
        time.sleep(0.34)
        return paper_info
        
    except:
        return None

def fetch_papers_by_topic(topic, papers_per_topic=10):
    print(f"\n{'='*60}")
    print(f"Topic: {topic}")
    print(f"{'='*60}")
    
    pmids = search_pubmed(topic, max_results=papers_per_topic)
    
    if not pmids:
        print("  No papers found\n")
        return []
    
    papers = []
    for i, pmid in enumerate(pmids, 1):
        print(f"  Fetching paper {i}/{len(pmids)} (PMID: {pmid})...")
        paper = fetch_paper_details(pmid)
        
        if paper is not None:
            paper['search_topic'] = topic
            papers.append(paper)
            try:
                print(f"    ✓ {paper['title'][:60]}...")
            except:
                print(f"    ✓ Paper fetched")
        else:
            print(f"    ✗ Skipped")
    
    print(f"\n✓ Fetched {len(papers)} papers\n")
    return papers

def main():
    print("\n" + "="*60)
    print("PubMed Research Paper Fetcher")
    print("Elenta Suzan Jacob - Fitness Chatbot Project")
    print("="*60)
    
    # Connect to database
    print("\nConnecting to database...")
    db = FitFactDB()
    
    all_papers = []
    
    for topic in SEARCH_TOPICS:
        papers = fetch_papers_by_topic(topic, papers_per_topic=10)
        
        # Save each paper to database
        for paper in papers:
            try:
                db.save_paper(
                    pmid=paper['pmid'],
                    title=paper['title'],
                    abstract=paper['abstract'],
                    authors=paper['authors'],
                    pub_date=paper['publication_date'],
                    journal=paper['journal'],
                    study_type='Research Article'
                )
            except Exception as e:
                print(f"  ✗ Error saving {paper['pmid']}: {e}")
        
        all_papers.extend(papers)
        print(f"Progress: {len(all_papers)} total papers fetched and saved\n")
    
    # Also save to JSON as backup
    output_file = "data/pubmed_papers.json"
    os.makedirs("data", exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_papers, f, indent=2, ensure_ascii=False)
    
    print("\n" + "="*60)
    print("COMPLETE!")
    print("="*60)
    print(f"✓ Total papers: {len(all_papers)}")
    print(f"✓ Saved to database AND {output_file}")
    print("="*60)
    
    db.close()

if __name__ == "__main__":
    main()