"""
Phase 3: Prompt Selector with ML Classifier
Uses trained model to predict query complexity and select optimal prompts
"""

import joblib
import os
from typing import Dict, Tuple

class PromptSelector:
    """Selects optimal prompt based on predicted query complexity"""
    
    def __init__(self, model_path=None):
        """Load trained classifier and prompt templates"""
        
        # Auto-detect correct path
        if model_path is None:
            # Check if running from ml_optimizer folder or project root
            if os.path.exists('complexity_classifier.pkl'):
                model_path = 'complexity_classifier.pkl'
            elif os.path.exists('ml_optimizer/complexity_classifier.pkl'):
                model_path = 'ml_optimizer/complexity_classifier.pkl'
            elif os.path.exists('../ml_optimizer/complexity_classifier.pkl'):
                model_path = '../ml_optimizer/complexity_classifier.pkl'
            else:
                raise FileNotFoundError("Could not find complexity_classifier.pkl")
        
        print(f"Loading ML classifier from: {model_path}")
        
        # Load model package
        self.model_package = joblib.load(model_path)
        self.model = self.model_package['model']
        self.scaler = self.model_package.get('scaler', None)
        self.feature_columns = self.model_package['feature_columns']
        self.model_type = self.model_package['model_type']
        
        print(f"✅ Loaded {self.model_type} model")
        print(f"   Accuracy: {self.model_package['accuracy']:.2%}")
        print(f"   Trained on {self.model_package['training_samples']} examples")
        
        # Initialize feature extractor - handle different import scenarios
        try:
            from ml_optimizer.query_feature_extractor import QueryFeatureExtractor
        except ImportError:
            try:
                from query_feature_extractor import QueryFeatureExtractor
            except ImportError:
                # If running from ml_optimizer folder
                import sys
                sys.path.insert(0, os.path.dirname(__file__))
                from query_feature_extractor import QueryFeatureExtractor
        
        self.feature_extractor = QueryFeatureExtractor()
        
        # Define prompt templates (optimized versions from Phase 1)
        self.prompts = {
            'simple': self._get_simple_prompt(),
            'medium': self._get_medium_prompt(),
            'complex': self._get_complex_prompt()
        }
        
        # Track usage statistics
        self.usage_stats = {
            'simple': 0,
            'medium': 0,
            'complex': 0,
            'total': 0
        }
    
    def _get_simple_prompt(self) -> str:
        """Simple prompt template (streamlined, ~380 tokens)"""
        return """You are FitFact, a knowledgeable fitness advisor who provides helpful, evidence-based guidance.

{context_section}

CRITICAL INSTRUCTIONS:
1. ALWAYS consider conversation history when answering follow-up questions
2. If this is a follow-up, maintain context from previous messages and reference them naturally
3. Use research to support practical recommendations
4. If papers don't perfectly match the question, extract relevant principles and apply them
5. Give specific numbers, guidelines, and actionable advice
6. Be confident and encouraging - you're here to help people succeed
7. Never apologize for "limitations" - focus on what you CAN tell them
8. Use numbered lists when presenting multiple points, steps, or recommendations

AVAILABLE RESEARCH:
{formatted_papers}

CURRENT USER QUESTION: {user_question}

Provide a brief, direct response (150-200 words). Use numbered lists if presenting multiple items. Include citations: (Author et al., Year)

References:
Author et al. (Year). Title. PMID: ######"""
    
    def _get_medium_prompt(self) -> str:
        """Medium prompt template (standard, ~410 tokens)"""
        return """You are FitFact, a knowledgeable fitness advisor who provides helpful, evidence-based guidance.

{context_section}

CRITICAL INSTRUCTIONS:
1. ALWAYS consider conversation history when answering follow-up questions
2. If this is a follow-up, maintain context from previous messages and reference them naturally
3. Use research to support practical recommendations
4. If papers don't perfectly match the question, extract relevant principles and apply them
5. Give specific numbers, guidelines, and actionable advice
6. Be confident and encouraging - you're here to help people succeed
7. Never apologize for "limitations" - focus on what you CAN tell them
8. Use numbered or bulleted lists when presenting multiple points, steps, or recommendations for clarity

AVAILABLE RESEARCH:
{formatted_papers}

CURRENT USER QUESTION: {user_question}

Provide a helpful response with:
- Direct answer with citations
- Practical recommendations (use numbered lists for multiple items)
- Actionable next steps

References:
Author et al. (Year). Title. PMID: ######"""
    
    def _get_complex_prompt(self) -> str:
        """Complex prompt template (full detail, ~450 tokens)"""
        return """You are FitFact, a knowledgeable fitness advisor who provides helpful, evidence-based guidance.

{context_section}

CRITICAL INSTRUCTIONS:
1. ALWAYS consider conversation history when answering follow-up questions
2. If this is a follow-up, maintain context from previous messages and reference them naturally
3. Use research to support practical recommendations
4. If papers don't perfectly match the question, extract relevant principles and apply them
5. Give specific numbers, guidelines, and actionable advice
6. Be confident and encouraging - you're here to help people succeed
7. Never apologize for "limitations" - focus on what you CAN tell them
8. Use numbered or bulleted lists when presenting multiple points, comparisons, or step-by-step recommendations

AVAILABLE RESEARCH:
{formatted_papers}

CURRENT USER QUESTION: {user_question}

Provide a comprehensive response that:
- Considers the conversation context (if this is a follow-up)
- Starts with a direct answer to their question
- Includes specific recommendations with numbers when possible (use lists for clarity)
- Uses evidence from the papers to support your advice
- Compares different approaches or findings when relevant (numbered lists help here)
- Addresses potential nuances or contradictions
- Ends with practical, actionable next steps (numbered lists recommended)
- Cites sources naturally as (Author et al., Year)

References:
List all cited papers with full details: Author et al. (Year). Title. PMID: ######"""
    
    def predict_complexity(self, query: str) -> Tuple[str, float, Dict]:
        """
        Predict query complexity using ML model
        
        Args:
            query: User query text
            
        Returns:
            Tuple of (complexity_label, confidence, features_dict)
        """
        # Extract features
        features = self.feature_extractor.extract_features(query)
        
        # Get feature vector in correct order
        feature_vector = []
        for col in self.feature_columns:
            if col in features:
                value = features[col]
                # Convert boolean to int
                if isinstance(value, bool):
                    value = int(value)
                feature_vector.append(value)
            else:
                feature_vector.append(0)
        
        # Reshape for prediction
        import numpy as np
        X = np.array(feature_vector).reshape(1, -1)
        
        # Scale if needed (for Logistic Regression)
        if self.scaler is not None:
            X = self.scaler.transform(X)
        
        # Predict
        prediction = self.model.predict(X)[0]
        
        # Get prediction probabilities (confidence)
        if hasattr(self.model, 'predict_proba'):
            proba = self.model.predict_proba(X)[0]
            confidence = max(proba)
        else:
            confidence = 1.0  # Default confidence
        
        return prediction, confidence, features
    
    def select_prompt(self, query: str, context_section: str = "", 
                     formatted_papers: str = "") -> Dict:
        """
        Select optimal prompt based on query complexity
        
        Args:
            query: User query text
            context_section: Conversation history
            formatted_papers: Formatted research papers
            
        Returns:
            Dict with prompt, complexity, confidence, features
        """
        # Predict complexity
        complexity, confidence, features = self.predict_complexity(query)
        
        # Get appropriate prompt template
        prompt_template = self.prompts[complexity]
        
        # Fill in the template
        prompt = prompt_template.format(
            context_section=context_section,
            formatted_papers=formatted_papers,
            user_question=query
        )
        
        # Update usage stats
        self.usage_stats[complexity] += 1
        self.usage_stats['total'] += 1
        
        # Calculate token estimate (rough)
        prompt_tokens = len(prompt.split()) * 1.3  # Rough token estimate
        
        return {
            'prompt': prompt,
            'complexity': complexity,
            'confidence': confidence,
            'features': features,
            'estimated_tokens': int(prompt_tokens),
            'usage_stats': self.usage_stats.copy()
        }
    
    def get_usage_statistics(self) -> Dict:
        """Get prompt selection statistics"""
        total = self.usage_stats['total']
        if total == 0:
            return self.usage_stats
        
        stats = self.usage_stats.copy()
        stats['percentages'] = {
            'simple': (self.usage_stats['simple'] / total) * 100,
            'medium': (self.usage_stats['medium'] / total) * 100,
            'complex': (self.usage_stats['complex'] / total) * 100
        }
        
        # Estimate token savings
        # Assume: simple saves 70, medium saves 40, complex saves 0
        simple_savings = self.usage_stats['simple'] * 70
        medium_savings = self.usage_stats['medium'] * 40
        total_savings = simple_savings + medium_savings
        
        stats['estimated_tokens_saved'] = total_savings
        stats['avg_tokens_saved_per_query'] = total_savings / total if total > 0 else 0
        
        return stats


# Test function
def test_prompt_selector():
    """Test the prompt selector with sample queries"""
    
    print("\n" + "="*80)
    print("Testing Prompt Selector")
    print("="*80)
    
    selector = PromptSelector()
    
    test_queries = [
        "What is protein?",  # Expected: simple
        "How much protein should I eat per day?",  # Expected: medium
        "Compare whey versus casein protein on muscle synthesis",  # Expected: complex
    ]
    
    for query in test_queries:
        print(f"\n{'='*80}")
        print(f"Query: {query}")
        print("-"*80)
        
        result = selector.select_prompt(query, "", "[Mock papers here]")
        
        print(f"Predicted Complexity: {result['complexity'].upper()}")
        print(f"Confidence: {result['confidence']:.2%}")
        print(f"Estimated Tokens: {result['estimated_tokens']}")
        print(f"\nKey Features:")
        print(f"  Word Count: {result['features']['word_count']}")
        print(f"  Technical Terms: {result['features']['technical_term_count']}")
        print(f"  Has Comparison: {result['features']['has_comparison']}")
    
    # Show overall stats
    print(f"\n{'='*80}")
    print("Usage Statistics")
    print("-"*80)
    stats = selector.get_usage_statistics()
    print(f"Total queries: {stats['total']}")
    print(f"  Simple: {stats['simple']} ({stats['percentages']['simple']:.1f}%)")
    print(f"  Medium: {stats['medium']} ({stats['percentages']['medium']:.1f}%)")
    print(f"  Complex: {stats['complex']} ({stats['percentages']['complex']:.1f}%)")
    print(f"\nEstimated tokens saved: {stats['estimated_tokens_saved']}")
    print(f"Avg saved per query: {stats['avg_tokens_saved_per_query']:.1f}")


if __name__ == "__main__":
    test_prompt_selector()
