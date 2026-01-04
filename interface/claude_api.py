"""
Claude API Integration for FitFact
Enhanced with structured JSON output for consistent frontend rendering
"""

import anthropic
import os
import json
import re
from dotenv import load_dotenv
from typing import List, Dict, Optional

load_dotenv()

class ClaudeProcessor:
    """Enhanced Claude API processor with structured output"""
    
    def __init__(self):
        self.client = anthropic.Anthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY")
        )
        self.model = "claude-3-haiku-20240307"
        
    def format_papers_for_prompt(self, papers: List[Dict]) -> str:
        """Format PubMed papers for Claude prompt"""
        formatted_papers = []
        papers_to_use = papers[:10] if len(papers) > 10 else papers
        
        for i, paper in enumerate(papers_to_use, 1):
            authors = paper.get('authors', [])
            if isinstance(authors, list):
                author_str = ', '.join(authors[:3])
                if len(authors) > 3:
                    author_str += ' et al.'
            else:
                author_str = str(authors) if authors else "Unknown"
            
            pub_date = paper.get('publication_date', '')
            year = pub_date.split('-')[0] if pub_date and '-' in pub_date else pub_date or "Unknown"
            
            abstract = paper.get('abstract', 'No abstract available')
            if isinstance(abstract, list):
                abstract = ' '.join(abstract)
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
        
        return "\n---\n".join(formatted_papers)
    
    def create_structured_prompt(self, user_question: str, papers: List[Dict], conversation_history: list = None) -> str:
        """Create prompt that requests structured JSON output"""
        formatted_papers = self.format_papers_for_prompt(papers)
        
        context_section = ""
        if conversation_history and len(conversation_history) > 1:
            recent_messages = conversation_history[-6:]
            context_section = "\nPREVIOUS CONVERSATION:\n"
            for msg in recent_messages[:-1]:
                role = "User" if msg['role'] == 'user' else 'FitFact'
                content = msg['content'][:200] + "..." if len(msg.get('content', '')) > 200 else msg.get('content', '')
                context_section += f"{role}: {content}\n"
        
        prompt = f"""You are FitFact, an evidence-based fitness advisor.
{context_section}
RESEARCH:
{formatted_papers}

QUESTION: {user_question}

You MUST respond with ONLY a JSON object (no markdown, no backticks, no extra text).

Format:
{{"headline":"Direct 1-2 sentence answer","points":[{{"title":"Topic Name","content":"Details with (Author, Year) citations"}}],"takeaway":"Brief action summary","references":[{{"num":1,"author":"LastName","year":"2024","title":"Paper title","journal":"Journal","pmid":"12345"}}]}}

RULES:
- 3-5 points with specific actionable advice
- Include numbers and recommendations  
- Only cite papers you reference
- Keep titles short: "Protein Timing", "Rest Days"
- Citations format: (Author et al., Year)

JSON response:"""
        
        return prompt
    
    def parse_structured_response(self, response_text: str, papers: List[Dict]) -> Dict:
        """Parse Claude's JSON response with robust fallback handling"""
        try:
            cleaned = response_text.strip()
            
            # Remove markdown code blocks
            if '```' in cleaned:
                match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', cleaned)
                if match:
                    cleaned = match.group(1)
                else:
                    cleaned = re.sub(r'```(?:json)?', '', cleaned).strip()
            
            # Try to find JSON object in response
            json_match = re.search(r'\{[\s\S]*\}', cleaned)
            if json_match:
                cleaned = json_match.group(0)
            
            data = json.loads(cleaned)
            
            # Validate and ensure references have PMIDs
            if data.get('references'):
                for ref in data['references']:
                    if not ref.get('pmid'):
                        # Try to match with actual papers
                        for paper in papers:
                            pub_date = paper.get('publication_date', '')
                            year = pub_date.split('-')[0] if '-' in pub_date else pub_date
                            if str(ref.get('year')) == str(year):
                                ref['pmid'] = paper.get('pmid', '')
                                ref['title'] = paper.get('title', ref.get('title', ''))
                                ref['journal'] = paper.get('journal', ref.get('journal', ''))
                                break
            
            if 'headline' in data:
                return {'structured': True, 'data': data}
                
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            print(f"Response was: {response_text[:500]}...")
        except Exception as e:
            print(f"Parse error: {e}")
        
        return {'structured': False, 'text': response_text}
    
    def build_references_from_papers(self, papers: List[Dict]) -> List[Dict]:
        """Build reference list from papers"""
        refs = []
        for i, paper in enumerate(papers[:6], 1):
            authors = paper.get('authors', [])
            if isinstance(authors, list):
                author = authors[0].split()[0] if authors else "Unknown"
            else:
                author = str(authors).split()[0] if authors else "Unknown"
            
            pub_date = paper.get('publication_date', '')
            year = pub_date.split('-')[0] if '-' in pub_date else pub_date or "Unknown"
            
            refs.append({
                "num": i,
                "author": author,
                "year": year,
                "title": paper.get('title', 'No title'),
                "journal": paper.get('journal', 'Unknown'),
                "pmid": paper.get('pmid', '')
            })
        return refs
    
    def format_structured_as_text(self, data: Dict) -> str:
        """Convert structured data to readable text"""
        parts = []
        
        if data.get('headline'):
            parts.append(data['headline'])
        
        if data.get('points'):
            for i, point in enumerate(data['points'], 1):
                parts.append(f"\n{i}. {point.get('title', 'Point')}: {point.get('content', '')}")
        
        if data.get('takeaway'):
            parts.append(f"\n{data['takeaway']}")
        
        if data.get('references'):
            parts.append("\n\n**References:**")
            for ref in data['references']:
                parts.append(f"{ref.get('num', '')}. {ref.get('author', '')} et al. ({ref.get('year', '')}) - \"{ref.get('title', '')}\" - {ref.get('journal', '')} - PMID: {ref.get('pmid', '')}")
        
        return '\n'.join(parts)
    
    def generate_response(self, papers: List[Dict], user_question: str, conversation_history: list = None) -> Dict:
        """Generate a structured response using Claude API"""
        try:
            prompt = self.create_structured_prompt(user_question, papers, conversation_history)
            
            message = self.client.messages.create(
                model=self.model,
                max_tokens=1500,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response_text = message.content[0].text
            print(f"[Claude] Raw response: {response_text[:300]}...")
            
            parsed = self.parse_structured_response(response_text, papers)
            
            if parsed['structured']:
                data = parsed['data']
                # Ensure references exist
                if not data.get('references'):
                    data['references'] = self.build_references_from_papers(papers)
                
                return {
                    'text': self.format_structured_as_text(data),
                    'structured_data': data,
                    'success': True,
                    'tokens_used': {
                        'input': message.usage.input_tokens,
                        'output': message.usage.output_tokens
                    }
                }
            else:
                # Fallback - build structured data from text
                print("[Claude] Falling back to text parsing")
                return {
                    'text': parsed['text'],
                    'structured_data': {
                        'headline': parsed['text'].split('.')[0] + '.' if parsed['text'] else '',
                        'points': [],
                        'takeaway': None,
                        'references': self.build_references_from_papers(papers)
                    },
                    'success': True,
                    'tokens_used': {
                        'input': message.usage.input_tokens,
                        'output': message.usage.output_tokens
                    }
                }
                
        except Exception as e:
            print(f"[Claude] Error: {e}")
            return {
                'text': f"Error generating response: {str(e)}",
                'structured_data': None,
                'success': False,
                'error': str(e)
            }
    
    def create_enhanced_prompt(self, user_question: str, papers: List[Dict], conversation_history: list = None) -> str:
        """Legacy method for backward compatibility"""
        return self.create_structured_prompt(user_question, papers, conversation_history)
    
    def extract_academic_search_terms(self, user_question: str) -> List[str]:
        """Use Claude to translate user question into academic search terms"""
        try:
            prompt = f"""Convert this fitness question into PubMed search terms.

Question: {user_question}

Provide 3-5 search queries, one per line:"""

            message = self.client.messages.create(
                model=self.model,
                max_tokens=200,
                temperature=0.2,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response = message.content[0].text.strip()
            return [line.strip() for line in response.split('\n') if line.strip()][:5]
            
        except Exception as e:
            print(f"Error extracting search terms: {e}")
            return [user_question]
    
    def validate_response(self, response: Dict) -> Dict:
        """Validate response quality"""
        if not response.get('success'):
            return {'valid': False, 'issues': ['API error']}
        
        issues = []
        if response.get('structured_data'):
            data = response['structured_data']
            if not data.get('points') or len(data.get('points', [])) < 1:
                issues.append("No points")
            if not data.get('references'):
                issues.append("No references")
        
        return {'valid': len(issues) == 0, 'issues': issues}


if __name__ == "__main__":
    processor = ClaudeProcessor()
    
    sample_papers = [{
        'pmid': '27102172',
        'title': 'Effects of Resistance Training Frequency on Muscle Hypertrophy',
        'abstract': 'This systematic review examined training frequency effects on muscle growth.',
        'authors': ['Schoenfeld BJ', 'Ogborn D', 'Krieger JW'],
        'publication_date': '2016-10-01',
        'journal': 'Sports Medicine'
    }]
    
    print("Testing structured response...")
    response = processor.generate_response(sample_papers, "How often should I train?")
    
    if response['success']:
        print("\n✅ Success!")
        if response.get('structured_data'):
            print("\nStructured:")
            print(json.dumps(response['structured_data'], indent=2))
    else:
        print(f"\n❌ Error: {response.get('error')}")
