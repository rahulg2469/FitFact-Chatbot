"""
Keyword Extraction Module for FitFact
Week 2 - Extract fitness-related keywords from user queries
"""

import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.tag import pos_tag
from typing import List, Set, Dict
import re

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

try:
    nltk.data.find('taggers/averaged_perceptron_tagger')
except LookupError:
    nltk.download('averaged_perceptron_tagger')

class FitnessKeywordExtractor:
    """Extract relevant keywords from fitness-related queries"""
    
    def __init__(self):
        self.stop_words = set(stopwords.words('english'))
        
        # Custom fitness-related terms to always include
        self.fitness_terms = {
            'protein', 'carbs', 'fat', 'calories', 'muscle', 'strength',
            'cardio', 'hiit', 'workout', 'exercise', 'training', 'recovery',
            'supplement', 'creatine', 'whey', 'bcaa', 'pre-workout',
            'hypertrophy', 'endurance', 'resistance', 'reps', 'sets',
            'bulking', 'cutting', 'lean', 'mass', 'weight', 'loss', 'gain',
            'nutrition', 'diet', 'fast', 'metabolism', 'energy', 'performance'
        }
        
        # Fitness phrase mappings (multi-word terms)
        self.fitness_phrases = {
            'high intensity interval training': 'HIIT',
            'branched chain amino acids': 'BCAA',
            'one rep max': '1RM',
            'body mass index': 'BMI',
            'delayed onset muscle soreness': 'DOMS',
            'rate of perceived exertion': 'RPE',
            'heart rate': 'heart_rate',
            'blood pressure': 'blood_pressure',
            'muscle growth': 'hypertrophy',
            'fat loss': 'fat_loss',
            'muscle building': 'hypertrophy',
            'weight training': 'resistance_training',
            'strength training': 'resistance_training'
        }
        
        # Question words to remove
        self.question_words = {
            'what', 'when', 'where', 'why', 'how', 'which', 'who',
            'is', 'are', 'was', 'were', 'do', 'does', 'did',
            'can', 'could', 'should', 'would', 'will'
        }
    
    def extract_keywords(self, query: str) -> Dict:
        """
        Extract keywords from a fitness query
        
        Args:
            query: User's fitness question
            
        Returns:
            Dict with keywords, key phrases, and fitness terms
        """
        query_lower = query.lower()
        
        # Step 1: Extract fitness phrases (before tokenization)
        extracted_phrases = []
        for phrase, replacement in self.fitness_phrases.items():
            if phrase in query_lower:
                extracted_phrases.append(replacement)
                # Replace in query to avoid duplicate extraction
                query_lower = query_lower.replace(phrase, replacement)
        
        # Step 2: Tokenize and clean
        tokens = word_tokenize(query_lower)
        
        # Step 3: Remove stopwords and question words
        filtered_tokens = [
            token for token in tokens 
            if token not in self.stop_words 
            and token not in self.question_words
            and token.isalnum()  # Remove punctuation
        ]
        
        # Step 4: POS tagging to identify important words
        pos_tags = pos_tag(filtered_tokens)
        
        # Step 5: Extract nouns and relevant terms
        keywords = []
        for word, pos in pos_tags:
            # Include nouns (NN*), verbs (VB*), and adjectives (JJ*)
            if pos.startswith(('NN', 'VB', 'JJ')):
                keywords.append(word)
            # Always include fitness terms
            elif word in self.fitness_terms:
                keywords.append(word)
        
        # Step 6: Extract fitness-specific terms
        fitness_keywords = [
            word for word in filtered_tokens 
            if word in self.fitness_terms
        ]
        
        # Step 7: Remove duplicates while preserving order
        keywords = list(dict.fromkeys(keywords))
        
        return {
            'all_keywords': keywords,
            'fitness_terms': fitness_keywords,
            'extracted_phrases': extracted_phrases,
            'search_query': self._create_search_query(keywords, extracted_phrases),
            'original_query': query
        }
    
    def _create_search_query(self, keywords: List[str], phrases: List[str]) -> str:
        """
        Create an optimized search query for PubMed
        
        Args:
            keywords: List of extracted keywords
            phrases: List of extracted phrases
            
        Returns:
            Optimized search query string
        """
        # Combine keywords and phrases, prioritizing fitness terms
        all_terms = phrases + keywords[:5]  # Limit to avoid overly specific queries
        
        # Remove duplicates
        all_terms = list(dict.fromkeys(all_terms))
        
        # Join with spaces for PubMed search
        return ' '.join(all_terms)
    
    def get_topic_category(self, keywords: List[str]) -> str:
        """
        Categorize the query into fitness topics
        
        Args:
            keywords: List of keywords
            
        Returns:
            Primary topic category
        """
        categories = {
            'supplementation': ['supplement', 'creatine', 'whey', 'protein', 'bcaa', 
                              'vitamin', 'mineral', 'pre-workout', 'post-workout'],
            'nutrition': ['diet', 'nutrition', 'calories', 'macros', 'carbs', 'fat',
                         'meal', 'food', 'eating', 'fasting'],
            'strength_training': ['strength', 'resistance', 'weight', 'lifting', 
                                 'hypertrophy', 'muscle', 'reps', 'sets'],
            'cardio': ['cardio', 'hiit', 'running', 'cycling', 'endurance',
                      'aerobic', 'heart rate', 'vo2max'],
            'recovery': ['recovery', 'rest', 'sleep', 'injury', 'soreness',
                        'doms', 'stretching', 'massage'],
            'weight_management': ['weight', 'loss', 'gain', 'cutting', 'bulking',
                                 'lean', 'body composition', 'bmi']
        }
        
        category_scores = {}
        for category, terms in categories.items():
            score = sum(1 for keyword in keywords if keyword in terms)
            if score > 0:
                category_scores[category] = score
        
        if category_scores:
            return max(category_scores, key=category_scores.get)
        return 'general_fitness'

# Test function
def test_keyword_extraction():
    """Test the keyword extractor with sample queries"""
    
    extractor = FitnessKeywordExtractor()
    
    test_queries = [
        "What are the benefits of creatine supplementation for muscle growth?",
        "How much protein should I eat after my workout?",
        "Is high intensity interval training better than steady state cardio for fat loss?",
        "What's the optimal rest time between sets for strength training?",
        "Can I build muscle while losing weight?",
        "Should I take BCAAs during my workout?"
    ]
    
    print("🔍 Fitness Keyword Extraction Tests")
    print("=" * 70)
    
    for query in test_queries:
        print(f"\n📝 Query: {query}")
        print("-" * 70)
        
        results = extractor.extract_keywords(query)
        
        print(f"🏷️  All Keywords: {', '.join(results['all_keywords'])}")
        print(f"💪 Fitness Terms: {', '.join(results['fitness_terms'])}")
        print(f"🔗 Extracted Phrases: {', '.join(results['extracted_phrases'])}")
        print(f"🔎 Search Query: {results['search_query']}")
        
        # Get topic category
        category = extractor.get_topic_category(results['all_keywords'])
        print(f"📁 Category: {category}")

if __name__ == "__main__":
    test_keyword_extraction()