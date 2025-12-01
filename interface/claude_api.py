"""
Claude API Integration for FitFact
Week 2 - Enhanced prompt engineering and response handling
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
        self.model = "claude-3-haiku-20240307"  # Use stable Haiku model
        
    def format_papers_for_prompt(self, papers: List[Dict]) -> str:
        """
        Format PubMed papers for Claude prompt
        Handles actual data structure from pubmed_fetcher.py
        """
        formatted_papers = []
        
        # Use up to 10 papers for Claude (to stay within token limits)
        # But prioritize diversity - try to get different perspectives
        papers_to_use = papers[:10] if len(papers) > 10 else papers
        
        for i, paper in enumerate(papers_to_use, 1):
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
            if len(abstract) > 600:
                abstract = abstract[:600] + "..."
            
            formatted_papers.append(f"""
PAPER {i}:
PMID: {paper.get('pmid', 'Unknown')}
Title: {paper.get('title', 'No title')}
Authors: {author_str}
Year: {year}
Journal: {paper.get('journal', 'Unknown')}
Abstract: {abstract}
            """)
        
        # Add a note if we have more papers available
        if len(papers) > 10:
            formatted_papers.append(f"\nNote: {len(papers)-10} additional papers available but not shown for brevity.")
        
        return "\n---\n".join(formatted_papers)
    
    def create_enhanced_prompt(self, user_question: str, papers: List[Dict], conversation_history: list = None) -> str:
        """
        Create a prompt with conversation context
        """
        formatted_papers = self.format_papers_for_prompt(papers)
    
        # Build conversation context
        context_section = ""
        if conversation_history and len(conversation_history) > 1:
            # Get last 10 messages (limit for token management)
            recent_messages = conversation_history[-10:]
        
            context_section = "\nCONVERSATION HISTORY:\n"
            for msg in recent_messages[:-1]:  # Exclude current message
                role = "User" if msg['role'] == 'user' else 'FitFact'
                content = msg['content']
                # Truncate long bot responses to save tokens
                if msg['role'] == 'assistant' and len(content) > 150:
                    content = content[:150] + "..."
                context_section += f"{role}: {content}\n"
            context_section += "\n"
    
        prompt = f"""You are FitFact, a knowledgeable fitness advisor who provides helpful, evidence-based guidance.
        {context_section}
        CRITICAL INSTRUCTIONS:
        1. ALWAYS consider the conversation history when answering follow-up questions
        2. If this is a follow-up, maintain context from previous messages and reference them naturally
        3. Use research to support practical recommendations
        4. If papers don't perfectly match the question, extract relevant principles and apply them
        5. Give specific numbers, guidelines, and actionable advice
        6. Be confident and encouraging - you're here to help people succeed
        7. Never apologize for "limitations" - focus on what you CAN tell them

        AVAILABLE RESEARCH:
        {formatted_papers}

        CURRENT USER QUESTION: {user_question}

        Provide a helpful response that:
        - Considers the conversation context (if this is a follow-up)
        - Starts with a direct answer to their question
        - Includes specific recommendations with numbers when possible
        - Uses evidence from the papers to support your advice
        - Ends with practical, actionable next steps
        - Cites sources naturally as (Author et al., Year)

        Your helpful response:"""
    
        return prompt
    
    def generate_response(self, papers: List[Dict], user_question: str, conversation_history: list = None) -> Dict:
        """
        Generate a response using Claude API with enhanced error handling
        """
        try:
            # Create the enhanced prompt
            prompt = self.create_enhanced_prompt(user_question, papers, conversation_history)
            
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
    
    def extract_academic_search_terms(self, user_question: str) -> List[str]:
        """
        Use Claude to translate user question into academic search terms
        """
        try:
            prompt = f"""Convert this fitness question into academic/medical search terms for PubMed.

User question: {user_question}

Provide 3-5 different search queries that would find relevant research papers. Include:
1. Medical/academic terminology
2. Common synonyms and related terms
3. MeSH terms when applicable

Format your response as a simple list, one search query per line, nothing else:"""

            message = self.client.messages.create(
                model=self.model,
                max_tokens=200,
                temperature=0.2,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            # Parse the response into search terms
            response = message.content[0].text.strip()
            search_terms = [line.strip() for line in response.split('\n') if line.strip()]
            
            return search_terms[:5]  # Return max 5 search terms
            
        except Exception as e:
            print(f"Error extracting search terms: {e}")
            # Fallback to basic extraction
            return [user_question]
    
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
    
    # Test search term extraction
    test_question = "What's the ideal daily protein intake for fat loss?"
    print("🧪 Testing Academic Search Term Extraction")
    print("=" * 60)
    print(f"User Question: {test_question}")
    
    search_terms = processor.extract_academic_search_terms(test_question)
    print("\n📚 Academic Search Terms:")
    for term in search_terms:
        print(f"  - {term}")
    
    print("\n" + "=" * 60)
    
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
    
    print("\n🤖 Testing Response Generation")
    print("=" * 60)
    print(f"Question: {test_question}")
    print(f"Papers loaded: {len(sample_papers)}")
    
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