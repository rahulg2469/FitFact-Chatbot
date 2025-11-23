"""
Claude API Integration for FitFact
Week 2 - Enhanced prompt engineering and response handling
Author: Satya (completing Rahul's tasks)
"""

import anthropic
import os
import json
from dotenv import load_dotenv
from typing import List, Dict, Optional

load_dotenv()

class ClaudeProcessor:
    """Enhanced Claude API processor for FitFact responses"""
    
    def __init__(self):
        self.client = anthropic.Anthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY")
        )
        self.model = "claude-3-5-haiku-20241022"
        
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
    
    def create_enhanced_prompt(self, user_question: str, papers: List[Dict]) -> str:
        """
        Create an enhanced prompt with better instructions and structure
        """
        formatted_papers = self.format_papers_for_prompt(papers)
        
        prompt = f"""You are FitFact, an AI fitness advisor that ONLY provides evidence-based responses using peer-reviewed research.

STRICT REQUIREMENTS:
1. Answer ONLY based on the provided research papers below
2. Every claim must cite the source: (First Author et al., Year)
3. If the papers don't fully answer the question, explicitly state what's missing
4. Synthesize findings across multiple papers when relevant
5. Highlight any conflicting findings between studies
6. Keep response between 200-300 words
7. Use clear, accessible language

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
        
        return prompt
    
    def generate_response(self, papers: List[Dict], user_question: str) -> Dict:
        """
        Generate a response using Claude API with enhanced error handling
        """
        try:
            # Create the enhanced prompt
            prompt = self.create_enhanced_prompt(user_question, papers)
            
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
                }
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

# Test function
def test_refined_claude():
    """Test the refined Claude processor with sample data"""
    
    processor = ClaudeProcessor()
    
    # Load sample papers from pubmed_papers_sample.json if it exists
    sample_papers = []
    if os.path.exists('data/pubmed_papers_sample.json'):
        with open('data/pubmed_papers_sample.json', 'r') as f:
            sample_papers = json.load(f)[:3]  # Use first 3 papers
    else:
        # Use mock data if file doesn't exist
        sample_papers = [
            {
                'pmid': '27102172',
                'title': 'Effects of Resistance Training Frequency on Muscle Hypertrophy',
                'abstract': 'This systematic review examined training frequency effects...',
                'authors': ['Schoenfeld BJ', 'Ogborn D', 'Krieger JW'],
                'publication_date': '2016-10-01',
                'journal': 'Sports Medicine',
                'keywords': ['Resistance Training', 'Muscle Hypertrophy']
            }
        ]
    
    test_question = "How often should I train each muscle group for optimal muscle growth?"
    
    print("🧪 Testing Claude Processor")
    print("=" * 60)
    print(f"Question: {test_question}")
    print(f"Papers loaded: {len(sample_papers)}")
    print("=" * 60)
    
    # Generate response
    print("\n🤖 Generating response...")
    response = processor.generate_response(sample_papers, test_question)
    
    if response['success']:
        print("\n✅ Response generated successfully!")
        print("-" * 60)
        print(response['text'])
        print("-" * 60)
        
        # Validate response
        validation = processor.validate_response(response)
        print(f"\n📊 Validation Results:")
        print(f"  Valid: {validation['valid']}")
        print(f"  Word count: {validation['word_count']}")
        print(f"  Citations: {validation['citations']}")
        if validation['issues']:
            print(f"  Issues: {', '.join(validation['issues'])}")
        
        print(f"\n💰 Token Usage:")
        print(f"  Input: {response['tokens_used']['input']}")
        print(f"  Output: {response['tokens_used']['output']}")
    else:
        print(f"\n❌ Error: {response['error']}")

if __name__ == "__main__":
    test_refined_claude()