from database import FitFactDB
from cache_manager import CacheManager
from datetime import datetime, timedelta

class AutoCacheManager:
    def __init__(self, db_connection):
        self.db = db_connection
        self.cache = CacheManager(db_connection)
        
    def check_auto_cache_eligibility(self):
        """Find papers that should be auto-cached based on usage"""
        self.db.cursor.execute("""
            SELECT paper_id, pmid, title, times_used
            FROM research_papers
            WHERE times_used >= 20
            AND paper_id NOT IN (
                SELECT DISTINCT paper_id 
                FROM response_citations
            )
            ORDER BY times_used DESC
            LIMIT 10
        """)
        return self.db.cursor.fetchall()
    
    def trigger_auto_cache(self, paper_id: int):
        """Auto-generate and cache a response for frequently accessed paper"""
        print(f"🤖 Auto-caching paper #{paper_id}")
        
        # Get paper details
        self.db.cursor.execute("""
            SELECT title, abstract, pmid 
            FROM research_papers 
            WHERE paper_id = %s
        """, (paper_id,))
        paper = self.db.cursor.fetchone()
        
        if paper:
            # Generate a standard query for this paper
            auto_query = f"What does research say about {paper['title'].lower()}"
            
            # Create auto-response (in production, Claude would generate this)
            auto_response = f"""Based on research (PMID: {paper['pmid']}), 
            this study examined {paper['title']}. The findings suggest that 
            {paper['abstract'][:200]}... This research provides evidence for 
            the effectiveness of the intervention studied."""
            
            # Store in cache
            self.cache.store_in_cache(auto_query, auto_response, [paper_id])
            return True
        return False
    
    def evict_stale_cache(self, days_old: int = 50):
        """Remove old cached responses and unused papers"""
        cutoff_date = datetime.now() - timedelta(days=days_old)
        
        # Find stale cached responses
        self.db.cursor.execute("""
            SELECT response_id, query_id
            FROM cached_responses
            WHERE last_served < %s
            AND times_served < 5
        """, (cutoff_date,))
        
        stale_responses = self.db.cursor.fetchall()
        
        if stale_responses:
            # Delete stale responses
            response_ids = [r['response_id'] for r in stale_responses]
            self.db.cursor.execute("""
                DELETE FROM cached_responses
                WHERE response_id = ANY(%s)
            """, (response_ids,))
            
            print(f"🗑️ Evicted {len(response_ids)} stale cached responses")
        
        # Clean up unused papers - with the parameter
        self.db.cursor.execute("""
            DELETE FROM research_papers
            WHERE last_accessed < %s
            AND times_used < 10
            AND paper_id NOT IN (
                SELECT DISTINCT paper_id FROM response_citations
            )
            RETURNING paper_id
        """, (cutoff_date,))
        
        deleted_papers = self.db.cursor.fetchall()
        if deleted_papers:
            print(f"🗑️ Removed {len(deleted_papers)} unused papers")
        
        self.db.conn.commit()
        return len(stale_responses) if stale_responses else 0, len(deleted_papers)
    
    def optimize_cache_performance(self):
        """Analyze and optimize cache performance"""
        # Get cache metrics
        self.db.cursor.execute("""
            WITH cache_stats AS (
                SELECT 
                    COUNT(CASE WHEN cache_hit THEN 1 END)::float / 
                    NULLIF(COUNT(*), 0) * 100 as hit_rate,
                    AVG(response_time_ms) as avg_response_time,
                    COUNT(*) as total_queries
                FROM user_queries
                WHERE timestamp > CURRENT_TIMESTAMP - INTERVAL '7 days'
            ),
            popular_misses AS (
                SELECT normalized_text, COUNT(*) as miss_count
                FROM user_queries
                WHERE cache_hit = false
                AND timestamp > CURRENT_TIMESTAMP - INTERVAL '7 days'
                GROUP BY normalized_text
                HAVING COUNT(*) > 2
                ORDER BY COUNT(*) DESC
                LIMIT 5
            )
            SELECT * FROM cache_stats, popular_misses
        """)
        
        results = self.db.cursor.fetchall()
        
        print("\n📊 Cache Performance Analysis")
        print("="*50)
        
        if results and results[0]['hit_rate'] is not None:
            print(f"7-day cache hit rate: {results[0]['hit_rate']:.1f}%")
            print(f"Avg response time: {results[0]['avg_response_time']:.0f}ms")
            print(f"Total queries: {results[0]['total_queries']}")
            
            print("\n🎯 Top Missed Queries (candidates for caching):")
            for r in results:
                if r['normalized_text']:
                    print(f"  - '{r['normalized_text']}' (missed {r['miss_count']} times)")
        
        # Suggest optimizations
        if results and results[0]['hit_rate'] and results[0]['hit_rate'] < 60:
            print("\n⚠️ Recommendations:")
            print("  - Cache hit rate below 60% target")
            print("  - Consider pre-caching popular queries")
            print("  - Review synonym mappings")
        
        return results

# Test the auto-cache manager
if __name__ == "__main__":
    db = FitFactDB()
    auto_manager = AutoCacheManager(db)
    
    print("🔄 Auto-Cache Manager Test\n")
    
    # Check for auto-cache candidates
    print("1️⃣ Checking auto-cache candidates...")
    candidates = auto_manager.check_auto_cache_eligibility()
    if candidates:
        for paper in candidates:
            print(f"  - Paper #{paper['paper_id']}: {paper['title'][:50]}... (used {paper['times_used']} times)")
    else:
        print("  No papers meet auto-cache threshold yet")
    
    # Simulate increasing usage to trigger auto-cache
    print("\n2️⃣ Simulating high usage...")
    for _ in range(20):
        db.cursor.execute("""
            UPDATE research_papers 
            SET times_used = times_used + 1 
            WHERE paper_id = 1
        """)
    db.conn.commit()
    
    # Check again
    candidates = auto_manager.check_auto_cache_eligibility()
    if candidates:
        print(f"  Paper now eligible for auto-caching!")
        auto_manager.trigger_auto_cache(candidates[0]['paper_id'])
    
    # Test cache optimization
    print("\n3️⃣ Running cache optimization analysis...")
    auto_manager.optimize_cache_performance()
    
    # Test eviction (won't delete anything in test since all data is recent)
    print("\n4️⃣ Testing cache eviction...")
    stale, unused = auto_manager.evict_stale_cache(days_old=1000)  # Far future for testing
    print(f"  Would evict: {stale} responses, {unused} papers")
    
    db.close()