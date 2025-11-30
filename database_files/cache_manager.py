import hashlib
import re
from typing import Dict, Optional, List

class CacheManager:
    def __init__(self, db_connection):
        self.db = db_connection
        
    def normalize_query(self, query: str) -> str:
        """Normalize query for better cache matching"""
        # Convert to lowercase
        normalized = query.lower()
        
        # Remove punctuation except spaces
        normalized = re.sub(r'[^\w\s]', '', normalized)
        
        # Remove common stop words
        stop_words = {'what', 'is', 'the', 'of', 'for', 'and', 'a', 'an', 'to', 'in', 'are', 'how'}
        words = normalized.split()
        words = [w for w in words if w not in stop_words]
        
        # Sort words for consistent ordering
        words.sort()
        
        return ' '.join(words)
    
    def apply_synonyms(self, query: str) -> str:
        """Replace terms with normalized synonyms"""
        synonym_map = {
            'whey': 'protein',
            'creatine monohydrate': 'creatine',
            'hiit': 'high intensity interval training',
            'weights': 'resistance training',
            'cardio': 'cardiovascular exercise',
            'supplements': 'supplementation',
            'muscle': 'muscles',
            'strength': 'strength training'
        }
        
        result = query.lower()
        for original, normalized in synonym_map.items():
            result = result.replace(original, normalized)
        
        return result
    
    def calculate_query_hash(self, normalized_query: str) -> str:
        """Generate hash for exact duplicate detection"""
        return hashlib.md5(normalized_query.encode()).hexdigest()
    
    def smart_cache_lookup(self, query: str, threshold: float = 0.7) -> Optional[Dict]:
        """Enhanced cache lookup with normalization"""
        # Step 1: Normalize the query
        normalized = self.normalize_query(query)
        normalized_with_synonyms = self.apply_synonyms(normalized)
        query_hash = self.calculate_query_hash(normalized_with_synonyms)
        
        # Step 2: Check for exact match first (fastest)
        self.db.cursor.execute("""
            SELECT cr.response_id, cr.response_text, 1.0 as similarity
            FROM user_queries uq
            JOIN cached_responses cr ON uq.query_id = cr.query_id
            WHERE uq.query_hash = %s
            LIMIT 1
        """, (query_hash,))
        
        exact_match = self.db.cursor.fetchone()
        if exact_match:
            print(f" Exact cache match found!")
            return exact_match
        
        # Step 3: Fuzzy match on normalized text
        self.db.cursor.execute("""
            SELECT cr.response_id, cr.response_text, 
                   similarity(uq.normalized_text, %s) as similarity
            FROM user_queries uq
            JOIN cached_responses cr ON uq.query_id = cr.query_id
            WHERE similarity(uq.normalized_text, %s) > %s
            ORDER BY similarity DESC
            LIMIT 1
        """, (normalized_with_synonyms, normalized_with_synonyms, threshold))
        
        fuzzy_match = self.db.cursor.fetchone()
        if fuzzy_match:
            print(f" Fuzzy cache match: {fuzzy_match['similarity']:.2%} similarity")
            # Update times_served counter
            self.db.cursor.execute("""
                UPDATE cached_responses 
                SET times_served = times_served + 1,
                    last_served = CURRENT_TIMESTAMP
                WHERE response_id = %s
            """, (fuzzy_match['response_id'],))
            self.db.conn.commit()
            return fuzzy_match
        
        print(f" No cache match found for: {query}")
        return None
    
    def store_in_cache(self, query: str, response: str, papers_used: List[int]) -> int:
        """Store a new response in cache with proper normalization"""
        normalized = self.normalize_query(query)
        normalized_with_synonyms = self.apply_synonyms(normalized)
        query_hash = self.calculate_query_hash(normalized_with_synonyms)
        
        # Insert query
        self.db.cursor.execute("""
            INSERT INTO user_queries 
            (query_text, normalized_text, query_hash, cache_hit, timestamp)
            VALUES (%s, %s, %s, false, CURRENT_TIMESTAMP)
            RETURNING query_id
        """, (query, normalized_with_synonyms, query_hash))
        
        query_id = self.db.cursor.fetchone()['query_id']
        
        # Insert response
        response_hash = hashlib.md5(response.encode()).hexdigest()
        self.db.cursor.execute("""
            INSERT INTO cached_responses
            (query_id, response_text, response_hash, timestamp)
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
            RETURNING response_id
        """, (query_id, response, response_hash))
        
        response_id = self.db.cursor.fetchone()['response_id']
        
        # Link to papers
        for order, paper_id in enumerate(papers_used[:5], 1):
            self.db.cursor.execute("""
                INSERT INTO response_citations
                (response_id, paper_id, citation_order, relevance_rank)
                VALUES (%s, %s, %s, %s)
            """, (response_id, paper_id, order, order))
        
        self.db.conn.commit()
        print(f" Cached response #{response_id} with {len(papers_used)} citations")
        return response_id

# Test the cache manager
if __name__ == "__main__":
    from database import FitFactDB
    
    db = FitFactDB()
    cache = CacheManager(db)
    
    # Test normalization
    test_queries = [
        "What are the benefits of creatine?",
        "benefits of creatine???",
        "creatine benefits",
        "What is HIIT good for?",
        "high intensity interval training benefits"
    ]
    
    print("Testing Query Normalization:")
    for q in test_queries:
        normalized = cache.normalize_query(q)
        with_synonyms = cache.apply_synonyms(normalized)
        print(f"Original: '{q}'")
        print(f"Normal:   '{normalized}'")
        print(f"Synonyms: '{with_synonyms}'")
        print(f"Hash:     {cache.calculate_query_hash(with_synonyms)[:8]}...")
        print()
    
    # Test smart lookup
    print("\nTesting Smart Cache Lookup:")
    result = cache.smart_cache_lookup("benefits of creatine for muscles!!!")
    if result:
        print(f"Found: {result['response_text'][:100]}...")
    
    db.close()