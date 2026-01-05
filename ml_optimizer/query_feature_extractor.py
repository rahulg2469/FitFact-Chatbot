"""
Query Feature Extractor for ML Prompt Optimizer
Extracts features from user queries for complexity classification
"""

import re
from typing import Dict, List
import nltk
from collections import Counter

# Download required NLTK data (run once)
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

class QueryFeatureExtractor:
    """Extract ML features from fitness queries"""
    
    # Keywords that indicate different complexity levels
    COMPARISON_KEYWORDS = [
        'vs', 'versus', 'compare', 'comparison', 'difference', 'better',
        'worse', 'prefer', 'instead of', 'rather than', 'alternative'
    ]
    
    SPECIFICITY_KEYWORDS = [
        'specific', 'specifically', 'detailed', 'exactly', 'precise',
        'in detail', 'elaborate', 'comprehensive', 'thorough'
    ]
    
    MECHANISM_KEYWORDS = [
        'how does', 'why does', 'mechanism', 'process', 'explain how',
        'what causes', 'reason for', 'work', 'function'
    ]
    
    # Common fitness technical terms
    TECHNICAL_TERMS = [
        'hypertrophy', 'atrophy', 'metabolism', 'glycogen', 'creatine',
        'protein synthesis', 'catabolism', 'anabolism', 'mitochondria',
        'vo2 max', 'lactate threshold', 'heart rate', 'reps', 'sets',
        'progressive overload', 'periodization', 'macronutrients',
        'testosterone', 'cortisol', 'insulin', 'glucagon', 'amino acids',
        'resistance training', 'cardiovascular', 'aerobic', 'anaerobic',
        'bmr', 'tdee', 'caloric deficit', 'surplus', 'body composition'
    ]
    
    def __init__(self):
        """Initialize feature extractor"""
        pass
    
    def extract_features(self, query: str) -> Dict:
        """
        Extract all features from a query
        
        Args:
            query: User query text
            
        Returns:
            Dictionary of extracted features
        """
        query_lower = query.lower()
        
        # Basic text features
        words = query.split()
        sentences = nltk.sent_tokenize(query)
        
        features = {
            # Text statistics
            'word_count': len(words),
            'char_count': len(query),
            'sentence_count': len(sentences),
            'question_mark_count': query.count('?'),
            'avg_word_length': sum(len(word) for word in words) / len(words) if words else 0,
            
            # Complexity indicators
            'has_comparison': self._has_keywords(query_lower, self.COMPARISON_KEYWORDS),
            'has_specificity': self._has_keywords(query_lower, self.SPECIFICITY_KEYWORDS),
            'has_mechanism': self._has_keywords(query_lower, self.MECHANISM_KEYWORDS),
            'has_multiple_questions': query.count('?') > 1,
            
            # Technical content
            'technical_term_count': self._count_technical_terms(query_lower),
            'technical_terms_found': self._find_technical_terms(query_lower),
            
            # Additional features
            'has_numbers': bool(re.search(r'\d', query)),
            'has_units': self._has_units(query_lower),
            'word_diversity': len(set(words)) / len(words) if words else 0,
        }
        
        # Calculate preliminary complexity score
        features['auto_complexity'] = self._calculate_complexity(features)
        
        return features
    
    def _has_keywords(self, text: str, keywords: List[str]) -> bool:
        """Check if text contains any of the keywords"""
        return any(keyword in text for keyword in keywords)
    
    def _count_technical_terms(self, text: str) -> int:
        """Count number of technical terms in text"""
        return sum(1 for term in self.TECHNICAL_TERMS if term in text)
    
    def _find_technical_terms(self, text: str) -> List[str]:
        """Find which technical terms are present"""
        return [term for term in self.TECHNICAL_TERMS if term in text]
    
    def _has_units(self, text: str) -> bool:
        """Check if text contains measurement units"""
        units = ['kg', 'lbs', 'pounds', 'grams', 'mg', 'ml', 'minutes', 
                 'hours', 'days', 'weeks', 'months', 'reps', 'sets', '%']
        return any(unit in text for unit in units)
    
    def _calculate_complexity(self, features: Dict) -> str:
        """
        Calculate automatic complexity classification
        Based on heuristic rules
        
        Returns:
            'simple', 'medium', or 'complex'
        """
        score = 0
        
        # Word count scoring
        if features['word_count'] > 20:
            score += 1
        if features['word_count'] > 40:
            score += 1
            
        # Boolean features
        if features['has_comparison']:
            score += 2
        if features['has_mechanism']:
            score += 2
        if features['has_specificity']:
            score += 1
        if features['has_multiple_questions']:
            score += 1
            
        # Technical content
        if features['technical_term_count'] > 2:
            score += 1
        if features['technical_term_count'] > 5:
            score += 1
            
        # Classify
        if score <= 2:
            return 'simple'
        elif score <= 5:
            return 'medium'
        else:
            return 'complex'
    
    def get_feature_vector(self, query: str) -> List[float]:
        """
        Get numerical feature vector for ML model
        
        Returns:
            List of numerical features suitable for sklearn
        """
        features = self.extract_features(query)
        
        # Convert to numerical vector
        vector = [
            features['word_count'],
            features['char_count'],
            features['sentence_count'],
            features['question_mark_count'],
            features['avg_word_length'],
            int(features['has_comparison']),
            int(features['has_specificity']),
            int(features['has_mechanism']),
            int(features['has_multiple_questions']),
            features['technical_term_count'],
            int(features['has_numbers']),
            int(features['has_units']),
            features['word_diversity']
        ]
        
        return vector
    
    def get_feature_names(self) -> List[str]:
        """Get names of features in the vector"""
        return [
            'word_count',
            'char_count', 
            'sentence_count',
            'question_mark_count',
            'avg_word_length',
            'has_comparison',
            'has_specificity',
            'has_mechanism',
            'has_multiple_questions',
            'technical_term_count',
            'has_numbers',
            'has_units',
            'word_diversity'
        ]


# Example usage and testing
if __name__ == "__main__":
    extractor = QueryFeatureExtractor()
    
    # Test queries of different complexities
    test_queries = [
        "What is protein?",  # Simple
        "How much protein should I eat per day?",  # Medium
        "Compare the effects of whey vs casein protein on muscle protein synthesis in trained individuals",  # Complex
        "Why does progressive overload lead to hypertrophy?"  # Medium-Complex
    ]
    
    print("Query Feature Extraction Examples:\n")
    for query in test_queries:
        print(f"Query: {query}")
        features = extractor.extract_features(query)
        print(f"Complexity: {features['auto_complexity']}")
        print(f"Word count: {features['word_count']}")
        print(f"Technical terms: {features['technical_term_count']}")
        print(f"Has comparison: {features['has_comparison']}")
        print(f"Has mechanism: {features['has_mechanism']}")
        print(f"Technical terms found: {features['technical_terms_found']}")
        print("-" * 80)
