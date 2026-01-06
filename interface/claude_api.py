"""
Claude API Integration for FitFact
Phase 3 - ML-based prompt optimization + Structured JSON output
"""

import anthropic
import os
import json
import re
from dotenv import load_dotenv
from typing import List, Dict, Optional

load_dotenv()

class ClaudeProcessor:
    """Enhanced Claude API processor with ML optimization and structured output"""
    
    def __init__(self):
        self.client = anthropic.Anthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY")
        )
        self.model = "claude-3-5-haiku-20241022"
        
        # Initialize ML-based prompt selector
        try:
            import sys
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
        """Format PubMed papers for Claude prompt"""
        formatted_papers = []
        
        for i, paper in enumerate(papers[:5], 1):
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
        
        # Use ML prompt selector if available
        if self.ml_enabled and self.prompt_selector:
            result = self.prompt_selector.select_prompt(
                query=user_question,
                context_section=context_section,
                formatted_papers=formatted_papers
            )
            
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
    
    def create_structured_prompt(self, user_question: str, papers: List[Dict], 
                                conversation_history: list = None) -> str:
        """Create prompt that requests structured JSON output"""
        formatted_papers = self.format_papers_for_prompt(papers)
        
        # Build reference list from papers for the prompt
        ref_examples = []
        for i, paper in enumerate(papers[:5], 1):
            authors = paper.get('authors', [])
            if isinstance(authors, list) and authors:
                author = authors[0].split()[0] if authors[0] else "Unknown"
            else:
                author = str(authors).split()[0] if authors else "Unknown"
            pub_date = paper.get('publication_date', '')
            year = pub_date.split('-')[0] if '-' in pub_date else pub_date or "2024"
            ref_examples.append(f'{{"num":{i},"author":"{author}","year":"{year}","title":"{paper.get("title", "Title")[:50]}","journal":"{paper.get("journal", "Journal")}","pmid":"{paper.get("pmid", "")}"}}')
        
        context_section = ""
        if conversation_history and len(conversation_history) > 1:
            recent_messages = conversation_history[-4:]
            context_section = "Previous conversation context: "
            for msg in recent_messages[:-1]:
                role = "User" if msg['role'] == 'user' else 'Assistant'
                content = msg['content'][:100] + "..." if len(msg.get('content', '')) > 100 else msg.get('content', '')
                context_section += f"{role}: {content} | "
        
        prompt = f"""You are FitFact, a fitness advisor. Answer based ONLY on the research papers provided.
{context_section}

RESEARCH PAPERS:
{formatted_papers}

USER QUESTION: {user_question}

Respond with a JSON object. Start your response with {{ and end with }}. No markdown, no backticks, no explanation before or after.

Required JSON structure:
{{
  "headline": "A clear 1-2 sentence direct answer to the question",
  "points": [
    {{"title": "Short Topic Name", "content": "Detailed explanation with (Author et al., Year) citations. Include specific numbers/recommendations."}},
    {{"title": "Another Topic", "content": "More details with citations."}}
  ],
  "takeaway": "One practical actionable recommendation",
  "references": [
    {ref_examples[0] if ref_examples else '{{"num":1,"author":"Author","year":"2024","title":"Title","journal":"Journal","pmid":"12345"}}'}
  ]
}}

IMPORTANT:
- Include 3-5 points with specific advice
- Every claim needs a citation: (Author et al., Year)
- References must include actual PMIDs from the papers above
- Start response with {{ - no other text before it"""
        
        return prompt
    
    def parse_structured_response(self, response_text: str, papers: List[Dict]) -> Dict:
        """Parse Claude's JSON response with robust fallback handling"""
        try:
            cleaned = response_text.strip()
            
            if '```' in cleaned:
                match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', cleaned)
                if match:
                    cleaned = match.group(1)
                else:
                    cleaned = re.sub(r'```(?:json)?', '', cleaned).strip()
            
            json_match = re.search(r'\{[\s\S]*\}', cleaned)
            if json_match:
                cleaned = json_match.group(0)
            
            data = json.loads(cleaned)
            
            if data.get('references'):
                for ref in data['references']:
                    if not ref.get('pmid'):
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
                parts.append(f"\n{i}. **{point.get('title', 'Point')}**: {point.get('content', '')}")
        
        if data.get('takeaway'):
            parts.append(f"\n{data['takeaway']}")
        
        if data.get('references'):
            parts.append("\n\n**References:**")
            for ref in data['references']:
                parts.append(f"{ref.get('num', '')}. {ref.get('author', '')} et al. ({ref.get('year', '')}) - \"{ref.get('title', '')}\" - {ref.get('journal', '')} - PMID: {ref.get('pmid', '')}")
        
        return '\n'.join(parts)
    
    def generate_response(self, papers: List[Dict], user_question: str, 
                         conversation_history: list = None, 
                         use_structured: bool = False) -> Dict:
        """
        Generate response with ML-optimized prompts
        
        Args:
            papers: Research papers
            user_question: User query
            conversation_history: Previous messages
            use_structured: If True, use structured JSON output (optional feature)
        """
        try:
            if use_structured:
                # Use structured JSON approach
                prompt = self.create_structured_prompt(user_question, papers, conversation_history)
                print(f"[Claude] Using structured prompt for: {user_question[:50]}...")
            else:
                # Use ML-optimized prompt approach (default)
                prompt_result = self.create_enhanced_prompt(user_question, papers, conversation_history)
                prompt = prompt_result['prompt']
            
            message = self.client.messages.create(
                model=self.model,
                max_tokens=1500,
                temperature=0.2,  # Lower temperature for more consistent JSON
                messages=[{"role": "user", "content": prompt}]
            )
            
            response_text = message.content[0].text
            print(f"[Claude] Raw response (first 200 chars): {response_text[:200]}...")
            
            # Handle structured response if requested
            if use_structured:
                parsed = self.parse_structured_response(response_text, papers)
                
                if parsed['structured']:
                    print(f"[Claude] ✅ Successfully parsed structured JSON")
                    data = parsed['data']
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
                    # Fallback - build structured data from text response
                    print(f"[Claude] ⚠️ JSON parse failed, building structured fallback")
                    text = parsed['text']
                    
                    # Extract first sentence as headline
                    sentences = text.split('. ')
                    headline = sentences[0] + '.' if sentences else text[:100]
                    
                    # Try to extract numbered points
                    points = []
                    import re
                    point_matches = re.findall(r'(\d+)\.\s*\*?\*?([^:*]+)\*?\*?:\s*([^\d]+?)(?=\d+\.|$)', text, re.DOTALL)
                    if point_matches:
                        for num, title, content in point_matches[:5]:
                            points.append({
                                'title': title.strip(),
                                'content': content.strip().replace('\n', ' ')
                            })
                    else:
                        # If no numbered points, create one point with the content
                        remaining = '. '.join(sentences[1:]) if len(sentences) > 1 else ''
                        if remaining:
                            points.append({
                                'title': 'Key Information',
                                'content': remaining[:500]
                            })
                    
                    return {
                        'text': text,
                        'structured_data': {
                            'headline': headline,
                            'points': points,
                            'takeaway': None,
                            'references': self.build_references_from_papers(papers)
                        },
                        'success': True,
                        'tokens_used': {
                            'input': message.usage.input_tokens,
                            'output': message.usage.output_tokens
                        }
                    }
            else:
                # Standard ML-optimized response
                citation_count = response_text.count("PMID:")
                
                result = {
                    'text': response_text,
                    'success': True,
                    'citations_found': citation_count,
                    'tokens_used': {
                        'input': message.usage.input_tokens,
                        'output': message.usage.output_tokens
                    }
                }
                
                # Add ML metadata if available
                if not use_structured and 'prompt_result' in locals():
                    result['ml_complexity'] = prompt_result.get('complexity', 'unknown')
                    result['ml_confidence'] = prompt_result.get('confidence', 0.0)
                    result['ml_optimized'] = prompt_result.get('ml_optimized', False)
                
                return result
                
        except Exception as e:
            print(f"[Claude] Error: {e}")
            import traceback
            traceback.print_exc()
            return {
                'text': f"Error generating response: {str(e)}",
                'success': False,
                'error': str(e)
            }
    
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
        
        # Check structured data if present
        if response.get('structured_data'):
            data = response['structured_data']
            if not data.get('points') or len(data.get('points', [])) < 1:
                issues.append("No points")
            if not data.get('references'):
                issues.append("No references")
        else:
            # Check text-based response
            text = response.get('text', '')
            
            if response.get('citations_found', 0) < 1:
                issues.append("No citations found in response")
            
            if "Reference" not in text and "PMID" not in text:
                issues.append("No references section found")
            
            word_count = len(text.split())
            if word_count < 150:
                issues.append(f"Response too short: {word_count} words")
            elif word_count > 400:
                issues.append(f"Response too long: {word_count} words")
        
        return {'valid': len(issues) == 0, 'issues': issues}
    
    def get_ml_stats(self) -> Dict:
        """Get ML prompt selector statistics"""
        if self.ml_enabled and self.prompt_selector:
            return self.prompt_selector.get_usage_statistics()
        return None


# Test function
def test_refined_claude():
    """Test Claude processor with ML optimization"""
    
    processor = ClaudeProcessor()
    
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