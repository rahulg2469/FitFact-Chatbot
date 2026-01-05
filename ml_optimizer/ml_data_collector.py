"""
ML Data Collector
Integrates feature extraction with database storage for ML training data collection
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import json
from datetime import datetime
from typing import Dict, Optional
from .query_feature_extractor import QueryFeatureExtractor


class MLDataCollector:
    """Collect and store ML training data"""
    
    def __init__(self, db_connection):
        """
        Initialize data collector
        
        Args:
            db_connection: psycopg2 database connection
        """
        self.conn = db_connection
        self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        self.feature_extractor = QueryFeatureExtractor()
    
    def collect_query_features(self, query_id: int, query_text: str) -> int:
        """
        Extract and store features for a query
        
        Args:
            query_id: ID of the query in user_queries table
            query_text: The actual query text
            
        Returns:
            feature_id: ID of the inserted feature record
        """
        # Extract features
        features = self.feature_extractor.extract_features(query_text)
        
        # Insert into database
        insert_query = """
            INSERT INTO query_features (
                query_id, word_count, char_count, sentence_count,
                question_mark_count, has_comparison, has_specificity,
                has_mechanism, has_multiple_questions, technical_term_count,
                complexity_label, complexity_confidence
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            ) RETURNING feature_id
        """
        
        self.cursor.execute(insert_query, (
            query_id,
            features['word_count'],
            features['char_count'],
            features['sentence_count'],
            features['question_mark_count'],
            features['has_comparison'],
            features['has_specificity'],
            features['has_mechanism'],
            features['has_multiple_questions'],
            features['technical_term_count'],
            features['auto_complexity'],
            0.6  # Default confidence for rule-based classification
        ))
        
        self.conn.commit()
        result = self.cursor.fetchone()
        return result['feature_id']
    
    def add_manual_label(self, query_id: int, complexity: str, 
                        labeled_by: str = 'manual') -> bool:
        """
        Add manual complexity label to a query
        
        Args:
            query_id: ID of the query
            complexity: 'simple', 'medium', or 'complex'
            labeled_by: Who labeled it
            
        Returns:
            Success boolean
        """
        if complexity not in ['simple', 'medium', 'complex']:
            raise ValueError(f"Invalid complexity: {complexity}")
        
        update_query = """
            UPDATE query_features
            SET manual_label = %s,
                labeled_by = %s,
                labeled_at = %s
            WHERE query_id = %s
        """
        
        self.cursor.execute(update_query, (
            complexity,
            labeled_by,
            datetime.now(),
            query_id
        ))
        
        self.conn.commit()
        return self.cursor.rowcount > 0
    
    def record_query_performance(self, query_id: int, response_id: int,
                                experiment_id: int, performance_data: Dict) -> int:
        """
        Record performance metrics for a query-response pair
        
        Args:
            query_id: Query ID
            response_id: Response ID
            experiment_id: Which prompt experiment was used
            performance_data: Dict with performance metrics
            
        Returns:
            performance_id
        """
        insert_query = """
            INSERT INTO query_performance (
                query_id, response_id, experiment_id,
                input_tokens, output_tokens, total_tokens,
                citation_count, response_length_chars, response_length_words,
                total_response_time_ms, claude_api_time_ms
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            ) RETURNING performance_id
        """
        
        self.cursor.execute(insert_query, (
            query_id,
            response_id,
            experiment_id,
            performance_data.get('input_tokens', 0),
            performance_data.get('output_tokens', 0),
            performance_data.get('total_tokens', 0),
            performance_data.get('citation_count', 0),
            performance_data.get('response_length_chars', 0),
            performance_data.get('response_length_words', 0),
            performance_data.get('total_response_time_ms', 0),
            performance_data.get('claude_api_time_ms', 0)
        ))
        
        self.conn.commit()
        result = self.cursor.fetchone()
        return result['performance_id']
    
    def add_user_feedback(self, performance_id: int, rating: int, 
                         feedback_text: Optional[str] = None) -> bool:
        """
        Add user feedback to a performance record
        
        Args:
            performance_id: Performance record ID
            rating: 1-5 rating
            feedback_text: Optional feedback text
            
        Returns:
            Success boolean
        """
        if not 1 <= rating <= 5:
            raise ValueError(f"Rating must be 1-5, got {rating}")
        
        update_query = """
            UPDATE query_performance
            SET user_rating = %s,
                user_feedback_text = %s
            WHERE performance_id = %s
        """
        
        self.cursor.execute(update_query, (rating, feedback_text, performance_id))
        self.conn.commit()
        return self.cursor.rowcount > 0
    
    def get_unlabeled_queries(self, limit: int = 50) -> list:
        """
        Get queries that need manual labeling
        
        Args:
            limit: Maximum number of queries to return
            
        Returns:
            List of query dictionaries
        """
        query = """
            SELECT 
                uq.query_id,
                uq.query_text,
                qf.complexity_label as auto_label,
                qf.word_count,
                qf.technical_term_count,
                qf.has_comparison,
                qf.has_mechanism
            FROM user_queries uq
            JOIN query_features qf ON uq.query_id = qf.query_id
            WHERE qf.manual_label IS NULL
            ORDER BY uq.timestamp DESC
            LIMIT %s
        """
        
        self.cursor.execute(query, (limit,))
        return self.cursor.fetchall()
    
    def export_training_data(self, output_file: str = 'training_data.json'):
        """
        Export labeled data for ML model training
        
        Args:
            output_file: Path to output JSON file
        """
        query = """
            SELECT 
                uq.query_text,
                qf.word_count,
                qf.char_count,
                qf.sentence_count,
                qf.question_mark_count,
                qf.has_comparison,
                qf.has_specificity,
                qf.has_mechanism,
                qf.has_multiple_questions,
                qf.technical_term_count,
                qf.manual_label as complexity
            FROM query_features qf
            JOIN user_queries uq ON qf.query_id = uq.query_id
            WHERE qf.manual_label IS NOT NULL
        """
        
        self.cursor.execute(query)
        data = self.cursor.fetchall()
        
        # Convert to list of dicts
        training_data = [dict(row) for row in data]
        
        # Save to JSON
        with open(output_file, 'w') as f:
            json.dump(training_data, f, indent=2)
        
        print(f"Exported {len(training_data)} labeled examples to {output_file}")
        return len(training_data)
    
    def get_data_statistics(self) -> Dict:
        """Get statistics about collected data"""
        stats = {}
        
        # Total queries
        self.cursor.execute("SELECT COUNT(*) as count FROM query_features")
        stats['total_queries'] = self.cursor.fetchone()['count']
        
        # Labeled queries
        self.cursor.execute("""
            SELECT COUNT(*) as count FROM query_features 
            WHERE manual_label IS NOT NULL
        """)
        stats['labeled_queries'] = self.cursor.fetchone()['count']
        
        # Complexity distribution
        self.cursor.execute("""
            SELECT manual_label, COUNT(*) as count
            FROM query_features
            WHERE manual_label IS NOT NULL
            GROUP BY manual_label
        """)
        stats['complexity_distribution'] = {
            row['manual_label']: row['count'] 
            for row in self.cursor.fetchall()
        }
        
        # Average features by complexity
        self.cursor.execute("""
            SELECT 
                manual_label,
                AVG(word_count) as avg_words,
                AVG(technical_term_count) as avg_technical_terms,
                COUNT(*) as count
            FROM query_features
            WHERE manual_label IS NOT NULL
            GROUP BY manual_label
        """)
        stats['avg_features_by_complexity'] = [dict(row) for row in self.cursor.fetchall()]
        
        return stats
    
    def close(self):
        """Close database connection"""
        self.cursor.close()
        self.conn.close()


# Example usage
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # Connect to database
    conn = psycopg2.connect(
        dbname=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT')
    )
    
    collector = MLDataCollector(conn)
    
    # Example: Get unlabeled queries
    unlabeled = collector.get_unlabeled_queries(limit=10)
    print(f"\nFound {len(unlabeled)} unlabeled queries")
    
    # Get statistics
    stats = collector.get_data_statistics()
    print("\nData Collection Statistics:")
    print(f"Total queries: {stats['total_queries']}")
    print(f"Labeled queries: {stats['labeled_queries']}")
    print(f"Complexity distribution: {stats['complexity_distribution']}")
    
    collector.close()
