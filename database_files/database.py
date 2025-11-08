"""
FitFact Database Connection Module
Week 2 - Enhanced with cache and performance features
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

class FitFactDB:
    def __init__(self):
        self.conn = psycopg2.connect(
            dbname=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            host=os.getenv('DB_HOST'),
            port=os.getenv('DB_PORT')
        )
        self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        print("✓ Database connected successfully")
    
    def check_cache(self, query_text):
        """Check if similar query exists in cache"""
        self.cursor.execute(
            "SELECT * FROM find_cached_response(%s)",
            (query_text,)
        )
        result = self.cursor.fetchone()
        if result:
            print(f"✓ Cache hit! Similarity: {result['similarity']:.2%}")
        else:
            print("✗ Cache miss - will need to fetch from PubMed")
        return result
    
    def save_paper(self, pmid, title, abstract, authors, pub_date, journal, study_type):
        """Insert a new paper or update if exists"""
        self.cursor.execute("""
            INSERT INTO research_papers 
            (pmid, title, abstract, authors, publication_date, journal_name, study_type)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (pmid) 
            DO UPDATE SET times_used = research_papers.times_used + 1,
                         last_accessed = CURRENT_TIMESTAMP
            RETURNING paper_id, times_used;
        """, (pmid, title, abstract, authors, pub_date, journal, study_type))
        self.conn.commit()
        result = self.cursor.fetchone()
        print(f"✓ Paper {pmid} saved/updated. Times used: {result['times_used']}")
        return result['paper_id']
    
    def log_api_call(self, api_name, endpoint, response_time_ms, status_code, tokens=0, cost=0):
        """Log API usage for rate limiting"""
        self.cursor.execute("""
            INSERT INTO api_call_log 
            (api_name, endpoint, response_time_ms, status_code, tokens_used, cost_usd)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (api_name, endpoint, response_time_ms, status_code, tokens, cost))
        self.conn.commit()
        print(f"✓ API call logged: {api_name}")
    
    def log_query(self, query_text, cache_hit, response_time_ms):
        """Log user query with metrics"""
        self.cursor.execute("""
            INSERT INTO user_queries (query_text, cache_hit, response_time_ms, timestamp)
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
            RETURNING query_id
        """, (query_text, cache_hit, response_time_ms))
        self.conn.commit()
        return self.cursor.fetchone()['query_id']
    
    def save_response(self, query_text, response_text):
        """Save Claude's response"""
        query_id = self.log_query(query_text, True, 0)
        
        self.cursor.execute("""
            INSERT INTO cached_responses (query_id, response_text, timestamp)
            VALUES (%s, %s, CURRENT_TIMESTAMP)
            RETURNING response_id
        """, (query_id, response_text))
        self.conn.commit()
        return self.cursor.fetchone()['response_id']
    
    def save_citation(self, response_id, paper_id, order):
        """Link response to paper"""
        self.cursor.execute("""
            INSERT INTO response_citations (response_id, paper_id, citation_order, relevance_rank)
            VALUES (%s, %s, %s, %s)
        """, (response_id, paper_id, order, order))
        self.conn.commit()
    
    def batch_insert_papers(self, papers_list):
        """Bulk insert papers from PubMed results"""
        # Implementation for Elenta's integration
        inserted_ids = []
        for paper in papers_list:
            paper_id = self.save_paper(
                paper.get('pmid'),
                paper.get('title'),
                paper.get('abstract'),
                paper.get('authors'),
                paper.get('pub_date'),
                paper.get('journal'),
                paper.get('study_type')
            )
            inserted_ids.append(paper_id)
        return inserted_ids
    
    def get_papers_for_query(self, query_text, limit=10):
        """Get most relevant papers for a query"""
        # Implementation for Rahul's integration
        self.cursor.execute("""
            SELECT paper_id, pmid, title, abstract, quality_score
            FROM research_papers
            WHERE search_vector @@ to_tsquery('english', %s)
            ORDER BY ts_rank(search_vector, to_tsquery('english', %s)) DESC
            LIMIT %s
        """, (query_text, query_text, limit))
        return self.cursor.fetchall()
    
    def get_stats(self):
        """Get database statistics"""
        self.cursor.execute("""
            SELECT 
                (SELECT COUNT(*) FROM research_papers) as papers,
                (SELECT COUNT(*) FROM user_queries) as queries,
                (SELECT COUNT(*) FROM cached_responses) as cached,
                (SELECT cache_hit_rate FROM performance_metrics 
                 WHERE date = CURRENT_DATE) as hit_rate
        """)
        return self.cursor.fetchone()
    
    def close(self):
        self.conn.close()
        print("✓ Database connection closed")

# Test script
if __name__ == "__main__":
    print("Testing FitFact Database Connection...\n")
    
    try:
        db = FitFactDB()
        
        print("1. Testing cache lookup:")
        result = db.check_cache("What are the benefits of creatine?")
        
        print("\n2. Database stats:")
        stats = db.get_stats()
        print(f"   Papers: {stats['papers']}")
        print(f"   Queries: {stats['queries']}")
        print(f"   Cached responses: {stats['cached']}")
        
        print("\n3. Testing API logging:")
        db.log_api_call('pubmed', '/esearch', 150, 200)
        
        print("\n4. Closing connection:")
        db.close()
        
        print("\n✓ All tests passed!")
        
    except Exception as e:
        print(f"✗ Error: {e}")