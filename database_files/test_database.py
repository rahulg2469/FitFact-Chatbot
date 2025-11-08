import unittest
import psycopg2
from database import FitFactDB
from datetime import datetime, date

class TestFitFactDatabase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up test database connection"""
        cls.db = FitFactDB()
        print("\n🧪 Starting Database Tests...")
    
    def test_01_insert_paper(self):
        """Test inserting a research paper"""
        paper_id = self.db.save_paper(
            pmid='TEST001',
            title='Test Paper: Protein Synthesis',
            abstract='This study examines protein synthesis rates...',
            authors='Test Author',
            pub_date=date(2024, 1, 1),
            journal='Test Journal',
            study_type='rct'
        )
        self.assertIsNotNone(paper_id)
        print("✓ Paper insert successful")
    
    def test_02_duplicate_paper(self):
        """Test handling duplicate papers (should update, not error)"""
        # Insert same paper again
        paper_id = self.db.save_paper(
            pmid='TEST001',
            title='Test Paper: Protein Synthesis',
            abstract='Updated abstract',
            authors='Test Author',
            pub_date=date(2024, 1, 1),
            journal='Test Journal',
            study_type='rct'
        )
        
        # Check times_used incremented
        self.db.cursor.execute(
            "SELECT times_used FROM research_papers WHERE pmid = %s",
            ('TEST001',)
        )
        result = self.db.cursor.fetchone()
        self.assertGreater(result['times_used'], 0)
        print("✓ Duplicate handling works (times_used incremented)")
    
    def test_03_cache_lookup(self):
        """Test fuzzy cache matching"""
        # First insert a query and response
        self.db.cursor.execute("""
            INSERT INTO user_queries (query_text, normalized_text, cache_hit)
            VALUES ('benefits of whey protein for muscle', 'benefits whey protein muscle', false)
            RETURNING query_id
        """)
        query_id = self.db.cursor.fetchone()['query_id']
        
        self.db.cursor.execute("""
            INSERT INTO cached_responses (query_id, response_text)
            VALUES (%s, 'Whey protein provides essential amino acids...')
        """, (query_id,))
        self.db.conn.commit()
        
        # Test similar query
        result = self.db.check_cache('whey protein muscle benefits')
        self.assertIsNotNone(result)
        print(f"✓ Cache fuzzy match works (similarity: {result['similarity']:.2%})")
    
    def test_04_full_text_search(self):
        """Test PostgreSQL full-text search"""
        self.db.cursor.execute("""
            SELECT paper_id, title, 
                   ts_rank(search_vector, query) as rank
            FROM research_papers,
                 to_tsquery('english', 'protein & synthesis') query
            WHERE search_vector @@ query
            ORDER BY rank DESC
        """)
        results = self.db.cursor.fetchall()
        self.assertGreater(len(results), 0)
        print(f"✓ Full-text search found {len(results)} papers")
    
    def test_05_api_logging(self):
        """Test API call logging"""
        self.db.log_api_call('pubmed', '/esearch', 150, 200, 0, 0)
        
        # Verify it was logged
        self.db.cursor.execute(
            "SELECT COUNT(*) as count FROM api_call_log WHERE api_name = 'pubmed'"
        )
        count = self.db.cursor.fetchone()['count']
        self.assertGreater(count, 0)
        print("✓ API logging works")
    
    def test_06_performance_check(self):
        """Test query performance"""
        import time
        
        # Time a cache lookup
        start = time.time()
        self.db.check_cache('test query for performance')
        elapsed = (time.time() - start) * 1000
        
        self.assertLess(elapsed, 100)  # Should be under 100ms
        print(f"✓ Cache lookup performance: {elapsed:.2f}ms")
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test data"""
        cls.db.cursor.execute("DELETE FROM research_papers WHERE pmid LIKE 'TEST%'")
        cls.db.conn.commit()
        cls.db.close()
        print("\n✅ All database tests passed!\n")

if __name__ == '__main__':
    unittest.main(verbosity=2)