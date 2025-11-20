"""
Query Processor - Integrates PubMed → Database → Claude Pipeline
Week 3
Complete with error handling and rate limiting
"""

import sys
sys.path.append('database_files')
from database import FitFactDB
import anthropic
import os
import time
from dotenv import load_dotenv

load_dotenv()

class QueryProcessor:
    """Handles complete query pipeline from user question to cited response"""
    
    def __init__(self):
        """Initialize database and Claude API connections with error handling"""
        print("Initializing Query Processor...")
        
        try:
            self.db = FitFactDB()
            print("✓ Database connected")
        except Exception as e:
            print(f"✗ Database connection failed: {e}")
            raise
        
        try:
            api_key = os.getenv('CLAUDE_API_KEY')
            if not api_key:
                raise ValueError("CLAUDE_API_KEY not found in .env file")
            
            self.claude = anthropic.Anthropic(api_key=api_key)
            print("✓ Claude API initialized")
        except Exception as e:
            print(f"✗ Claude API initialization failed: {e}")
            self.db.close()
            raise
        
        # Rate limiting
        self.last_api_call = 0
        self.min_api_interval = 1.0
        
        print("✓ All connections successful\n")
    
    def _extract_keywords(self, query_text):
        """Extract key fitness terms from question"""
        import re
        query_text = re.sub(r'[^\w\s]', '', query_text)
        
        stopwords = ['what', 'are', 'the', 'of', 'for', 'is', 'how', 'does', 'can', 'will', 
                     'should', 'would', 'do', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at',
                     'my', 'me', 'i', 'to', 'from', 'with', 'about', 'when', 'where', 'why']
        
        words = query_text.lower().split()
        keywords = [w for w in words if w not in stopwords and len(w) > 2]
        
        return keywords
    
    def _enforce_rate_limit(self):
        """Enforce rate limiting for API calls"""
        current_time = time.time()
        time_since_last_call = current_time - self.last_api_call
        
        if time_since_last_call < self.min_api_interval:
            wait_time = self.min_api_interval - time_since_last_call
            print(f"⏳ Rate limiting: waiting {wait_time:.2f}s...")
            time.sleep(wait_time)
        
        self.last_api_call = time.time()
    
    def search_papers(self, query_text, limit=5):
        """Search database for relevant papers with error handling"""
        print(f"Searching database for: '{query_text}'")
        
        try:
            keywords = self._extract_keywords(query_text)
            print(f"Keywords: {keywords}")
            
            if not keywords:
                print("⚠ No keywords extracted")
                return []
            
            like_conditions = " OR ".join([f"(title ILIKE '%{kw}%' OR abstract ILIKE '%{kw}%')" for kw in keywords])
            
            query = f"""
                SELECT paper_id, pmid, title, abstract, journal_name, publication_date, authors
                FROM research_papers
                WHERE {like_conditions}
                LIMIT {limit}
            """
            
            self.db.cursor.execute(query)
            results = self.db.cursor.fetchall()
            
            papers = []
            for row in results:
                papers.append({
                    'paper_id': row['paper_id'],
                    'pmid': row['pmid'],
                    'title': row['title'],
                    'abstract': row['abstract'],
                    'journal': row['journal_name'],
                    'pub_date': str(row['publication_date']),
                    'authors': row['authors']
                })
            
            print(f"✓ Found {len(papers)} relevant papers\n")
            return papers
            
        except Exception as e:
            print(f"✗ Database search error: {e}")
            return []
    
    def generate_response(self, user_question, papers):
        """Generate response using Claude with error handling and rate limiting"""
        print("Generating response with Claude API...")
        
        context = self._build_context(papers)
        
        prompt = f"""You are a scientific fitness advisor. Answer the user's question based ONLY on the research papers provided below. Always cite sources using [Author et al., Year, PMID: xxxxx] format.

USER QUESTION: {user_question}

RELEVANT RESEARCH PAPERS:
{context}

INSTRUCTIONS:
1. Provide an evidence-based answer
2. Cite specific papers for each claim
3. Mention any conflicting evidence if present
4. Keep response concise (200-300 words)
5. If papers don't fully address the question, acknowledge limitations

ANSWER:"""
        
        try:
            # Enforce rate limiting
            self._enforce_rate_limit()
            
            message = self.claude.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}],
                timeout=30.0
            )
            
            response_text = message.content[0].text
            tokens_used = message.usage.input_tokens + message.usage.output_tokens
            
            print(f"✓ Response generated ({tokens_used} tokens)\n")
            
            return response_text, tokens_used
            
        except anthropic.APIError as e:
            print(f"✗ Claude API error: {e}")
            return "Error: Unable to generate response due to API failure. Please try again later.", 0
        except anthropic.APITimeoutError:
            print(f"✗ Claude API timeout")
            return "Error: Response generation timed out. Please try again with a simpler question.", 0
        except Exception as e:
            print(f"✗ Unexpected error during response generation: {e}")
            return f"Error: {str(e)}", 0
    
    def _build_context(self, papers):
        """Format papers as context for Claude"""
        context_parts = []
        
        for i, paper in enumerate(papers, 1):
            authors = paper.get('authors', ['Unknown'])
            if isinstance(authors, str):
                authors = [authors]
            authors_str = ", ".join(authors[:3])
            
            year = str(paper.get('pub_date', 'Unknown'))[:4]
            
            context_parts.append(f"""
[{i}] {paper['title']}
Authors: {authors_str}
Journal: {paper['journal']} ({year})
PMID: {paper['pmid']}
Abstract: {paper['abstract'][:500]}...
""")
        
        return "\n".join(context_parts)
    
    def process_query(self, user_question):
        """Complete pipeline with comprehensive error handling"""
        print("="*60)
        print("PROCESSING QUERY")
        print("="*60)
        print(f"Question: {user_question}\n")
        
        try:
            papers = self.search_papers(user_question, limit=5)
            
            if not papers:
                return "I couldn't find relevant research papers for your question. Please try rephrasing or ask about a different fitness topic."
            
            response, tokens = self.generate_response(user_question, papers)
            
            sys.path.append('src/llm')
            from citation_formatter import format_for_response
            references = format_for_response(papers)
            
            full_response = f"{response}\n\n{'='*60}\nREFERENCES:\n{references}"
            
            self.db.log_query(user_question, cache_hit=False, response_time_ms=0)
            
            print("="*60)
            print("RESPONSE READY")
            print("="*60)
            
            return full_response
            
        except Exception as e:
            print(f"✗ Pipeline error: {e}")
            return f"Error processing your question: {str(e)}"
    
    def close(self):
        """Close database connection"""
        try:
            self.db.close()
        except:
            pass


if __name__ == "__main__":
    try:
        processor = QueryProcessor()
        
        question = "What are the benefits of creatine supplementation for muscle growth?"
        
        response = processor.process_query(question)
        
        print("\n" + "="*60)
        print("FINAL RESPONSE:")
        print("="*60)
        print(response)
        print("="*60)
        
        processor.close()
        
    except Exception as e:
        print(f"\n✗ Fatal error: {e}")