"""
FitFact - Research-Backed Fitness Q&A Chatbot
Production-grade Streamlit interface with PubMed Query Optimizer
Author: Satya (completing Rahul's Week 3 tasks)
"""

import streamlit as st
import time
from datetime import datetime
import sys
import os

# Add paths for imports
sys.path.append('database_files')

from database import FitFactDB
from cache_manager import CacheManager
from claude_files.claude_api import ClaudeProcessor
from keyword_extractor import FitnessKeywordExtractor
from pubmed_query_optimizer import PubMedQueryOptimizer  # NEW IMPORT
from src.etl.pubmed_fetcher import search_pubmed, fetch_paper_details
from dotenv import load_dotenv

load_dotenv()

# Page configuration
st.set_page_config(
    page_title="FitFact - Evidence-Based Fitness Advisor",
    page_icon="💪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional styling (keeping your existing CSS)
st.markdown("""
<style>
    /* Main container styling */
    .main {
        padding: 0rem 1rem;
    }
    
    /* Custom header styling */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    /* Chat message styling */
    .user-message {
        background-color: #E8F4FD;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        border-left: 4px solid #2196F3;
    }
    
    .assistant-message {
        background-color: #F3E5F5;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        border-left: 4px solid #9C27B0;
    }
    
    /* Citation styling */
    .citation {
        color: #1976D2;
        text-decoration: none;
        font-weight: 500;
    }
    
    .citation:hover {
        text-decoration: underline;
    }
    
    /* Metric cards */
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
    }
    
    /* Loading animation */
    .stSpinner > div {
        border-color: #667eea !important;
    }
    
    /* Success/Error messages */
    .success-message {
        background-color: #E8F5E9;
        color: #2E7D32;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #4CAF50;
    }
    
    .error-message {
        background-color: #FFEBEE;
        color: #C62828;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #F44336;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'total_queries' not in st.session_state:
    st.session_state.total_queries = 0
if 'cache_hits' not in st.session_state:
    st.session_state.cache_hits = 0
if 'db_connected' not in st.session_state:
    st.session_state.db_connected = False
if 'pipeline' not in st.session_state:
    st.session_state.pipeline = None

# Initialize the pipeline
@st.cache_resource
def init_pipeline():
    """Initialize the FitFact pipeline with caching"""
    try:
        # Test database connection first
        test_db = FitFactDB()
        test_db.close()
        print("✅ Database test successful")
        
        return FitFactPipeline()
    except Exception as e:
        print(f"❌ Failed to initialize pipeline: {str(e)}")
        st.error(f"Database connection failed: {str(e)}")
        return None

class FitFactPipeline:
    """Main pipeline for FitFact chatbot"""
    
    def __init__(self):
        try:
            self.db = FitFactDB()
            self.cache = CacheManager(self.db)
            st.session_state.db_connected = True
            print("✅ Database connected in pipeline")
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            st.session_state.db_connected = False
            self.db = None
            self.cache = None
        
        self.claude = ClaudeProcessor()
        self.keyword_extractor = FitnessKeywordExtractor()
        self.query_optimizer = PubMedQueryOptimizer()  # NEW: Initialize query optimizer
    
    def process_query(self, user_query: str) -> dict:
        """Process user query through the pipeline with optimized PubMed searches"""
        start_time = time.time()
        metrics = {}
        
        # Step 1: Check cache first
        if self.db and self.cache:
            cached = self.cache.smart_cache_lookup(user_query, threshold=0.7)
            
            if cached:
                st.session_state.cache_hits += 1
                metrics['cache_hit'] = True
                metrics['similarity'] = cached.get('similarity', 1.0)
                metrics['response_time'] = time.time() - start_time
                
                return {
                    'response': cached['response_text'],
                    'metrics': metrics,
                    'cached': True
                }
        
        # Step 2: Optimize the query for PubMed search
        print("\n🔬 OPTIMIZING QUERY FOR PUBMED...")
        optimized = self.query_optimizer.optimize_query(user_query)
        research_focuses = self.query_optimizer.extract_research_focus(user_query)
        
        print(f"📝 Original query: {user_query}")
        print(f"🎯 Academic query: {optimized['academic'][:100]}...")
        print(f"🏷️ MeSH enhanced: {optimized['mesh_enhanced'][:100]}...")
        print(f"🔬 Research focuses: {', '.join(research_focuses)}")
        
        # Step 3: Extract keywords as fallback
        keywords = self.keyword_extractor.extract_keywords(user_query)
        metrics['keywords'] = keywords['all_keywords']
        metrics['research_focuses'] = research_focuses
        metrics['cache_hit'] = False
        
        # Step 4: Search PubMed with optimized queries - GET UP TO 20 PAPERS
        print("\n📚 SEARCHING PUBMED WITH OPTIMIZED QUERIES...")
        papers = []
        seen_pmids = set()
        
        # Try different search strategies from the optimizer
        search_strategies = optimized['search_strategies']
        
        # Add Claude's academic terms if available
        try:
            academic_terms = self.claude.extract_academic_search_terms(user_query)
            if academic_terms:
                search_strategies = academic_terms + search_strategies
        except:
            pass
        
        # Execute searches with different strategies
        for idx, search_query in enumerate(search_strategies[:5], 1):  # Try up to 5 strategies
            if len(papers) >= 20:
                break
            
            try:
                print(f"\n  Strategy {idx}: {search_query[:100]}...")
                pmids = search_pubmed(search_query, max_results=10)
                
                if pmids:
                    print(f"    ✅ Found {len(pmids)} PMIDs")
                    for pmid in pmids:
                        if pmid not in seen_pmids and len(papers) < 20:
                            paper = fetch_paper_details(pmid)
                            if paper:
                                seen_pmids.add(pmid)
                                papers.append(paper)
                                print(f"      📄 Paper {len(papers)}/20: {paper['title'][:50]}...")
                else:
                    print(f"    ⚠️ No results for this strategy")
                    
            except Exception as e:
                print(f"    ❌ Search failed: {e}")
                continue
        
        # Step 5: If still need more papers, try review-focused search
        if len(papers) < 10:
            print(f"\n🔍 Searching for systematic reviews and meta-analyses...")
            try:
                review_query = optimized['review_focused']
                pmids = search_pubmed(review_query, max_results=5)
                
                if pmids:
                    for pmid in pmids:
                        if pmid not in seen_pmids and len(papers) < 20:
                            paper = fetch_paper_details(pmid)
                            if paper:
                                seen_pmids.add(pmid)
                                papers.append(paper)
                                print(f"      📚 Review paper: {paper['title'][:50]}...")
            except:
                pass
        
        # Step 6: Final fallback to basic keyword search if needed
        if len(papers) < 5:
            print(f"\n⚠️ Only {len(papers)} papers found, trying basic keyword search...")
            basic_query = ' '.join(keywords['all_keywords'][:5])
            try:
                pmids = search_pubmed(basic_query, max_results=10)
                if pmids:
                    for pmid in pmids:
                        if pmid not in seen_pmids and len(papers) < 20:
                            paper = fetch_paper_details(pmid)
                            if paper:
                                seen_pmids.add(pmid)
                                papers.append(paper)
            except:
                pass
        
        print(f"\n📊 Total papers collected: {len(papers)}")
        
        if not papers:
            return {
                'response': "I couldn't find relevant research papers for your question. This might be a connection issue with PubMed. Please try again or rephrase your question.",
                'metrics': metrics,
                'cached': False,
                'error': True
            }
        
        # Step 7: Generate response with Claude
        print(f"\n🤖 GENERATING RESPONSE with {len(papers)} papers...")
        try:
            # Use up to 10 most relevant papers for Claude's response
            claude_response = self.claude.generate_response(papers[:10], user_query)
            
            if not claude_response['success']:
                return {
                    'response': "I encountered an error generating a response. Please try again.",
                    'metrics': metrics,
                    'cached': False,
                    'error': True
                }
        except Exception as e:
            print(f"❌ Claude response failed: {e}")
            return {
                'response': f"Error generating response: {str(e)}",
                'metrics': metrics,
                'cached': False,
                'error': True
            }
        
        # Step 8: Store papers and response in cache
        if self.db and self.cache:
            try:
                paper_ids = self._store_papers(papers)
                if paper_ids:
                    self.cache.store_in_cache(user_query, claude_response['text'], paper_ids)
                    print(f"✅ Response cached with {len(paper_ids)} papers!")
            except Exception as e:
                print(f"⚠️ Cache storage failed: {e}")
        
        # Prepare metrics
        metrics['response_time'] = time.time() - start_time
        metrics['papers_found'] = len(papers)
        metrics['citations'] = claude_response.get('citations_found', 0)
        metrics['search_strategies_used'] = len([s for s in search_strategies[:5] if s])
        metrics['optimization_applied'] = True
        
        return {
            'response': claude_response['text'],
            'metrics': metrics,
            'cached': False
        }
    
    def _store_papers(self, papers: list) -> list:
        """Store papers and return their IDs"""
        if not self.db:
            return []
        
        paper_ids = []
        for paper in papers:
            try:
                paper_id = self.db.save_paper(
                    pmid=paper['pmid'],
                    title=paper['title'],
                    abstract=paper['abstract'],
                    authors=str(paper.get('authors', [])),
                    pub_date=paper.get('publication_date', '2024-01-01'),
                    journal=paper.get('journal', 'Unknown'),
                    study_type='research'
                )
                paper_ids.append(paper_id)
            except Exception as e:
                print(f"Error storing paper: {e}")
        
        return paper_ids

# Header
st.markdown("""
<div class="main-header">
    <h1 style="margin: 0; font-size: 2.5rem;">💪 FitFact</h1>
    <p style="margin: 0.5rem 0 0 0; font-size: 1.1rem; opacity: 0.9;">
        Evidence-Based Fitness Advice from Peer-Reviewed Research
    </p>
</div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("### 📊 Session Statistics")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Queries", st.session_state.total_queries)
    with col2:
        hit_rate = (st.session_state.cache_hits / max(st.session_state.total_queries, 1)) * 100
        st.metric("Cache Hit Rate", f"{hit_rate:.1f}%")
    
    st.markdown("---")
    
    st.markdown("### 🎯 Quick Questions")
    quick_questions = [
        "How many times a week should I work out?",
        "What's the ideal protein intake for muscle gain?",
        "Is HIIT better than steady cardio for fat loss?",
        "Best recovery methods after training?",
        "Can I build muscle while cutting?"
    ]
    
    for question in quick_questions:
        if st.button(question, key=f"quick_{question}"):
            st.session_state.messages.append({"role": "user", "content": question})
            st.rerun()
    
    st.markdown("---")
    
    st.markdown("### ℹ️ About FitFact")
    st.info(
        "FitFact provides fitness advice based exclusively on "
        "peer-reviewed research from PubMed. Every response includes "
        "proper citations to scientific studies.\n\n"
        "🔬 Now with enhanced query optimization for better research matching!"
    )
    
    st.markdown("---")
    
    # Database connection status
    if st.session_state.db_connected:
        st.success("✅ Database Connected")
    else:
        st.error("❌ Database Disconnected")
    
    # Clear chat button
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# Main chat interface
chat_container = st.container()

# Display chat messages
with chat_container:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
            # Display metrics if available
            if "metrics" in message:
                with st.expander("📈 Query Metrics", expanded=False):
                    metrics = message["metrics"]
                    
                    # Row 1: Basic metrics
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Response Time", f"{metrics.get('response_time', 0):.2f}s")
                    with col2:
                        if metrics.get('cache_hit'):
                            st.metric("Source", "✅ Cache")
                        else:
                            st.metric("Papers Used", metrics.get('papers_found', 0))
                    with col3:
                        st.metric("Citations", metrics.get('citations', 0))
                    with col4:
                        if metrics.get('optimization_applied'):
                            st.metric("Optimized", "✅ Yes")
                        else:
                            st.metric("Strategies", metrics.get('search_strategies_used', 1))
                    
                    # Row 2: Additional details
                    if metrics.get('research_focuses'):
                        st.write(f"**Research Focus:** {', '.join(metrics['research_focuses'])}")
                    if metrics.get('keywords'):
                        st.write(f"**Keywords:** {', '.join(metrics['keywords'][:5])}")

# Chat input
if prompt := st.chat_input("Ask me anything about fitness, nutrition, or training..."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.session_state.total_queries += 1
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Generate response
    with st.chat_message("assistant"):
        # Initialize pipeline if needed
        if st.session_state.pipeline is None:
            with st.spinner("Initializing FitFact system..."):
                st.session_state.pipeline = init_pipeline()
        
        if st.session_state.pipeline is None:
            st.error("Failed to initialize the system. Please check your database connection.")
        else:
            # Process the query with detailed status updates
            status_placeholder = st.empty()
            progress_bar = st.progress(0)
            
            with status_placeholder.container():
                st.write("🧠 **Analyzing your question...**")
            progress_bar.progress(20)
            time.sleep(0.3)
            
            with status_placeholder.container():
                st.write("🔬 **Optimizing search terms for academic databases...**")
            progress_bar.progress(40)
            time.sleep(0.3)
            
            # Process the query
            result = st.session_state.pipeline.process_query(prompt)
            
            if result.get('cached'):
                with status_placeholder.container():
                    st.write("✅ **Found in knowledge base!**")
                progress_bar.progress(100)
            else:
                with status_placeholder.container():
                    st.write("📚 **Searching PubMed with optimized queries...**")
                progress_bar.progress(60)
                time.sleep(0.3)
                
                with status_placeholder.container():
                    st.write("🤖 **Generating evidence-based response...**")
                progress_bar.progress(80)
                time.sleep(0.3)
                
                with status_placeholder.container():
                    st.write("✅ **Complete!**")
                progress_bar.progress(100)
            
            time.sleep(0.5)
            status_placeholder.empty()
            progress_bar.empty()
            
            # Display the response
            if result.get('error'):
                st.error(result['response'])
            else:
                st.markdown(result['response'])
                
                # Add response to messages with metrics
                message_data = {
                    "role": "assistant",
                    "content": result['response'],
                    "metrics": result.get('metrics', {})
                }
                st.session_state.messages.append(message_data)

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666; font-size: 0.9rem;'>
        FitFact v1.0 | Built with ❤️ by Team FitFact | 
        <a href='https://github.com/rahulg2469/FitFact-Chatbot' target='_blank'>GitHub</a>
    </div>
    """,
    unsafe_allow_html=True
)