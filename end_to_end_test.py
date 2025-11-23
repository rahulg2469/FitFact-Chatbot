"""
End-to-End Integration Test for FitFact
Week 2 - Test complete pipeline: Question → Keywords → PubMed → Claude → Response
Author: Satya (completing Rahul's tasks)
"""

import os
import json
import time
from datetime import datetime
from dotenv import load_dotenv
from typing import List, Dict

# Import our modules
from keyword_extractor import FitnessKeywordExtractor
from claude_files.claude_api import ClaudeProcessor

# Import team modules from database_files folder
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'database_files'))
from database import FitFactDB
from cache_manager import CacheManager

load_dotenv()

class FitFactIntegration:
    """Complete integration of all FitFact components"""
    
    def __init__(self):
        self.db = FitFactDB()
        self.cache = CacheManager(self.db)
        self.keyword_extractor = FitnessKeywordExtractor()
        self.claude = ClaudeProcessor()
        
        # Track metrics
        self.metrics = {
            'total_time': 0,
            'cache_time': 0,
            'keyword_time': 0,
            'claude_time': 0,
            'cache_hit': False
        }
    
    def process_query(self, user_query: str) -> Dict:
        """
        Process a user query through the complete pipeline
        
        Args:
            user_query: User's fitness question
            
        Returns:
            Dict with response and metrics
        """
        print(f"\n🚀 Processing Query: {user_query}")
        print("=" * 70)
        
        start_time = time.time()
        
        # Step 1: Extract keywords
        print("\n1️⃣ EXTRACTING KEYWORDS...")
        keyword_start = time.time()
        keywords = self.keyword_extractor.extract_keywords(user_query)
        self.metrics['keyword_time'] = time.time() - keyword_start
        
        print(f"   Keywords: {', '.join(keywords['all_keywords'][:5])}")
        print(f"   Search query: {keywords['search_query']}")
        print(f"   Time: {self.metrics['keyword_time']:.2f}s")
        
        # Step 2: Check cache
        print("\n2️⃣ CHECKING CACHE...")
        cache_start = time.time()
        cached_response = self.cache.smart_cache_lookup(user_query, threshold=0.7)
        self.metrics['cache_time'] = time.time() - cache_start
        
        if cached_response:
            self.metrics['cache_hit'] = True
            self.metrics['total_time'] = time.time() - start_time
            
            print(f"   ✅ Cache HIT! (similarity: {cached_response['similarity']:.2%})")
            print(f"   Time: {self.metrics['cache_time']:.2f}s")
            
            return {
                'response': cached_response['response_text'],
                'cache_hit': True,
                'metrics': self.metrics,
                'keywords': keywords
            }
        
        print(f"   ❌ Cache MISS")
        print(f"   Time: {self.metrics['cache_time']:.2f}s")
        
        # Step 3: Fetch papers (simulated for now)
        print("\n3️⃣ FETCHING PAPERS...")
        papers = self._fetch_papers_simulation(keywords['search_query'])
        print(f"   Papers found: {len(papers)}")
        
        # Step 4: Generate response with Claude
        print("\n4️⃣ GENERATING RESPONSE WITH CLAUDE...")
        claude_start = time.time()
        claude_response = self.claude.generate_response(papers, user_query)
        self.metrics['claude_time'] = time.time() - claude_start
        
        if not claude_response['success']:
            return {
                'response': "Sorry, I couldn't generate a response at this time.",
                'error': claude_response.get('error'),
                'metrics': self.metrics
            }
        
        print(f"   ✅ Response generated")
        print(f"   Citations found: {claude_response['citations_found']}")
        print(f"   Tokens used: {claude_response['tokens_used']['input']} in, {claude_response['tokens_used']['output']} out")
        print(f"   Time: {self.metrics['claude_time']:.2f}s")
        
        # Step 5: Validate response
        print("\n5️⃣ VALIDATING RESPONSE...")
        validation = self.claude.validate_response(claude_response)
        if validation['valid']:
            print(f"   ✅ Response valid")
        else:
            print(f"   ⚠️ Issues found: {', '.join(validation['issues'])}")
        
        # Step 6: Store in cache
        print("\n6️⃣ STORING IN CACHE...")
        paper_ids = self._store_papers_in_db(papers)
        cache_id = self.cache.store_in_cache(
            user_query, 
            claude_response['text'], 
            paper_ids
        )
        print(f"   ✅ Cached as ID: {cache_id}")
        
        # Calculate total time
        self.metrics['total_time'] = time.time() - start_time
        
        return {
            'response': claude_response['text'],
            'cache_hit': False,
            'metrics': self.metrics,
            'keywords': keywords,
            'validation': validation,
            'papers_used': len(papers)
        }
    
    def _fetch_papers_simulation(self, search_query: str) -> List[Dict]:
        """
        Simulate fetching papers (use sample data for testing)
        In production, this would call pubmed_fetcher
        """
        # Check if we have sample data
        sample_file = 'data/pubmed_papers_sample.json'
        if os.path.exists(sample_file):
            with open(sample_file, 'r') as f:
                papers = json.load(f)
                # Filter papers based on keywords (simple matching)
                relevant_papers = []
                search_terms = search_query.lower().split()
                for paper in papers:
                    title_abstract = f"{paper.get('title', '')} {paper.get('abstract', '')}".lower()
                    if any(term in title_abstract for term in search_terms):
                        relevant_papers.append(paper)
                return relevant_papers[:5]  # Return top 5
        
        # Fallback mock data
        return [
            {
                'pmid': '12345678',
                'title': f'Study on {search_query}',
                'abstract': f'This study examined the effects of {search_query} on fitness outcomes...',
                'authors': ['Smith J', 'Doe A'],
                'publication_date': '2023-01-01',
                'journal': 'Journal of Exercise Science',
                'keywords': search_query.split()
            }
        ]
    
    def _store_papers_in_db(self, papers: List[Dict]) -> List[int]:
        """Store papers in database and return IDs"""
        paper_ids = []
        for paper in papers:
            try:
                paper_id = self.db.save_paper(
                    pmid=paper.get('pmid', 'UNKNOWN'),
                    title=paper.get('title', ''),
                    abstract=paper.get('abstract', ''),
                    authors=str(paper.get('authors', [])),
                    pub_date=paper.get('publication_date', datetime.now().date()),
                    journal=paper.get('journal', ''),
                    study_type=paper.get('study_type', 'research')
                )
                paper_ids.append(paper_id)
            except:
                continue
        return paper_ids
    
    def print_metrics_summary(self):
        """Print a summary of performance metrics"""
        print("\n📊 PERFORMANCE METRICS")
        print("=" * 70)
        print(f"Total Time: {self.metrics['total_time']:.2f}s")
        print(f"  - Keyword Extraction: {self.metrics['keyword_time']:.2f}s")
        print(f"  - Cache Lookup: {self.metrics['cache_time']:.2f}s")
        if not self.metrics['cache_hit']:
            print(f"  - Claude Generation: {self.metrics['claude_time']:.2f}s")
        print(f"Cache Hit: {'Yes ✅' if self.metrics['cache_hit'] else 'No ❌'}")

def test_end_to_end():
    """Run end-to-end integration tests"""
    
    print("\n" + "=" * 70)
    print("🧪 FITFACT END-TO-END INTEGRATION TEST")
    print("=" * 70)
    
    integration = FitFactIntegration()
    
    test_queries = [
        "What are the benefits of creatine for muscle growth?",
        "How much protein should I eat after a workout?",
        "Is HIIT better than steady cardio for fat loss?"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n\n{'🔵' * 35}")
        print(f"TEST {i} OF {len(test_queries)}")
        print(f"{'🔵' * 35}")
        
        result = integration.process_query(query)
        
        print("\n📝 RESPONSE:")
        print("-" * 70)
        print(result['response'][:500] + "..." if len(result['response']) > 500 else result['response'])
        
        integration.print_metrics_summary()
        
        # Test cache on second run of same query
        if i == 1:
            print("\n\n🔄 TESTING CACHE WITH SAME QUERY...")
            result2 = integration.process_query(query)
            if result2['cache_hit']:
                print("✅ Cache working correctly!")
            integration.print_metrics_summary()
    
    # Close database connection
    integration.db.close()
    
    print("\n" + "=" * 70)
    print("✅ END-TO-END INTEGRATION TEST COMPLETE!")
    print("=" * 70)

if __name__ == "__main__":
    test_end_to_end()