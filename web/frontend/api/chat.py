"""
FitFact Chat API - Vercel Serverless Function
Handles chat requests using Claude API and PubMed
"""

from http.server import BaseHTTPRequestHandler
import json
import os
import time
import re
from urllib.request import urlopen, Request
from urllib.parse import urlencode
from xml.etree import ElementTree as ET

# Initialize Anthropic client
from anthropic import Anthropic

client = Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))

# ==================== PUBMED FUNCTIONS ====================

def search_pubmed(query, max_results=5):
    """Search PubMed for relevant articles"""
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {
        'db': 'pubmed',
        'term': query,
        'retmax': max_results,
        'retmode': 'json',
        'sort': 'relevance'
    }
    
    try:
        url = f"{base_url}?{urlencode(params)}"
        req = Request(url, headers={'User-Agent': 'FitFact/1.0'})
        with urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            return data.get('esearchresult', {}).get('idlist', [])
    except Exception as e:
        print(f"PubMed search error: {e}")
        return []

def fetch_paper_details(pmid):
    """Fetch paper details from PubMed"""
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    params = {
        'db': 'pubmed',
        'id': pmid,
        'retmode': 'xml'
    }
    
    try:
        url = f"{base_url}?{urlencode(params)}"
        req = Request(url, headers={'User-Agent': 'FitFact/1.0'})
        with urlopen(req, timeout=10) as response:
            root = ET.fromstring(response.read().decode())
            article = root.find('.//PubmedArticle')
            if not article:
                return None
            
            # Extract title
            title_elem = article.find('.//ArticleTitle')
            title = title_elem.text if title_elem is not None else 'No title'
            
            # Extract abstract
            abstract_elem = article.find('.//AbstractText')
            abstract = abstract_elem.text if abstract_elem is not None else ''
            
            # Extract authors
            authors = []
            for author in article.findall('.//Author'):
                lastname = author.find('LastName')
                forename = author.find('ForeName')
                if lastname is not None:
                    name = lastname.text
                    if forename is not None:
                        name = f"{lastname.text} {forename.text[0]}"
                    authors.append(name)
            
            # Extract journal
            journal_elem = article.find('.//Journal/Title')
            journal = journal_elem.text if journal_elem is not None else 'Unknown'
            
            # Extract publication date
            pub_date = article.find('.//PubDate')
            year = pub_date.find('Year').text if pub_date is not None and pub_date.find('Year') is not None else ''
            
            return {
                'pmid': pmid,
                'title': title,
                'abstract': abstract,
                'authors': authors,
                'journal': journal,
                'publication_date': year
            }
    except Exception as e:
        print(f"PubMed fetch error: {e}")
        return None

# ==================== QUERY OPTIMIZATION ====================

def optimize_query(user_query):
    """Convert user question to PubMed search queries"""
    query_lower = user_query.lower()
    
    # Topic mappings
    topic_terms = {
        'protein': ['protein intake', 'protein supplementation', 'muscle protein synthesis'],
        'creatine': ['creatine monohydrate', 'creatine supplementation', 'creatine performance'],
        'sleep': ['sleep recovery', 'sleep muscle', 'sleep performance'],
        'hiit': ['high intensity interval training', 'HIIT exercise', 'interval training'],
        'cardio': ['cardiovascular exercise', 'aerobic training', 'endurance exercise'],
        'strength': ['resistance training', 'strength training', 'weight training'],
        'recovery': ['muscle recovery', 'exercise recovery', 'post-exercise recovery'],
        'weight loss': ['fat loss exercise', 'weight reduction', 'body composition'],
        'muscle': ['muscle hypertrophy', 'muscle growth', 'skeletal muscle']
    }
    
    strategies = []
    
    # Find matching topics
    for topic, terms in topic_terms.items():
        if topic in query_lower:
            strategies.extend(terms[:2])
    
    # If no specific topic, create general search
    if not strategies:
        # Remove common words and create search
        stop_words = {'how', 'what', 'when', 'should', 'can', 'does', 'is', 'the', 'a', 'an', 'i', 'my', 'me', 'for'}
        words = [w for w in query_lower.split() if w not in stop_words and len(w) > 2]
        if words:
            strategies.append(' '.join(words[:4]) + ' exercise')
            strategies.append(' '.join(words[:3]) + ' fitness')
    
    return strategies[:3]

# ==================== CLAUDE RESPONSE ====================

def generate_response(papers, user_query, conversation_history=None):
    """Generate response using Claude"""
    
    # Format papers for context
    papers_text = ""
    for i, paper in enumerate(papers[:6], 1):
        authors = paper.get('authors', [])
        author_str = f"{authors[0]} et al." if authors else "Unknown"
        papers_text += f"\n[{i}] {paper['title']}\n"
        papers_text += f"    Authors: {author_str} ({paper.get('publication_date', 'N/A')})\n"
        papers_text += f"    Journal: {paper.get('journal', 'Unknown')}\n"
        papers_text += f"    PMID: {paper['pmid']}\n"
        if paper.get('abstract'):
            papers_text += f"    Abstract: {paper['abstract'][:500]}...\n"
    
    # Build conversation context
    context = ""
    if conversation_history:
        for msg in conversation_history[-4:]:
            role = "User" if msg['role'] == 'user' else "Assistant"
            context += f"{role}: {msg['content']}\n\n"
    
    prompt = f"""You are FitFact, an evidence-based fitness advisor. Answer questions using the research papers provided.

RESEARCH PAPERS:
{papers_text}

{"CONVERSATION HISTORY:" + chr(10) + context if context else ""}

USER QUESTION: {user_query}

Respond in this JSON format:
{{
  "headline": "Direct 1-2 sentence answer to the question",
  "points": [
    {{"title": "Key Point Title", "content": "Detailed explanation with citation (Author et al., Year)"}},
    {{"title": "Another Point", "content": "More details with citation"}}
  ],
  "takeaway": "Brief actionable summary",
  "references": [
    {{"num": 1, "author": "LastName", "year": "2024", "title": "Paper title", "journal": "Journal", "pmid": "12345678"}}
  ]
}}

Use 2-4 points. Always cite sources as (Author et al., Year). Be practical and helpful."""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}]
        )
        
        response_text = response.content[0].text
        
        # Try to parse JSON
        try:
            # Find JSON in response
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                structured = json.loads(json_match.group())
                
                # Add PMIDs to references from papers
                if structured.get('references'):
                    for ref in structured['references']:
                        for paper in papers:
                            year = paper.get('publication_date', '')
                            if year == ref.get('year'):
                                ref['pmid'] = paper.get('pmid', ref.get('pmid', ''))
                                ref['title'] = paper.get('title', ref.get('title', ''))
                                ref['journal'] = paper.get('journal', ref.get('journal', ''))
                                break
                
                return {
                    'text': response_text,
                    'structured': structured
                }
        except json.JSONDecodeError:
            pass
        
        return {'text': response_text, 'structured': None}
        
    except Exception as e:
        print(f"Claude error: {e}")
        return {'text': f"Error generating response: {str(e)}", 'structured': None}


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        start_time = time.time()
        
        # Parse request body
        content_length = int(self.headers['Content-Length'])
        body = json.loads(self.rfile.read(content_length).decode())
        
        user_query = body.get('message', '')
        conversation_history = body.get('conversation_history', [])
        
        if not user_query:
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Message required'}).encode())
            return
        
        # Search PubMed
        search_queries = optimize_query(user_query)
        papers = []
        seen_pmids = set()
        
        for search_query in search_queries:
            if len(papers) >= 10:
                break
            try:
                pmids = search_pubmed(search_query, max_results=5)
                for pmid in pmids:
                    if pmid not in seen_pmids and len(papers) < 10:
                        paper = fetch_paper_details(pmid)
                        if paper and paper.get('abstract'):
                            seen_pmids.add(pmid)
                            papers.append(paper)
            except Exception as e:
                print(f"Search error: {e}")
                continue
        
        if not papers:
            response_data = {
                'response': "I couldn't find relevant research papers. Please try rephrasing your question.",
                'structured': None,
                'papers_used': 0,
                'response_time': time.time() - start_time,
                'cached': False
            }
        else:
            # Generate response
            claude_response = generate_response(papers, user_query, conversation_history)
            
            response_data = {
                'response': claude_response['text'],
                'structured': claude_response.get('structured'),
                'papers_used': len(papers),
                'response_time': time.time() - start_time,
                'cached': False
            }
        
        # Send response
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(response_data).encode())
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
