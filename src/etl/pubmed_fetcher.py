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

# Load environment variables
load_dotenv()

# API credentials
PUBMED_API_KEY = os.getenv('PUBMED_API_KEY')
PUBMED_EMAIL = os.getenv('PUBMED_EMAIL')

# Base URLs
ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

# Fitness topics to search
SEARCH_TOPICS = [
    "resistance training muscle hypertrophy",
    "cardiovascular exercise fitness",
    "protein supplementation muscle",
    "creatine supplementation performance",
    "HIIT high intensity interval training"
]

def search_pubmed(query, max_results=10):
    """Search PubMed for papers using XML"""
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
        
        # DEBUG: Print first 500 characters of response
        print(f"  DEBUG: Response preview: {response.text[:500]}")
        
        # Parse XML
        root = ET.fromstring(response.content)
        id_list = root.find('.//IdList')
        
        if id_list is None:
            print(f"  ✗ No IdList found")
            return []
        
        pmids = [id_elem.text for id_elem in id_list.findall('Id')]
        print(f"  ✓ Found {len(pmids)} papers")
        
        time.sleep(0.34)
        return pmids
        
    except Exception as e:
        print(f"  ✗ Error searching: {e}")
        print(f"  Response status: {response.status_code}")
        print(f"  Response text: {response.text[:1000]}")
        return []

def fetch_paper_details(pmid):
    """Fetch detailed information for a paper"""
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
        
        # Extract article data
        article = root.find('.//Article')
        if article is None:
            return None
        
        # Get title
        title_elem = article.find('.//ArticleTitle')
        title = title_elem.text if title_elem is not None else "No title"
        
        # Get abstract
        abstract_parts = article.findall('.//AbstractText')
        abstract = " ".join([part.text or "" for part in abstract_parts]) if abstract_parts else "No abstract available"
        
        # Get journal
        journal_elem = article.find('.//Journal/Title')
        journal = journal_elem.text if journal_elem is not None else "Unknown journal"
        
        # Get publication date
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
        
        # Get authors
        authors = []
        author_list = article.findall('.//Author')
        for author in author_list[:3]:
            lastname = author.find('LastName')
            initials = author.find('Initials')
            if lastname is not None and initials is not None:
                authors.append(f"{lastname.text} {initials.text}")
        
        # Get MeSH terms
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
        
    except Exception as e:
        print(f"  ✗ Error fetching PMID {pmid}: {e}")
        return None

def fetch_papers_by_topic(topic, papers_per_topic=10):
    """Fetch papers for a specific topic"""
    print(f"\n{'='*60}")
    print(f"Topic: {topic}")
    print(f"{'='*60}")
    
    pmids = search_pubmed(topic, max_results=papers_per_topic)
    
    if not pmids:
        print("  No papers found for this topic\n")
        return []
    
    papers = []
    for i, pmid in enumerate(pmids, 1):
        print(f"  Fetching paper {i}/{len(pmids)} (PMID: {pmid})...")
        paper = fetch_paper_details(pmid)
        
        if paper:
            paper['search_topic'] = topic
            papers.append(paper)
            print(f"    ✓ {paper['title'][:60]}...")
    
    print(f"\n✓ Successfully fetched {len(papers)} papers for this topic\n")
    return papers

def main():
    """Main function to fetch papers across all topics"""
    print("\n" + "="*60)
    print("PubMed Research Paper Fetcher")
    print("Elenta Suzan Jacob - Fitness Chatbot Project")
    print("="*60)
    
    all_papers = []
    
    for topic in SEARCH_TOPICS:
        papers = fetch_papers_by_topic(topic, papers_per_topic=10)
        all_papers.extend(papers)
        print(f"Progress: {len(all_papers)} total papers fetched so far\n")
    
    output_file = "data/pubmed_papers.json"
    os.makedirs("data", exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_papers, f, indent=2, ensure_ascii=False)
    
    print("\n" + "="*60)
    print("FETCH COMPLETE!")
    print("="*60)
    print(f"✓ Total papers fetched: {len(all_papers)}")
    print(f"✓ Topics covered: {len(SEARCH_TOPICS)}")
    print(f"✓ Saved to: {output_file}")
    
    if os.path.exists(output_file):
        print(f"✓ File size: {os.path.getsize(output_file) / 1024:.2f} KB")
    
    print("="*60)
    
    if all_papers:
        print("\n📄 Sample Paper:")
        print(f"Title: {all_papers[0]['title']}")
        print(f"Journal: {all_papers[0]['journal']}")
        print(f"Date: {all_papers[0]['publication_date']}")
        print(f"PMID: {all_papers[0]['pmid']}")

if __name__ == "__main__":
    main()