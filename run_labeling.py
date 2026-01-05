"""
Wrapper script to run manual labeling tool
Run this from project root directory
"""

import sys
import os

# Add ml_optimizer to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ml_optimizer'))

# Now import and run
from ml_optimizer.manual_labeling_tool import ManualLabelingTool
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
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
