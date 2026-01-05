"""
Batch Testing Script for FitFact ML Data Collection
Automatically processes multiple queries to collect training data
"""

import sys
import time
sys.path.append('..')
sys.path.append('../database_files')
sys.path.append('../claude_files')
sys.path.append('../src/etl')

from database_files.database import FitFactDB
from database_files.cache_manager import CacheManager
from claude_files.claude_api import ClaudeProcessor
from keyword_extractor import FitnessKeywordExtractor
from pubmed_query_optimizer import PubMedQueryOptimizer
from src.etl.pubmed_fetcher import search_pubmed, fetch_paper_details
from ml_optimizer.ml_data_collector import MLDataCollector
from dotenv import load_dotenv

load_dotenv()

# Your 100 test questions
TEST_QUESTIONS = [
    # Simple (30 questions)
    "What is protein?",
    "What is creatine?",
    "What is HIIT?",
    "What is cardio?",
    "What is BMI?",
    "What is bulking?",
    "What is cutting?",
    "What are macros?",
    "What is testosterone?",
    "What is metabolism?",
    "What is hypertrophy?",
    "What are BCAAs?",
    "What is glycogen?",
    "What is progressive overload?",
    "What is a calorie?",
    "What is BMR?",
    "What is TDEE?",
    "What are electrolytes?",
    "What is lactate?",
    "What is VO2 max?",
    "What is soreness?",
    "What is flexibility?",
    "What is endurance?",
    "What are carbs?",
    "What is insulin?",
    "What is cortisol?",
    "What are abs?",
    "What is a rep?",
    "What is a set?",
    "What is deloading?",
    
    # Medium (40 questions)
    "How much protein should I eat per day?",
    "What's the best time to workout?",
    "Should I do cardio before or after weights?",
    "How many days per week should I train?",
    "Is fasted cardio better for fat loss?",
    "How long should my workouts be?",
    "What's the best protein powder for muscle gain?",
    "How much water should I drink daily?",
    "Should I take creatine on rest days?",
    "What's better for fat loss: HIIT or steady cardio?",
    "How many calories should I eat to lose weight?",
    "Is it possible to gain muscle and lose fat simultaneously?",
    "What's the ideal rep range for muscle growth?",
    "Should I train to failure on every set?",
    "How important is sleep for muscle recovery?",
    "What should I eat before a workout?",
    "What should I eat after a workout?",
    "How long should I rest between sets?",
    "Is protein timing really important for muscle growth?",
    "Can I build muscle without supplements?",
    "What's the best exercise for building chest muscle?",
    "How often should I change my workout routine?",
    "Should I do full body or split workouts?",
    "Is stretching before exercise necessary?",
    "How much cardio is too much for muscle gain?",
    "What's the difference between whey and casein protein?",
    "Should I lift heavy or light weights for strength?",
    "How do I break through a plateau?",
    "Is it necessary to count calories for weight loss?",
    "What causes muscle soreness after workouts?",
    "How long does it take to build noticeable muscle?",
    "Should beginners do compound or isolation exercises?",
    "What's the role of genetics in muscle building?",
    "Is intermittent fasting good for muscle gain?",
    "How important are rest days for progress?",
    "What's the best cardio for preserving muscle mass?",
    "Should I train abs every day?",
    "How do I lose belly fat specifically?",
    "What supplements are actually worth taking?",
    "Is soreness a good indicator of workout effectiveness?",
    
    # Complex (30 questions)
    "Compare the effects of whey versus casein protein on muscle protein synthesis in resistance-trained individuals",
    "What is the optimal protein distribution throughout the day for maximizing muscle hypertrophy in natural athletes?",
    "How does progressive overload through volume versus intensity affect long-term strength gains in intermediate lifters?",
    "Explain the mechanism by which creatine supplementation enhances performance in high-intensity resistance training protocols",
    "Compare the effectiveness of different periodization models for strength development in competitive powerlifters",
    "What are the hormonal and metabolic differences between morning versus evening resistance training sessions?",
    "How does training frequency affect muscle protein synthesis rates and recovery in natural bodybuilders?",
    "Compare the muscle-building effects of training to failure versus stopping short of failure across multiple sets",
    "What is the relationship between training volume, intensity, and frequency for optimal muscle hypertrophy?",
    "How does nutrient timing around workouts affect muscle glycogen replenishment and protein synthesis rates?",
    "Compare the effects of different rep tempo strategies on mechanical tension and muscle growth adaptations",
    "What are the physiological mechanisms underlying the anabolic window and its practical significance?",
    "How does sleep quality and duration affect testosterone levels, cortisol, and recovery in strength athletes?",
    "Compare the effectiveness of linear versus undulating periodization for improving one-rep max strength",
    "What is the optimal rest interval between sets for maximizing both strength and hypertrophy adaptations?",
    "How does training age affect the dose-response relationship between volume and muscle growth?",
    "Compare the metabolic and cardiovascular adaptations from HIIT versus steady-state cardio in overweight individuals",
    "What are the mechanisms by which eccentric training causes greater muscle damage and hypertrophy than concentric training?",
    "How does protein quality and amino acid profile affect muscle protein synthesis compared to total protein intake?",
    "Compare the effects of different carbohydrate intake levels on performance and body composition during a fat loss phase",
    "What is the interference effect between concurrent strength and endurance training and how can it be minimized?",
    "How does blood flow restriction training compare to traditional high-load resistance training for muscle hypertrophy?",
    "What are the physiological differences between muscle hypertrophy from sarcoplasmic versus myofibrillar adaptations?",
    "Compare the effectiveness of different deload strategies for managing fatigue while maintaining training adaptations",
    "How does the rate of weight loss affect muscle mass preservation during caloric restriction in resistance-trained individuals?",
    "What is the relationship between training proximity to failure and stimulus-to-fatigue ratio across different exercises?",
    "Compare the anabolic effects of plant-based versus animal-based protein sources on muscle protein synthesis rates",
    "How does age affect protein requirements and muscle protein synthesis response to resistance training?",
    "What are the practical differences between training for strength versus hypertrophy in terms of programming variables?",
    "Compare the long-term effectiveness of push-pull-legs versus upper-lower split routines for intermediate natural lifters"
]

class BatchTester:
    """Automated batch testing for ML data collection"""
    
    def __init__(self):
        print("\n" + "="*80)
        print("FitFact Batch Testing - ML Data Collection")
        print("="*80)
        
        # Initialize components
        self.db = FitFactDB()
        self.cache = CacheManager(self.db)
        self.claude = ClaudeProcessor()
        self.keyword_extractor = FitnessKeywordExtractor()
        self.query_optimizer = PubMedQueryOptimizer()
        self.ml_collector = MLDataCollector(self.db.conn)
        
        print("✅ All components initialized\n")
    
    def process_single_query(self, question: str, index: int, total: int):
        """Process a single query and collect ML features"""
        print(f"\n[{index}/{total}] Processing: {question[:60]}...")
        
        start_time = time.time()
        
        try:
            # Check cache first
            cached = self.cache.smart_cache_lookup(question, threshold=0.7)
            if cached:
                print(f"  ✓ Cache hit! (similarity: {cached.get('similarity', 1.0):.2f})")
                response_text = cached['response_text']
                from_cache = True
            else:
                # Search PubMed
                optimized = self.query_optimizer.optimize_query(question)
                keywords = self.keyword_extractor.extract_keywords(question)
                
                papers = []
                seen_pmids = set()
                
                # Try academic query first
                for search_query in optimized['search_strategies'][:2]:
                    if len(papers) >= 5:
                        break
                    
                    try:
                        pmids = search_pubmed(search_query, max_results=5)
                        if pmids:
                            for pmid in pmids:
                                if pmid not in seen_pmids and len(papers) < 5:
                                    paper = fetch_paper_details(pmid)
                                    if paper:
                                        seen_pmids.add(pmid)
                                        papers.append(paper)
                    except:
                        pass
                    
                    time.sleep(0.5)  # Rate limiting
                
                if not papers:
                    print(f"  ⚠️ No papers found - skipping")
                    return False
                
                # Generate response
                claude_response = self.claude.generate_response(papers, question)
                
                if not claude_response['success']:
                    print(f"  ⚠️ Claude API error - skipping")
                    return False
                
                response_text = claude_response['text']
                
                # Store in cache
                paper_ids = []
                for paper in papers:
                    try:
                        paper_id = self.db.save_paper(
                            pmid=paper['pmid'],
                            title=paper['title'],
                            abstract=paper['abstract'],
                            authors=str(paper.get('authors', [])),
                            pub_date=paper.get('publication_date', '2024-01-01'),
                            journal=paper.get('journal', 'Unknown'),
                            study_type='research'
                        )
                        paper_ids.append(paper_id)
                    except:
                        pass
                
                if paper_ids:
                    self.cache.store_in_cache(question, response_text, paper_ids)
                
                from_cache = False
            
            # Collect ML features
            try:
                # Get query_id
                self.db.cursor.execute("""
                    SELECT query_id FROM user_queries 
                    WHERE query_text = %s 
                    ORDER BY timestamp DESC LIMIT 1
                """, (question,))
                result = self.db.cursor.fetchone()
                
                if result:
                    query_id = result['query_id']
                    
                    # Collect features
                    feature_id = self.ml_collector.collect_query_features(query_id, question)
                    
                    elapsed = time.time() - start_time
                    print(f"  ✓ Features collected (feature_id: {feature_id}, {elapsed:.1f}s)")
                    return True
                
            except Exception as e:
                print(f"  ⚠️ ML collection failed: {e}")
                return False
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
            return False
    
    def run_batch(self, start_index=0, count=None, delay=2):
        """
        Run batch testing
        
        Args:
            start_index: Which question to start from (0-99)
            count: How many questions to process (None = all remaining)
            delay: Seconds to wait between questions (for rate limiting)
        """
        questions = TEST_QUESTIONS[start_index:]
        if count:
            questions = questions[:count]
        
        total = len(questions)
        successful = 0
        failed = 0
        
        print(f"\n🚀 Starting batch test: {total} questions")
        print(f"   Start index: {start_index}")
        print(f"   Delay: {delay}s between queries")
        print("="*80)
        
        for idx, question in enumerate(questions, start=start_index + 1):
            success = self.process_single_query(question, idx, start_index + total)
            
            if success:
                successful += 1
            else:
                failed += 1
            
            # Rate limiting delay
            if idx < start_index + total:  # Don't delay after last question
                time.sleep(delay)
        
        # Summary
        print("\n" + "="*80)
        print("BATCH TEST COMPLETE")
        print("="*80)
        print(f"Total processed: {total}")
        print(f"Successful: {successful} ({successful/total*100:.1f}%)")
        print(f"Failed: {failed} ({failed/total*100:.1f}%)")
        print("\nData collection complete! ✅")
        
        self.db.close()

# Main execution
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Batch test FitFact queries')
    parser.add_argument('--start', type=int, default=0, help='Start index (0-99)')
    parser.add_argument('--count', type=int, default=None, help='Number of questions to process')
    parser.add_argument('--delay', type=float, default=2.0, help='Delay between queries (seconds)')
    
    args = parser.parse_args()
    
    tester = BatchTester()
    tester.run_batch(start_index=args.start, count=args.count, delay=args.delay)
