"""
Manual Labeling Tool
Interactive CLI for labeling query complexity
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv
from .ml_data_collector import MLDataCollector
from .query_feature_extractor import QueryFeatureExtractor


class ManualLabelingTool:
    """Interactive tool for manually labeling queries"""
    
    def __init__(self, db_connection):
        self.collector = MLDataCollector(db_connection)
        self.extractor = QueryFeatureExtractor()
        self.labeled_count = 0
        
    def display_query_info(self, query_data: dict):
        """Display query information for labeling"""
        print("\n" + "="*80)
        print(f"Query ID: {query_data['query_id']}")
        print(f"\nQuery: {query_data['query_text']}")
        print("\n" + "-"*80)
        
        # Show extracted features
        print("\nAutomatically Detected Features:")
        print(f"  Word Count: {query_data['word_count']}")
        print(f"  Technical Terms: {query_data['technical_term_count']}")
        print(f"  Has Comparison: {'Yes' if query_data['has_comparison'] else 'No'}")
        print(f"  Has Mechanism Question: {'Yes' if query_data['has_mechanism'] else 'No'}")
        print(f"\n  Auto-suggested Complexity: {query_data['auto_label'].upper()}")
        print("-"*80)
    
    def get_user_label(self) -> str:
        """Get complexity label from user"""
        while True:
            print("\nHow would you classify this query?")
            print("  1 - Simple (basic definition/fact)")
            print("  2 - Medium (explanation/comparison)")
            print("  3 - Complex (multiple concepts/mechanisms)")
            print("  s - Skip this query")
            print("  q - Quit labeling session")
            
            choice = input("\nYour choice: ").strip().lower()
            
            if choice == '1':
                return 'simple'
            elif choice == '2':
                return 'medium'
            elif choice == '3':
                return 'complex'
            elif choice == 's':
                return 'skip'
            elif choice == 'q':
                return 'quit'
            else:
                print("Invalid choice. Please try again.")
    
    def label_queries(self, batch_size: int = 20, labeled_by: str = 'manual'):
        """
        Interactive labeling session
        
        Args:
            batch_size: Number of queries to label in this session
            labeled_by: Username or identifier
        """
        # Get unlabeled queries
        queries = self.collector.get_unlabeled_queries(limit=batch_size)
        
        if not queries:
            print("\n✓ No unlabeled queries found. All caught up!")
            return
        
        print(f"\n{'='*80}")
        print(f"Manual Labeling Session - {len(queries)} queries to label")
        print(f"{'='*80}")
        
        for i, query in enumerate(queries, 1):
            print(f"\n[{i}/{len(queries)}]")
            self.display_query_info(query)
            
            label = self.get_user_label()
            
            if label == 'quit':
                print(f"\nSession ended. Labeled {self.labeled_count} queries.")
                break
            elif label == 'skip':
                print("Skipped.")
                continue
            else:
                # Save label
                success = self.collector.add_manual_label(
                    query['query_id'], 
                    label, 
                    labeled_by
                )
                
                if success:
                    self.labeled_count += 1
                    print(f"✓ Labeled as: {label.upper()}")
                else:
                    print("✗ Error saving label")
        
        # Show session summary
        print(f"\n{'='*80}")
        print(f"Session Complete!")
        print(f"Labeled: {self.labeled_count} queries")
        print(f"{'='*80}")
        
        # Show updated statistics
        self.show_statistics()
    
    def show_statistics(self):
        """Display current labeling statistics"""
        stats = self.collector.get_data_statistics()
        
        print("\n" + "="*80)
        print("Current Data Collection Statistics")
        print("="*80)
        print(f"Total Queries: {stats['total_queries']}")
        print(f"Labeled Queries: {stats['labeled_queries']}")
        print(f"Unlabeled: {stats['total_queries'] - stats['labeled_queries']}")
        
        if stats['complexity_distribution']:
            print("\nComplexity Distribution:")
            for complexity, count in stats['complexity_distribution'].items():
                percentage = (count / stats['labeled_queries']) * 100
                print(f"  {complexity.capitalize()}: {count} ({percentage:.1f}%)")
        
        if stats['avg_features_by_complexity']:
            print("\nAverage Features by Complexity:")
            for row in stats['avg_features_by_complexity']:
                print(f"\n  {row['manual_label'].capitalize()} ({row['count']} examples):")
                print(f"    Avg Words: {row['avg_words']:.1f}")
                print(f"    Avg Technical Terms: {row['avg_technical_terms']:.1f}")
        
        print("="*80)
    
    def review_labels(self, limit: int = 10):
        """Review recently labeled queries"""
        query = """
            SELECT 
                uq.query_text,
                qf.manual_label,
                qf.complexity_label as auto_label,
                qf.labeled_at,
                qf.labeled_by
            FROM query_features qf
            JOIN user_queries uq ON qf.query_id = uq.query_id
            WHERE qf.manual_label IS NOT NULL
            ORDER BY qf.labeled_at DESC
            LIMIT %s
        """
        
        self.collector.cursor.execute(query, (limit,))
        results = self.collector.cursor.fetchall()
        
        print("\n" + "="*80)
        print(f"Recently Labeled Queries (Last {limit})")
        print("="*80)
        
        for i, row in enumerate(results, 1):
            agreement = "✓" if row['manual_label'] == row['auto_label'] else "✗"
            print(f"\n{i}. {row['query_text'][:70]}...")
            print(f"   Manual: {row['manual_label']} | Auto: {row['auto_label']} {agreement}")
            print(f"   By: {row['labeled_by']} at {row['labeled_at']}")


def main():
    """Main labeling interface"""
    load_dotenv()
    
    # Connect to database
    conn = psycopg2.connect(
        dbname=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT')
    )
    
    tool = ManualLabelingTool(conn)
    
    print("\n" + "="*80)
    print("FitFact Query Complexity Labeling Tool")
    print("="*80)
    
    while True:
        print("\nWhat would you like to do?")
        print("  1 - Start labeling session")
        print("  2 - View statistics")
        print("  3 - Review recent labels")
        print("  4 - Export training data")
        print("  5 - Exit")
        
        choice = input("\nChoice: ").strip()
        
        if choice == '1':
            batch_size = input("How many queries to label? (default 20): ").strip()
            batch_size = int(batch_size) if batch_size else 20
            
            labeled_by = input("Your name/ID (default 'manual'): ").strip()
            labeled_by = labeled_by if labeled_by else 'manual'
            
            tool.label_queries(batch_size, labeled_by)
            
        elif choice == '2':
            tool.show_statistics()
            
        elif choice == '3':
            limit = input("How many to review? (default 10): ").strip()
            limit = int(limit) if limit else 10
            tool.review_labels(limit)
            
        elif choice == '4':
            filename = input("Output filename (default training_data.json): ").strip()
            filename = filename if filename else 'training_data.json'
            count = tool.collector.export_training_data(filename)
            print(f"\n✓ Exported {count} examples to {filename}")
            
        elif choice == '5':
            print("\nGoodbye!")
            break
        else:
            print("Invalid choice. Please try again.")
    
    conn.close()


if __name__ == "__main__":
    main()
