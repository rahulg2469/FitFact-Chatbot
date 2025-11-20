"""
FitFact Database Performance Testing
Week 4 - Simplified Performance Metrics
Author: Satya Harish
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import time
import statistics
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

class PerformanceTester:
    def __init__(self):
        self.conn = psycopg2.connect(
            dbname=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            host=os.getenv('DB_HOST'),
            port=os.getenv('DB_PORT')
        )
        self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        print("✅ Connected to FitFact database")
    
    def test_current_performance(self):
        """Test actual current database performance"""
        print("\n🔬 TESTING CURRENT DATABASE PERFORMANCE\n")
        print("=" * 60)
        
        results = {}
        
        # 1. Test cache lookup
        print("Testing cache lookups...")
        times = []
        test_queries = [
            "benefits of creatine",
            "protein intake timing",
            "HIIT vs cardio",
            "muscle recovery",
            "strength training"
        ]
        
        for query in test_queries * 10:  # 50 total lookups
            start = time.perf_counter()
            self.cursor.execute("SELECT * FROM find_cached_response(%s)", (query,))
            self.cursor.fetchone()
            times.append((time.perf_counter() - start) * 1000)
        
        results['Cache Lookup'] = {
            'avg_ms': statistics.mean(times),
            'min_ms': min(times),
            'max_ms': max(times),
            'median_ms': statistics.median(times)
        }
        
        # 2. Test full-text search
        print("Testing full-text search...")
        times = []
        search_terms = ['protein', 'muscle', 'creatine', 'exercise', 'recovery']
        
        for term in search_terms * 10:  # 50 searches
            start = time.perf_counter()
            self.cursor.execute("""
                SELECT paper_id, title 
                FROM research_papers 
                WHERE to_tsvector('english', title || ' ' || COALESCE(abstract, '')) 
                      @@ plainto_tsquery('english', %s)
                LIMIT 10
            """, (term,))
            self.cursor.fetchall()
            times.append((time.perf_counter() - start) * 1000)
        
        results['Full-Text Search'] = {
            'avg_ms': statistics.mean(times),
            'min_ms': min(times),
            'max_ms': max(times),
            'median_ms': statistics.median(times)
        }
        
        # 3. Test complex join query
        print("Testing complex analytics queries...")
        times = []
        
        for _ in range(20):
            start = time.perf_counter()
            self.cursor.execute("""
                SELECT 
                    rp.title,
                    COUNT(rc.response_id) as citations,
                    rp.times_used
                FROM research_papers rp
                LEFT JOIN response_citations rc ON rp.paper_id = rc.paper_id
                GROUP BY rp.paper_id
                ORDER BY rp.times_used DESC
                LIMIT 10
            """)
            self.cursor.fetchall()
            times.append((time.perf_counter() - start) * 1000)
        
        results['Complex Analytics'] = {
            'avg_ms': statistics.mean(times),
            'min_ms': min(times),
            'max_ms': max(times),
            'median_ms': statistics.median(times)
        }
        
        # 4. Check current database stats
        self.cursor.execute("SELECT * FROM database_health")
        health = self.cursor.fetchall()
        
        # Generate report
        self.generate_report(results, health)
        return results
    
    def generate_report(self, results, health):
        """Generate performance report"""
        report = f"""
╔══════════════════════════════════════════════════════════════╗
║           FITFACT DATABASE PERFORMANCE REPORT                ║
║                  {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}                      ║
╚══════════════════════════════════════════════════════════════╝

📊 PERFORMANCE METRICS
{"="*60}

"""
        for operation, metrics in results.items():
            report += f"🔹 {operation}\n"
            report += f"   Average:   {metrics['avg_ms']:.2f}ms\n"
            report += f"   Median:    {metrics['median_ms']:.2f}ms\n"
            report += f"   Min:       {metrics['min_ms']:.2f}ms\n"
            report += f"   Max:       {metrics['max_ms']:.2f}ms\n\n"
        
        report += f"""
🏆 PERFORMANCE GRADES
{"="*60}

"""
        for operation, metrics in results.items():
            avg = metrics['avg_ms']
            if avg < 1:
                grade = "A+ (Sub-millisecond)"
            elif avg < 10:
                grade = "A (Excellent)"
            elif avg < 50:
                grade = "B (Good)"
            elif avg < 100:
                grade = "C (Acceptable)"
            else:
                grade = "D (Needs Optimization)"
            report += f"{operation}: {grade}\n"
        
        report += f"""

💾 DATABASE HEALTH
{"="*60}

"""
        for item in health:
            report += f"{item['metric']}: {item['value']} - {item['status']}\n"
        
        # Save report
        with open('database_files/performance_report.txt', 'w') as f:
            f.write(report)
        
        print(report)
        print("✅ Report saved to database_files/performance_report.txt")
    
    def close(self):
        self.conn.close()

if __name__ == "__main__":
    tester = PerformanceTester()
    try:
        tester.test_current_performance()
    finally:
        tester.close()