from database import FitFactDB
import time

class PerformanceOptimizer:
    def __init__(self, db_connection):
        self.db = db_connection
    
    def analyze_missing_indexes(self):
        """Find queries that could benefit from indexes"""
        print("🔍 Analyzing Index Coverage\n")
        
        # Check existing indexes
        self.db.cursor.execute("""
            SELECT 
                schemaname,
                tablename,
                indexname,
                indexdef
            FROM pg_indexes
            WHERE schemaname = 'public'
            ORDER BY tablename, indexname;
        """)
        
        indexes = self.db.cursor.fetchall()
        print(f"Found {len(indexes)} indexes in database")
        
        # Group by table
        tables = {}
        for idx in indexes:
            table = idx['tablename']
            if table not in tables:
                tables[table] = []
            tables[table].append(idx['indexname'])
        
        # Check for potentially missing indexes
        recommendations = []
        
        # Check user_queries table
        if 'idx_queries_normalized' not in tables.get('user_queries', []):
            recommendations.append(
                "CREATE INDEX idx_queries_normalized ON user_queries(normalized_text);"
            )
        
        # Check cached_responses table  
        if 'idx_responses_timestamp' not in tables.get('cached_responses', []):
            recommendations.append(
                "CREATE INDEX idx_responses_timestamp ON cached_responses(timestamp DESC);"
            )
        
        # Check research_papers for composite index
        if 'idx_papers_quality_used' not in tables.get('research_papers', []):
            recommendations.append(
                "CREATE INDEX idx_papers_quality_used ON research_papers(quality_score DESC, times_used DESC);"
            )
        
        if recommendations:
            print("\n⚡ Recommended Indexes to Add:")
            for rec in recommendations:
                print(f"  {rec}")
        else:
            print("✓ All recommended indexes are present")
        
        return recommendations
    
    def benchmark_queries(self):
        """Benchmark critical queries"""
        print("\n⏱️ Query Performance Benchmarks\n")
        
        benchmarks = {}
        
        # 1. Cache lookup performance
        start = time.time()
        self.db.cursor.execute("""
            SELECT cr.response_text
            FROM user_queries uq
            JOIN cached_responses cr ON uq.query_id = cr.query_id
            WHERE similarity(uq.query_text, 'test query') > 0.5
            LIMIT 1;
        """)
        benchmarks['cache_lookup'] = (time.time() - start) * 1000
        
        # 2. Full-text search performance
        start = time.time()
        self.db.cursor.execute("""
            SELECT paper_id, title
            FROM research_papers
            WHERE search_vector @@ to_tsquery('english', 'protein & muscle')
            ORDER BY ts_rank(search_vector, to_tsquery('english', 'protein & muscle')) DESC
            LIMIT 10;
        """)
        benchmarks['full_text_search'] = (time.time() - start) * 1000
        
        # 3. Analytics query performance
        start = time.time()
        self.db.cursor.execute("""
            SELECT 
                DATE(timestamp) as date,
                COUNT(*) as queries,
                AVG(response_time_ms) as avg_time
            FROM user_queries
            GROUP BY DATE(timestamp)
            ORDER BY date DESC
            LIMIT 30;
        """)
        benchmarks['analytics'] = (time.time() - start) * 1000
        
        # 4. Join-heavy query
        start = time.time()
        self.db.cursor.execute("""
            SELECT 
                rp.title,
                COUNT(DISTINCT rc.response_id) as citation_count,
                AVG(cr.times_served) as avg_times_served
            FROM research_papers rp
            LEFT JOIN response_citations rc ON rp.paper_id = rc.paper_id
            LEFT JOIN cached_responses cr ON rc.response_id = cr.response_id
            GROUP BY rp.paper_id, rp.title
            ORDER BY citation_count DESC
            LIMIT 10;
        """)
        benchmarks['complex_join'] = (time.time() - start) * 1000
        
        # Display results
        for query_name, time_ms in benchmarks.items():
            status = "✓" if time_ms < 10 else "⚠️" if time_ms < 50 else "❌"
            print(f"{status} {query_name}: {time_ms:.2f}ms")
        
        return benchmarks
    
    def add_performance_indexes(self):
        """Add the recommended performance indexes"""
        print("\n🔧 Adding Performance Indexes\n")
        
        indexes_to_create = [
            ("idx_queries_normalized", 
             "CREATE INDEX IF NOT EXISTS idx_queries_normalized ON user_queries(normalized_text);"),
            ("idx_responses_timestamp", 
             "CREATE INDEX IF NOT EXISTS idx_responses_timestamp ON cached_responses(timestamp DESC);"),
            ("idx_papers_quality_used", 
             "CREATE INDEX IF NOT EXISTS idx_papers_quality_used ON research_papers(quality_score DESC, times_used DESC);"),
            ("idx_queries_timestamp_cache", 
             "CREATE INDEX IF NOT EXISTS idx_queries_timestamp_cache ON user_queries(timestamp DESC, cache_hit);"),
            ("idx_citations_composite", 
             "CREATE INDEX IF NOT EXISTS idx_citations_composite ON response_citations(paper_id, response_id);")
        ]
        
        for idx_name, idx_sql in indexes_to_create:
            try:
                self.db.cursor.execute(idx_sql)
                self.db.conn.commit()
                print(f"✓ Created index: {idx_name}")
            except Exception as e:
                print(f"✗ Failed to create {idx_name}: {e}")
                self.db.conn.rollback()
    
    def analyze_table_sizes(self):
        """Check table sizes and row counts"""
        print("\n📊 Table Statistics\n")
        
        self.db.cursor.execute("""
            SELECT 
                schemaname,
                relname as tablename,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||relname)) as size,
                n_live_tup as row_count
            FROM pg_stat_user_tables
            WHERE schemaname = 'public'
            ORDER BY pg_total_relation_size(schemaname||'.'||relname) DESC;
        """)
        
        tables = self.db.cursor.fetchall()
        
        print(f"{'Table':<25} {'Rows':<10} {'Size':<10}")
        print("-" * 45)
        for table in tables:
            print(f"{table['tablename']:<25} {table['row_count']:<10} {table['size']:<10}")
    
    def vacuum_analyze(self):
        """Run VACUUM ANALYZE to update statistics"""
        print("\n🧹 Running VACUUM ANALYZE\n")
        
        # Need to commit any pending transaction first
        self.db.conn.commit()
        
        # Set autocommit for VACUUM
        old_isolation = self.db.conn.isolation_level
        self.db.conn.set_isolation_level(0)
        
        try:
            self.db.cursor.execute("VACUUM ANALYZE;")
            print("✓ VACUUM ANALYZE completed")
        finally:
            # Restore isolation level
            self.db.conn.set_isolation_level(old_isolation)

# Run performance optimization
if __name__ == "__main__":
    db = FitFactDB()
    optimizer = PerformanceOptimizer(db)
    
    print("🚀 Database Performance Optimization\n")
    
    # 1. Analyze missing indexes
    optimizer.analyze_missing_indexes()
    
    # 2. Run benchmarks before optimization
    print("\nBefore optimization:")
    before = optimizer.benchmark_queries()
    
    # 3. Add performance indexes
    optimizer.add_performance_indexes()
    
    # 4. Run VACUUM ANALYZE
    optimizer.vacuum_analyze()
    
    # 5. Run benchmarks after optimization
    print("\nAfter optimization:")
    after = optimizer.benchmark_queries()
    
    # 6. Show improvement
    print("\n📈 Performance Improvements:")
    for query in before.keys():
        improvement = ((before[query] - after[query]) / before[query]) * 100
        if improvement > 0:
            print(f"  {query}: {improvement:.1f}% faster")
    
    # 7. Show table sizes
    optimizer.analyze_table_sizes()
    
    db.close()