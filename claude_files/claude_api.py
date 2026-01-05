"""
Claude API Integration for FitFact
Phase 3 - ML-based prompt optimization integrated
"""

import anthropic
import os
import json
from dotenv import load_dotenv
from typing import List, Dict, Optional

load_dotenv()

class ClaudeProcessor:
    """Enhanced Claude API processor with ML-based prompt optimization"""
    
    def __init__(self):
        self.client = anthropic.Anthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY")
        )
        self.model = "claude-3-5-haiku-20241022"
        
        # NEW: Initialize ML-based prompt selector
        try:
            import sys
            # Add parent directory to path for imports
            parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            if parent_dir not in sys.path:
                sys.path.insert(0, parent_dir)
            
            from ml_optimizer.prompt_selector import PromptSelector
            self.prompt_selector = PromptSelector()
            print("✅ ML Prompt Selector initialized")
            self.ml_enabled = True
        except Exception as e:
            print(f"⚠️ Could not load ML Prompt Selector: {e}")
            print("   Falling back to default prompts")
            self.prompt_selector = None
            self.ml_enabled = False
        
    def format_papers_for_prompt(self, papers: List[Dict]) -> str:
        """
        Format PubMed papers for Claude prompt
        Handles actual data structure from pubmed_fetcher.py
        """
        formatted_papers = []
        
        for i, paper in enumerate(papers[:5], 1):  # Limit to top 5 papers
            # Handle authors - could be list or string
            authors = paper.get('authors', [])
            if isinstance(authors, list):
                author_str = ', '.join(authors[:3])
                if len(authors) > 3:
                    author_str += ' et al.'
            else:
                author_str = str(authors) if authors else "Unknown"
            
            # Extract year from publication_date
            pub_date = paper.get('publication_date', '')
            if pub_date and '-' in pub_date:
                year = pub_date.split('-')[0]
            else:
                year = pub_date or "Unknown"
            
            # Handle abstract - might be string or list
            abstract = paper.get('abstract', 'No abstract available')
            if isinstance(abstract, list):
                abstract = ' '.join(abstract)
            
            # Truncate very long abstracts
            if len(abstract) > 800:
                abstract = abstract[:800] + "..."
            
            formatted_papers.append(f"""
PAPER {i}:
PMID: {paper.get('pmid', 'Unknown')}
Title: {paper.get('title', 'No title')}
Authors: {author_str}
Year: {year}
Journal: {paper.get('journal', 'Unknown')}
Keywords: {', '.join(paper.get('keywords', [])[:5])}
Abstract: {abstract}
            """)
        
        return "\n---\n".join(formatted_papers)
    
    def create_enhanced_prompt(self, user_question: str, papers: List[Dict], 
                              conversation_history: list = None) -> Dict:
        """
        Create prompt with ML-based complexity detection
        Returns dict with prompt and metadata
        """
        formatted_papers = self.format_papers_for_prompt(papers)
        
        # Build conversation context
        context_section = ""
        if conversation_history and len(conversation_history) > 1:
            recent_messages = conversation_history[-10:]
            context_section = "\nCONVERSATION HISTORY:\n"
            for msg in recent_messages[:-1]:
                role = "User" if msg['role'] == 'user' else 'FitFact'
                content = msg['content']
                if msg['role'] == 'assistant' and len(content) > 150:
                    content = content[:150] + "..."
                context_section += f"{role}: {content}\n"
            context_section += "\n"
        
        # NEW: Use ML prompt selector if available
        if self.ml_enabled and self.prompt_selector:
            result = self.prompt_selector.select_prompt(
                query=user_question,
                context_section=context_section,
                formatted_papers=formatted_papers
            )
            
            # Log the selection for monitoring
            print(f"🤖 ML Prompt Selected: {result['complexity'].upper()} "
                  f"(confidence: {result['confidence']:.1%}, "
                  f"~{result['estimated_tokens']} tokens)")
            
            return {
                'prompt': result['prompt'],
                'complexity': result['complexity'],
                'confidence': result['confidence'],
                'ml_optimized': True
            }
        
        # FALLBACK: Use default medium-complexity prompt if ML not available
        else:
            prompt = f"""You are FitFact, an AI fitness advisor that ONLY provides evidence-based responses using peer-reviewed research.

STRICT REQUIREMENTS:
1. Answer ONLY based on the provided research papers below
2. Every claim must cite the source: (First Author et al., Year)
3. If the papers don't fully answer the question, explicitly state what's missing
4. Synthesize findings across multiple papers when relevant
5. Highlight any conflicting findings between studies
6. Keep response between 200-300 words
7. Use clear, accessible language
8. Use numbered or bulleted lists when presenting multiple points for clarity

RESEARCH PAPERS:
{formatted_papers}

USER QUESTION: {user_question}

RESPONSE STRUCTURE:
1. Direct answer to the question
2. Supporting evidence from the papers (with citations)
3. Any limitations or caveats
4. Practical takeaway (if applicable)

References:
List all cited papers in format: Author et al. (Year). Title. PMID: ######

Your evidence-based response:"""
            
            return {
                'prompt': prompt,
                'complexity': 'medium',
                'confidence': 1.0,
                'ml_optimized': False
            }
    
    def generate_response(self, papers: List[Dict], user_question: str, 
                         conversation_history: list = None) -> Dict:
        """
        Generate a response using Claude API with ML-optimized prompts
        """
        try:
            # Create the prompt (now returns dict with metadata)
            prompt_result = self.create_enhanced_prompt(user_question, papers, conversation_history)
            prompt = prompt_result['prompt']
            
            # Call Claude API
            message = self.client.messages.create(
                model=self.model,
                max_tokens=1500,
                temperature=0.3,  # Lower temperature for more factual responses
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            response_text = message.content[0].text
            
            # Extract citations count for validation
            citation_count = response_text.count("PMID:")
            
            return {
                'text': response_text,
                'success': True,
                'citations_found': citation_count,
                'tokens_used': {
                    'input': message.usage.input_tokens,
                    'output': message.usage.output_tokens
                },
                # NEW: Include ML metadata
                'ml_complexity': prompt_result.get('complexity', 'unknown'),
                'ml_confidence': prompt_result.get('confidence', 0.0),
                'ml_optimized': prompt_result.get('ml_optimized', False)
            }
            
        except Exception as e:
            return {
                'text': f"Error generating response: {str(e)}",
                'success': False,
                'error': str(e)
            }
    
    def validate_response(self, response: Dict) -> Dict:
        """
        Validate that the response meets quality criteria
        """
        if not response['success']:
            return {'valid': False, 'issues': ['API error occurred']}
        
        text = response['text']
        issues = []
        
        # Check for citations
        if response['citations_found'] < 1:
            issues.append("No citations found in response")
        
        # Check for references section
        if "Reference" not in text and "PMID" not in text:
            issues.append("No references section found")
        
        # Check response length
        word_count = len(text.split())
        if word_count < 150:
            issues.append(f"Response too short: {word_count} words")
        elif word_count > 400:
            issues.append(f"Response too long: {word_count} words")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'word_count': word_count,
            'citations': response['citations_found']
        }
    
    def get_ml_stats(self) -> Dict:
        """Get ML prompt selector statistics"""
        if self.ml_enabled and self.prompt_selector:
            return self.prompt_selector.get_usage_statistics()
        return None

# Test function
def test_refined_claude():
    """Test the refined Claude processor with ML optimization"""
    
    processor = ClaudeProcessor()
    
    # Load sample papers
    sample_papers = [
        {
            'pmid': '27102172',
            'title': 'Effects of Resistance Training Frequency on Muscle Hypertrophy',
            'abstract': 'This systematic review examined training frequency effects on muscle hypertrophy in trained individuals. Results indicated that training each muscle group 2-3 times per week produced superior hypertrophy outcomes compared to once-weekly training.',
            'authors': ['Schoenfeld BJ', 'Ogborn D', 'Krieger JW'],
            'publication_date': '2016-10-01',
            'journal': 'Sports Medicine',
            'keywords': ['Resistance Training', 'Muscle Hypertrophy']
        }
    ]
    
    # Test with different complexity questions
    test_questions = [
        ("What is protein?", "simple"),
        ("How much protein should I eat per day?", "medium"),
        ("Compare the effects of whey versus casein protein on muscle protein synthesis in resistance-trained individuals", "complex")
    ]
    
    print("🧪 Testing Claude Processor with ML Optimization")
    print("=" * 80)
    
    for question, expected_complexity in test_questions:
        print(f"\n{'='*80}")
        print(f"Question: {question}")
        print(f"Expected Complexity: {expected_complexity.upper()}")
        print("-" * 80)
        
        response = processor.generate_response(sample_papers, question)
        
        if response['success']:
            print(f"\n✅ Response generated!")
            print(f"   ML Complexity: {response.get('ml_complexity', 'N/A').upper()}")
            print(f"   ML Confidence: {response.get('ml_confidence', 0):.1%}")
            print(f"   ML Optimized: {response.get('ml_optimized', False)}")
            print(f"   Input tokens: {response['tokens_used']['input']}")
            print(f"   Output tokens: {response['tokens_used']['output']}")
            print(f"   Total tokens: {sum(response['tokens_used'].values())}")
        else:
            print(f"\n❌ Error: {response.get('error', 'Unknown')}")
    
    # Show ML stats
    print(f"\n{'='*80}")
    print("ML Prompt Selection Statistics")
    print("-" * 80)
    stats = processor.get_ml_stats()
    if stats:
        print(f"Total queries: {stats['total']}")
        print(f"  Simple: {stats['simple']} ({stats['percentages']['simple']:.1f}%)")
        print(f"  Medium: {stats['medium']} ({stats['percentages']['medium']:.1f}%)")
        print(f"  Complex: {stats['complex']} ({stats['percentages']['complex']:.1f}%)")
        print(f"\nEstimated tokens saved: {stats['estimated_tokens_saved']}")
        print(f"Avg saved per query: {stats['avg_tokens_saved_per_query']:.1f}")
    else:
        print("ML optimization not enabled")

if __name__ == "__main__":
    test_refined_claude()
