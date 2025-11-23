import time
import sys
import os

# Add database_files to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'database_files'))

from database import FitFactDB
from claude_files.claude_api import ClaudeProcessor  # Updated path for Claude
import pubmed_fetcher  # Import the module instead
from dotenv import load_dotenv

load_dotenv()

class FitFactPipeline:
    def __init__(self):
        self.db = FitFactDB()
        self.claude = ClaudeProcessor()
        
    def process_query(self, user_query):
        """Main pipeline: Cache → PubMed → Claude → Store"""
        start_time = time.time()
        
        # 1. Check cache first (Satya's part)
        print(f"\n🔍 Query: {user_query}")
        cached = self.db.check_cache(user_query)
        
        if cached and cached['similarity'] > 0.7:
            # Cache hit - return immediately
            response_time = int((time.time() - start_time) * 1000)
            self.db.log_query(user_query, cache_hit=True, response_time_ms=response_time)
            print("✅ Cache hit!")
            return cached['response_text']
        
        # 2. Cache miss - fetch papers (Elenta's part)
        print("🔎 Fetching papers from PubMed...")
        # Use the fetch_papers_by_topic function from pubmed_fetcher
        papers = pubmed_fetcher.fetch_papers_by_topic(user_query, papers_per_topic=5)
        
        if not papers:
            # Try a simpler search
            pmids = pubmed_fetcher.search_pubmed(user_query, max_results=5)
            papers = []
            for pmid in pmids:
                paper = pubmed_fetcher.fetch_paper_details(pmid)
                if paper:
                    papers.append(paper)
        
        if not papers:
            return "Sorry, couldn't find relevant research on this topic."
        
        # 3. Store papers in database
        paper_ids = []
        for paper in papers:
            # Handle the date format from pubmed_fetcher
            pub_date = paper.get('publication_date', '2024-01-01')
            
            paper_id = self.db.save_paper(
                pmid=paper['pmid'],
                title=paper['title'],
                abstract=paper['abstract'],
                authors=str(paper.get('authors', [])),  # Convert list to string
                pub_date=pub_date,
                journal=paper.get('journal', 'Unknown'),
                study_type='research'
            )
            paper_ids.append(paper_id)
        
        # 4. Generate response with Claude (Rahul's part)
        print("🤖 Generating response with Claude...")
        response = self.claude.generate_response(papers, user_query)
        
        # 5. Store response and citations
        response_id = self.db.save_response(user_query, response['text'])
        for i, paper_id in enumerate(paper_ids[:3]):  # Top 3 papers as citations
            self.db.save_citation(response_id, paper_id, order=i+1)
        
        # 6. Log metrics
        response_time = int((time.time() - start_time) * 1000)
        self.db.log_query(user_query, cache_hit=False, response_time_ms=response_time)
        
        return response['text']

if __name__ == "__main__":
    pipeline = FitFactPipeline()
    
    # Test query
    test_query = "What are the benefits of creatine for muscle growth?"
    response = pipeline.process_query(test_query)
    print(f"\n✅ Response:\n{response}")