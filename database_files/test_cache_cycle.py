from database import FitFactDB
from cache_manager import CacheManager

def test_cache_storage_and_retrieval():
    """Test storing and retrieving from cache"""
    db = FitFactDB()
    cache = CacheManager(db)
    
    print("🧪 Testing Complete Cache Cycle\n")
    
    # 1. Store a response
    print("1️⃣ Storing new response in cache...")
    test_query = "What are the benefits of creatine for muscle growth?"
    test_response = """Based on meta-analysis research, creatine supplementation 
    has been shown to increase muscle strength by 5-15%, improve high-intensity 
    exercise performance, and accelerate muscle recovery. Studies consistently 
    show gains in lean muscle mass when combined with resistance training."""
    
    # Use the paper IDs we already have in database
    paper_ids = [1, 2]  # From our test data
    
    response_id = cache.store_in_cache(test_query, test_response, paper_ids)
    
    # 2. Test exact match
    print("\n2️⃣ Testing exact match lookup...")
    result = cache.smart_cache_lookup("What are the benefits of creatine for muscle growth?")
    assert result is not None, "Should find exact match"
    
    # 3. Test variations (should all match due to normalization)
    print("\n3️⃣ Testing normalized variations...")
    variations = [
        "benefits of creatine for muscles",
        "creatine benefits muscle growth",
        "muscle growth creatine benefits"
    ]
    
    for query in variations:
        print(f"\nTrying: '{query}'")
        result = cache.smart_cache_lookup(query, threshold=0.6)
        if result:
            print(f"✓ Match found (similarity: {result['similarity']:.2%})")
        else:
            print("✗ No match")
    
    # 4. Test cache statistics
    print("\n4️⃣ Cache Statistics:")
    db.cursor.execute("""
        SELECT 
            COUNT(DISTINCT uq.query_id) as unique_queries,
            COUNT(DISTINCT cr.response_id) as cached_responses,
            AVG(cr.times_served) as avg_times_served,
            MAX(cr.times_served) as max_times_served
        FROM user_queries uq
        JOIN cached_responses cr ON uq.query_id = cr.query_id
    """)
    stats = db.cursor.fetchone()
    print(f"Unique queries: {stats['unique_queries']}")
    print(f"Cached responses: {stats['cached_responses']}")
    print(f"Avg times served: {stats['avg_times_served']:.1f}")
    print(f"Max times served: {stats['max_times_served']}")
    
    db.close()
    print("\n✅ Cache cycle test complete!")

if __name__ == "__main__":
    test_cache_storage_and_retrieval()