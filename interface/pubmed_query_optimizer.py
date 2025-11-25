"""
PubMed Query Optimizer for FitFact
Week 3, Task 3 - Optimize PubMed search query generation
Translates everyday fitness language to academic search terms
"""

import re
from typing import List, Dict, Tuple

class PubMedQueryOptimizer:
    """Optimizes user queries for PubMed searches"""
    
    def __init__(self):
        # Map common terms to academic/medical equivalents
        self.term_mappings = {
            # Exercise types
            'workout': 'exercise training resistance training physical activity',
            'cardio': 'cardiovascular exercise aerobic training endurance exercise',
            'weights': 'resistance training strength training resistance exercise',
            'lifting': 'resistance training weightlifting strength training',
            'hiit': 'high intensity interval training HIIT interval training',
            'running': 'running aerobic exercise endurance training',
            
            # Body composition
            'fat loss': 'weight loss body fat reduction adipose tissue',
            'muscle gain': 'muscle hypertrophy lean mass muscle growth',
            'getting ripped': 'body composition muscle definition fat loss',
            'bulk': 'muscle mass hypertrophy weight gain',
            'cut': 'caloric deficit fat loss body composition',
            'shredded': 'body fat percentage muscle definition',
            
            # Nutrition
            'protein': 'protein dietary protein protein supplementation',
            'carbs': 'carbohydrate CHO glycogen',
            'pre workout': 'pre-exercise supplementation ergogenic aid',
            'post workout': 'post-exercise nutrition recovery nutrition',
            'supplements': 'dietary supplementation nutritional supplements',
            
            # Frequency/timing
            'how often': 'frequency training frequency exercise frequency',
            'how many times': 'frequency weekly frequency training volume',
            'daily': 'daily frequency everyday',
            'weekly': 'weekly frequency per week',
            
            # General terms
            'best': 'optimal effective recommended',
            'ideal': 'optimal recommended appropriate',
            'good for': 'benefits effects efficacy',
        }
        
        # MeSH terms for better PubMed matching
        self.mesh_terms = {
            'exercise': 'Exercise[MeSH]',
            'nutrition': 'Nutritional Sciences[MeSH]',
            'muscle': 'Muscle, Skeletal[MeSH]',
            'protein': 'Dietary Proteins[MeSH]',
            'training': 'Resistance Training[MeSH]',
            'weight loss': 'Weight Loss[MeSH]',
            'diet': 'Diet[MeSH]',
            'supplementation': 'Dietary Supplements[MeSH]'
        }
        
    def optimize_query(self, user_query: str) -> Dict:
        """
        Optimize a user query for PubMed search
        
        Returns:
            Dict with multiple search strategies
        """
        query_lower = user_query.lower()
        
        # Strategy 1: Direct academic translation
        academic_query = self._translate_to_academic(query_lower)
        
        # Strategy 2: MeSH term enhancement
        mesh_query = self._add_mesh_terms(academic_query)
        
        # Strategy 3: Systematic review focus
        review_query = f"{academic_query} AND (systematic review OR meta-analysis)"
        
        # Strategy 4: Recent research (last 5 years)
        recent_query = f"{academic_query} AND 2019:2024[dp]"
        
        # Strategy 5: Build Boolean query
        boolean_query = self._build_boolean_query(query_lower)
        
        return {
            'original': user_query,
            'academic': academic_query,
            'mesh_enhanced': mesh_query,
            'review_focused': review_query,
            'recent_only': recent_query,
            'boolean': boolean_query,
            'search_strategies': [
                academic_query,  # Try this first
                mesh_query,       # Then this
                boolean_query     # Fallback
            ]
        }
    
    def _translate_to_academic(self, query: str) -> str:
        """Translate everyday terms to academic language"""
        result = query
        
        # Replace common terms with academic equivalents
        for common, academic in self.term_mappings.items():
            if common in result:
                # Use OR to include both terms
                result = result.replace(common, f"({academic})")
        
        return result
    
    def _add_mesh_terms(self, query: str) -> str:
        """Add MeSH terms to improve search precision"""
        enhanced = query
        
        for term, mesh in self.mesh_terms.items():
            if term in query.lower():
                enhanced = f"{enhanced} OR {mesh}"
        
        return enhanced
    
    def _build_boolean_query(self, query: str) -> str:
        """Build a Boolean query for PubMed"""
        # Extract key concepts
        concepts = []
        
        # Check for nutrition terms
        if any(term in query for term in ['protein', 'carb', 'fat', 'diet', 'nutrition']):
            concepts.append('(nutrition OR diet OR macronutrient)')
        
        # Check for exercise terms  
        if any(term in query for term in ['workout', 'exercise', 'training', 'cardio', 'weights']):
            concepts.append('(exercise OR training OR physical activity)')
        
        # Check for outcome terms
        if any(term in query for term in ['loss', 'gain', 'build', 'burn']):
            concepts.append('(body composition OR weight change)')
        
        # Combine with AND
        if concepts:
            return ' AND '.join(concepts)
        
        return query
    
    def extract_research_focus(self, query: str) -> List[str]:
        """Extract the main research focus areas from query"""
        focuses = []
        
        query_lower = query.lower()
        
        # Identify focus areas
        if 'how many' in query_lower or 'how often' in query_lower:
            focuses.append('frequency')
            focuses.append('training volume')
        
        if 'protein' in query_lower or 'carb' in query_lower:
            focuses.append('macronutrient')
            focuses.append('nutrition')
        
        if 'fat loss' in query_lower or 'weight loss' in query_lower:
            focuses.append('weight management')
            focuses.append('body composition')
        
        if 'muscle' in query_lower or 'strength' in query_lower:
            focuses.append('hypertrophy')
            focuses.append('resistance training')
        
        return focuses

# Test the optimizer
if __name__ == "__main__":
    optimizer = PubMedQueryOptimizer()
    
    test_queries = [
        "Weekly workout frequency for fat loss?",
        "How much protein should I eat to build muscle?",
        "Is HIIT better than cardio for losing weight?",
        "Best supplements for muscle gain?"
    ]
    
    print("🔍 PubMed Query Optimization Tests")
    print("=" * 70)
    
    for query in test_queries:
        print(f"\n📝 Original: {query}")
        optimized = optimizer.optimize_query(query)
        print(f"🎯 Academic: {optimized['academic'][:100]}...")
        print(f"🏷️ MeSH: {optimized['mesh_enhanced'][:100]}...")
        print(f"📚 Reviews: {optimized['review_focused'][:100]}...")
        focuses = optimizer.extract_research_focus(query)
        print(f"🔬 Focus Areas: {', '.join(focuses)}")