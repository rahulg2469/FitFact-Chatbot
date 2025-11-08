"""
Test PubMed API connection
Goal: Fetch 5 papers about "creatine supplementation"
"""

from Bio import Entrez
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set your email (required by NCBI)
Entrez.email = os.getenv('PUBMED_EMAIL')
Entrez.api_key = os.getenv('PUBMED_API_KEY')

def search_pubmed(query, max_results=5):
    """Search PubMed and return PMIDs"""
    print(f"Searching PubMed for: {query}")
    
    try:
        handle = Entrez.esearch(
            db="pubmed",
            term=query,
            retmax=max_results,
            sort="relevance"
        )
        
        record = Entrez.read(handle)
        handle.close()
        
        pmids = record["IdList"]
        print(f"✓ Found {len(pmids)} papers")
        return pmids
    except Exception as e:
        print(f"✗ Error: {e}")
        return []

def fetch_paper_details(pmid):
    """Fetch details for a specific PMID"""
    print(f"\nFetching details for PMID: {pmid}")
    
    try:
        handle = Entrez.efetch(
            db="pubmed",
            id=pmid,
            rettype="abstract",
            retmode="xml"
        )
        
        records = Entrez.read(handle)
        handle.close()
        
        # Extract basic info
        article = records['PubmedArticle'][0]['MedlineCitation']['Article']
        
        paper_info = {
            'pmid': pmid,
            'title': article['ArticleTitle'],
            'abstract': article.get('Abstract', {}).get('AbstractText', ['No abstract'])[0] if 'Abstract' in article else 'No abstract',
            'journal': article['Journal']['Title'],
        }
        
        return paper_info
    except Exception as e:
        print(f"✗ Error fetching paper: {e}")
        return None

if __name__ == "__main__":
    # Test the API
    print("=" * 60)
    print("🧪 PubMed API Test - Elenta's Setup Verification")
    print("=" * 60)
    
    # Check if credentials are loaded
    api_key = os.getenv('PUBMED_API_KEY')
    email = os.getenv('PUBMED_EMAIL')
    
    if not api_key or not email:
        print("\n✗ ERROR: API key or email not found in .env file!")
        print("Please check your .env file and make sure it contains:")
        print("  PUBMED_API_KEY=your_key")
        print("  PUBMED_EMAIL=your_email@northeastern.edu")
        exit(1)
    
    print(f"✓ API Key loaded: {api_key[:10]}...")
    print(f"✓ Email loaded: {email}")
    
    # Search for papers
    pmids = search_pubmed("resistance training muscle hypertrophy", max_results=3)
    
    # Fetch details for first paper
    if pmids:
        print("\n" + "=" * 60)
        print("📄 Sample Paper Details:")
        print("=" * 60)
        paper = fetch_paper_details(pmids[0])
        
        if paper:
            print(f"\nTitle: {paper['title']}")
            print(f"Journal: {paper['journal']}")
            print(f"PMID: {paper['pmid']}")
            print(f"\nAbstract preview: {str(paper['abstract'])[:200]}...")
            print("\n" + "=" * 60)
            print("🎉 SUCCESS! Your PubMed API is working perfectly!")
            print("=" * 60)
        else:
            print("✗ Could not fetch paper details")
    else:
        print("\n✗ No papers found or API error occurred")
        print("Check your API key and internet connection")