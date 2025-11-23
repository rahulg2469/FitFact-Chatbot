"""
Query Processor - Hybrid PubMed + Database System
Week 4 - Real-time PubMed search with database fallback and detail levels
"""

import sys
sys.path.append('database_files')
sys.path.append('src/etl')
from database import FitFactDB
import anthropic
import os
import time
import requests
import xml.etree.ElementTree as ET
from dotenv import load_dotenv

load_dotenv()

class QueryProcessor:
    """Handles complete query pipeline with live PubMed + database fallback"""
    
    def __init__(self):
        """Initialize database and Claude API connections"""
        print("Initializing Hybrid Query Processor...")
        
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
        
        # PubMed API config
        self.pubmed_api_key = os.getenv('PUBMED_API_KEY')
        self.pubmed_email = os.getenv('PUBMED_EMAIL')
        self.esearch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        self.efetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        
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
                     'my', 'me', 'i', 'to', 'from', 'with', 'about', 'when', 'where', 'why',
                     'tell']
        
        words = query_text.lower().split()
        keywords = [w for w in words if w not in stopwords and len(w) > 2]
        
        return keywords
    
    def _search_pubmed_live(self, keywords, max_results=5):
        """Search PubMed API in real-time"""
        print(" Attempting live PubMed search...")
        
        try:
            search_term = " ".join(keywords)
            
            params = {
                'db': 'pubmed',
                'term': search_term,
                'retmax': max_results,
                'retmode': 'xml',
                'api_key': self.pubmed_api_key,
                'email': self.pubmed_email
            }
            
            response = requests.get(self.esearch_url, params=params, timeout=10)
            response.raise_for_status()
            
            if '<html' in response.text.lower():
                print(" PubMed is under maintenance")
                return None
            
            root = ET.fromstring(response.content)
            id_list = root.find('.//IdList')
            
            if id_list is None:
                print(" No papers found on PubMed")
                return []
            
            pmids = [id_elem.text for id_elem in id_list.findall('Id')]
            print(f"✓ Found {len(pmids)} papers on PubMed")
            
            papers = []
            for pmid in pmids[:max_results]:
                paper = self._fetch_pubmed_paper(pmid)
                if paper:
                    try:
                        self.db.save_paper(
                            pmid=paper['pmid'],
                            title=paper['title'],
                            abstract=paper['abstract'],
                            authors=paper['authors'],
                            pub_date=paper['pub_date'],
                            journal=paper['journal'],
                            study_type='Research Article'
                        )
                        print(f"  ✓ Cached paper {pmid} to database")
                    except:
                        pass
                    
                    papers.append(paper)
                time.sleep(0.34)
            
            return papers
            
        except requests.Timeout:
            print(" PubMed API timeout")
            return None
        except requests.RequestException as e:
            print(f"⚠ PubMed API error: {e}")
            return None
        except Exception as e:
            print(f"⚠ Unexpected error searching PubMed: {e}")
            return None
    
    def _fetch_pubmed_paper(self, pmid):
        """Fetch single paper from PubMed"""
        try:
            params = {
                'db': 'pubmed',
                'id': pmid,
                'rettype': 'abstract',
                'retmode': 'xml',
                'api_key': self.pubmed_api_key,
                'email': self.pubmed_email
            }
            
            response = requests.get(self.efetch_url, params=params, timeout=10)
            response.raise_for_status()
            
            root = ET.fromstring(response.content)
            article = root.find('.//Article')
            
            if article is None:
                return None
            
            title_elem = article.find('.//ArticleTitle')
            title = title_elem.text if title_elem is not None else "No title"
            
            abstract_parts = article.findall('.//AbstractText')
            abstract = " ".join([part.text or "" for part in abstract_parts]) if abstract_parts else "No abstract"
            
            journal_elem = article.find('.//Journal/Title')
            journal = journal_elem.text if journal_elem is not None else "Unknown"
            
            pub_date = article.find('.//Journal/JournalIssue/PubDate')
            year = "Unknown"
            if pub_date is not None:
                year_elem = pub_date.find('Year')
                year = year_elem.text if year_elem is not None else "Unknown"
            
            authors = []
            author_list = article.findall('.//Author')
            for author in author_list[:3]:
                lastname = author.find('LastName')
                initials = author.find('Initials')
                if lastname is not None and initials is not None:
                    authors.append(f"{lastname.text} {initials.text}")
            
            return {
                'pmid': pmid,
                'title': title,
                'abstract': abstract,
                'journal': journal,
                'pub_date': f"{year}-01-01",
                'authors': authors
            }
            
        except:
            return None
    
    def _search_database(self, keywords, limit=5):
        """Search local database as fallback"""
        print(" Searching local database...")
        
        try:
            if not keywords:
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
            
            print(f"✓ Found {len(papers)} papers in database\n")
            return papers
            
        except Exception as e:
            print(f"✗ Database search error: {e}")
            return []
    
    def search_papers(self, query_text, limit=5):
        """Hybrid search: Try PubMed first, fallback to database"""
        print(f"Searching for: '{query_text}'")
        
        keywords = self._extract_keywords(query_text)
        print(f"Keywords: {keywords}\n")
        
        if not keywords:
            return [], "database"
        
        papers = self._search_pubmed_live(keywords, max_results=limit)
        
        if papers is None:
            print(" PubMed API unavailable - using cached database papers\n")
            papers = self._search_database(keywords, limit=limit)
            return papers, "database_fallback"
        elif len(papers) > 0:
            print("✓ Using fresh PubMed papers\n")
            return papers, "pubmed_live"
        else:
            print(" No papers on PubMed - checking database\n")
            papers = self._search_database(keywords, limit=limit)
            return papers, "database_fallback"
    
    def _enforce_rate_limit(self):
        """Enforce rate limiting for Claude API calls"""
        current_time = time.time()
        time_since_last_call = current_time - self.last_api_call
        
        if time_since_last_call < self.min_api_interval:
            wait_time = self.min_api_interval - time_since_last_call
            print(f" Rate limiting: waiting {wait_time:.2f}s...")
            time.sleep(wait_time)
        
        self.last_api_call = time.time()
    
    def generate_response(self, user_question, papers, source, detail_level='standard'):
        """Generate response with adjustable detail level"""
        print(f"Generating {detail_level} response with Claude API...")
        
        token_limits = {
            'brief': 200,
            'standard': 500,
            'detailed': 1500
        }
        
        detail_instructions = {
            'brief': "Keep response very concise (100-150 words). Focus only on key points.",
            'standard': "Keep response concise (200-300 words). Balance brevity with completeness.",
            'detailed': "Provide a comprehensive, detailed explanation (500-800 words). Cover mechanisms, research methods, practical applications, and nuanced interpretations of the evidence."
        }
        
        context = self._build_context(papers)
        
        source_note = ""
        if source == "database_fallback":
            source_note = "\n\n NOTE: PubMed API is currently unavailable. Response is based on cached research papers from our database."
        elif source == "pubmed_live":
            source_note = "\n\n✓ NOTE: Response is based on the latest research papers retrieved from PubMed."
        
        prompt = f"""You are a scientific fitness advisor. Answer the user's question based ONLY on the research papers provided below. Always cite sources using [Author et al., Year, PMID: xxxxx] format.

USER QUESTION: {user_question}

RELEVANT RESEARCH PAPERS:
{context}

INSTRUCTIONS:
1. Provide an evidence-based answer
2. Cite specific papers for each claim
3. Mention any conflicting evidence if present
4. {detail_instructions[detail_level]}
5. If papers don't fully address the question, acknowledge limitations

ANSWER:"""
        
        try:
            self._enforce_rate_limit()
            
            message = self.claude.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=token_limits[detail_level],
                messages=[{"role": "user", "content": prompt}],
                timeout=30.0
            )
            
            response_text = message.content[0].text
            tokens_used = message.usage.input_tokens + message.usage.output_tokens
            
            print(f"✓ Response generated ({tokens_used} tokens)\n")
            
            full_response = response_text + source_note
            
            return full_response, tokens_used
            
        except Exception as e:
            print(f"✗ Error: {e}")
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
Journal: {paper.get('journal', 'Unknown')}
Year: {year}
PMID: {paper['pmid']}
Abstract: {paper['abstract'][:500]}...
""")
        
        return "\n".join(context_parts)
    
    def process_query(self, user_question, detail_level='standard'):
        """Complete hybrid pipeline with detail level control"""
        print("="*60)
        print(f"PROCESSING QUERY ({detail_level.upper()} MODE)")
        print("="*60)
        print(f"Question: {user_question}\n")
        
        try:
            papers, source = self.search_papers(user_question, limit=5)
            
            if not papers:
                return "I couldn't find relevant research papers for your question. Please try rephrasing or ask about a different fitness topic."
            
            if source == "database_fallback":
                print(" MESSAGE: PubMed API is currently down. Using cached papers from database.\n")
            
            response, tokens = self.generate_response(user_question, papers, source, detail_level)
            
            sys.path.append('src/llm')
            from citation_formatter import format_for_response
            references = format_for_response(papers)
            
            full_response = f"{response}\n\n{'='*60}\nREFERENCES:\n{references}"
            
            self.db.log_query(user_question, cache_hit=(source=="database_fallback"), response_time_ms=0)
            
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
        
        # Test different detail levels
        print("\n TESTING STANDARD RESPONSE:")
        response = processor.process_query(question, detail_level='standard')
        print(response)
        
        print("\n\n TESTING DETAILED RESPONSE:")
        response_detailed = processor.process_query(question, detail_level='detailed')
        print(response_detailed)
        
        processor.close()
        
    except Exception as e:
        print(f"\n✗ Fatal error: {e}")