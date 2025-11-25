"""
Diagnose and fix the FitFact pipeline issues
"""
import sys
import os
from dotenv import load_dotenv

load_dotenv()

print("🔍 DIAGNOSING FITFACT PIPELINE")
print("=" * 70)

# Step 1: Test PubMed API with a query that MUST have results
print("\n1️⃣ Testing PubMed with known good searches...")
from src.etl.pubmed_fetcher import search_pubmed, fetch_paper_details

test_searches = [
    "protein intake fat loss",
    "resistance training frequency",
    "creatine supplementation",
    "high protein diet weight loss"
]

all_papers = []
for search in test_searches:
    print(f"\nSearching: {search}")
    pmids = search_pubmed(search, max_results=3)
    print(f"  Found PMIDs: {pmids}")
    
    if pmids:
        # Fetch first paper details
        paper = fetch_paper_details(pmids[0])
        if paper:
            print(f"  ✅ Paper title: {paper.get('title', 'No title')[:60]}...")
            all_papers.append(paper)
        else:
            print(f"  ❌ Could not fetch details for PMID {pmids[0]}")

print(f"\n📊 Total papers fetched: {len(all_papers)}")

# Step 2: Test database and cache
print("\n2️⃣ Testing Database and Cache...")
sys.path.append('database_files')
from database import FitFactDB
from cache_manager import CacheManager

try:
    db = FitFactDB()
    cache = CacheManager(db)
    print("  ✅ Database connected")
    
    # Check if we have papers in DB
    db.cursor.execute("SELECT COUNT(*) as count FROM research_papers")
    count = db.cursor.fetchone()['count']
    print(f"  📄 Papers in database: {count}")
    
    # Test cache lookup
    test_query = "How much protein for fat loss?"
    cached = cache.smart_cache_lookup(test_query, threshold=0.5)
    if cached:
        print(f"  ✅ Found cached response for test query")
    else:
        print(f"  ℹ️ No cache match for test query (this is OK)")
    
    db.close()
except Exception as e:
    print(f"  ❌ Database error: {e}")

# Step 3: Test keyword extraction
print("\n3️⃣ Testing Keyword Extraction...")
from keyword_extractor import FitnessKeywordExtractor

extractor = FitnessKeywordExtractor()
test_questions = [
    "What's the ideal daily protein intake for fat loss?",
    "How many times should I work out per week?"
]

for question in test_questions:
    keywords = extractor.extract_keywords(question)
    print(f"\n  Question: {question}")
    print(f"  Keywords: {keywords['all_keywords']}")
    print(f"  Search query: {keywords['search_query']}")

# Step 4: Test Claude with real papers
print("\n4️⃣ Testing Claude with Real Papers...")
if all_papers:
    from claude_files.claude_api import ClaudeProcessor
    
    processor = ClaudeProcessor()
    test_question = "What's the ideal daily protein intake for fat loss?"
    
    print(f"  Question: {test_question}")
    print(f"  Using {len(all_papers)} real papers from PubMed")
    
    response = processor.generate_response(all_papers, test_question)
    if response['success']:
        print("  ✅ Claude generated response")
        print(f"  Response preview: {response['text'][:200]}...")
    else:
        print(f"  ❌ Claude error: {response.get('error')}")

# Step 5: Test complete pipeline
print("\n5️⃣ Testing Complete Pipeline Flow...")

def test_full_pipeline(question):
    """Test the complete flow"""
    print(f"\n  Testing: {question}")
    
    # Extract keywords
    keywords = extractor.extract_keywords(question)
    search_query = keywords['search_query']
    print(f"  Search query: {search_query}")
    
    # Search PubMed
    pmids = search_pubmed(search_query, max_results=5)
    print(f"  PMIDs found: {pmids}")
    
    if not pmids:
        # Try alternative search
        alt_search = ' '.join(keywords['all_keywords'][:3])
        print(f"  Trying alternative: {alt_search}")
        pmids = search_pubmed(alt_search, max_results=5)
        print(f"  Alternative PMIDs: {pmids}")
    
    papers = []
    for pmid in pmids[:3]:
        paper = fetch_paper_details(pmid)
        if paper:
            papers.append(paper)
    
    print(f"  Papers fetched: {len(papers)}")
    
    if papers:
        # Generate response
        response = processor.generate_response(papers, question)
        if response['success']:
            print("  ✅ SUCCESS! Response generated")
            return True
        else:
            print(f"  ❌ Claude failed: {response.get('error')}")
            return False
    else:
        print("  ❌ No papers fetched")
        return False

# Test with a real question
success = test_full_pipeline("What's the ideal daily protein intake for fat loss?")

print("\n" + "=" * 70)
if success:
    print("✅ PIPELINE WORKING! The issue might be in Streamlit integration")
else:
    print("❌ Issues found - check the errors above")