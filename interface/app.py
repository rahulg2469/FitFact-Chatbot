"""
FitFact - Research-Backed Fitness Q&A Chatbot
Production-grade Streamlit interface with PubMed Query Optimizer
Author: Satya (completing Rahul's Week 3 tasks)
Enhanced by: Rahul (conversation memory, UI improvements)
"""

import streamlit as st
import time
from datetime import datetime
import sys
import os
import base64

# Add paths for imports
sys.path.append('..')  # Parent directory
sys.path.append('../database_files')
sys.path.append('../claude_files')
sys.path.append('../src/etl')
from database_files.database import FitFactDB
from database_files.cache_manager import CacheManager
from claude_api import ClaudeProcessor
from keyword_extractor import FitnessKeywordExtractor
from pubmed_query_optimizer import PubMedQueryOptimizer
from src.etl.pubmed_fetcher import search_pubmed, fetch_paper_details
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()


# Get absolute path to logo
script_dir = os.path.dirname(os.path.abspath(__file__))  # Get full path to interface folder
parent_dir = os.path.dirname(script_dir)  # Go up to FitFact-Chatbot
logo_path = os.path.join(parent_dir, "assets", "fitfact_logo.jpg")

print(f"🔍 Script directory: {script_dir}")
print(f"📁 Parent directory: {parent_dir}")
print(f"🖼️ Logo path: {logo_path}")
print(f"✅ Logo exists: {os.path.exists(logo_path)}")


st.set_page_config(
    page_title="FitFact - Evidence-Based Fitness Advisor",
    page_icon=logo_path if os.path.exists(logo_path) else "💪",
    layout="wide",
    initial_sidebar_state="expanded"
)


# Custom CSS for professional styling with DARK THEME
st.markdown("""
<style>
    /* Dark theme background */
    .stApp {
        background-color: #121212;
    }
    
    .main {
        padding: 0rem 1rem;
        background-color: #121212;
    }
    
    /* Adjust sidebar for dark theme */
    [data-testid="stSidebar"] {
        background-color: #1a1a1a;
    }
    
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
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
    
    .citation {
        color: #1976D2;
        text-decoration: none;
        font-weight: 500;
    }
    
    .citation:hover {
        text-decoration: underline;
    }
    
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
    }
    
    .stSpinner > div {
        border-color: #667eea !important;
    }
    
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
    
    /* Quick question card styling - COMPACT */
    div[data-testid="column"] button {
        background: linear-gradient(135deg, rgba(20, 30, 50, 0.8) 0%, rgba(30, 40, 60, 0.6) 100%) !important;
        border: 2px solid rgba(0, 150, 255, 0.3) !important;
        border-radius: 15px !important;
        padding: 1rem 0.5rem !important;
        height: 110px !important;
        color: white !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 15px rgba(0, 100, 255, 0.2) !important;
    }
    
    div[data-testid="column"] button:hover {
        border-color: rgba(0, 200, 255, 0.8) !important;
        box-shadow: 0 6px 25px rgba(0, 150, 255, 0.4) !important;
        transform: translateY(-5px) !important;
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
        self.query_optimizer = PubMedQueryOptimizer()
    
    def process_query(self, user_query: str, conversation_history: list = None) -> dict:
        """Process user query through the pipeline with conversation context"""
        start_time = time.time()
        metrics = {}
        
        # Only use cache for longer, standalone questions (8+ words)
        if self.db and self.cache and len(user_query.split()) >= 8:
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
        
        # Optimize the query for PubMed search
        print("\n🔬 OPTIMIZING QUERY FOR PUBMED...")
        optimized = self.query_optimizer.optimize_query(user_query)
        research_focuses = self.query_optimizer.extract_research_focus(user_query)
        
        print(f"📝 Original query: {user_query}")
        print(f"🎯 Academic query: {optimized['academic'][:100]}...")
        print(f"🏷️ MeSH enhanced: {optimized['mesh_enhanced'][:100]}...")
        print(f"🔬 Research focuses: {', '.join(research_focuses)}")
        
        # Extract keywords as fallback
        keywords = self.keyword_extractor.extract_keywords(user_query)
        metrics['keywords'] = keywords['all_keywords']
        metrics['research_focuses'] = research_focuses
        metrics['cache_hit'] = False
        
        # Search PubMed with optimized queries
        print("\n📚 SEARCHING PUBMED WITH OPTIMIZED QUERIES...")
        papers = []
        seen_pmids = set()
        
        search_strategies = optimized['search_strategies']
        
        try:
            academic_terms = self.claude.extract_academic_search_terms(user_query)
            if academic_terms:
                search_strategies = academic_terms + search_strategies
        except:
            pass
        
        for idx, search_query in enumerate(search_strategies[:5], 1):
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
        
        if len(papers) < 10:
            print(f"\n🔍 Searching for systematic reviews...")
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
            except:
                pass
        
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
                'response': "I couldn't find relevant research papers for your question. Please try again or rephrase your question.",
                'metrics': metrics,
                'cached': False,
                'error': True
            }
        
        # Generate response with Claude
        print(f"\n🤖 GENERATING RESPONSE with {len(papers)} papers...")
        try:
            claude_response = self.claude.generate_response(papers[:10], user_query, conversation_history)
            
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
        
        # Store papers and response in cache
        if self.db and self.cache:
            try:
                paper_ids = self._store_papers(papers)
                if paper_ids:
                    self.cache.store_in_cache(user_query, claude_response['text'], paper_ids)
                    print(f"✅ Response cached with {len(paper_ids)} papers!")
            except Exception as e:
                print(f"⚠️ Cache storage failed: {e}")
        
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

# Header with logo - NO BLUE LINES VERSION
if os.path.exists(logo_path):
    with open(logo_path, "rb") as f:
        img_data = base64.b64encode(f.read()).decode()
    
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 25%, #16213e 50%, #1a1a2e 75%, #0a0a0a 100%); padding: 1.5rem 2rem; border-radius: 10px; margin-bottom: 1.5rem; text-align: center; box-shadow: 0 8px 32px rgba(0, 100, 255, 0.3), 0 0 60px rgba(0, 150, 255, 0.2) inset; border: 1px solid rgba(0, 150, 255, 0.2); position: relative; overflow: hidden;">
        <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 70%; height: 70%; background: radial-gradient(ellipse at center, rgba(0, 150, 255, 0.15) 0%, transparent 70%); filter: blur(50px); pointer-events: none;"></div>
        <div style="display: flex; justify-content: center; align-items: center; margin-bottom: 0.5rem; position: relative; z-index: 1;">
            <img src="data:image/jpeg;base64,{img_data}" width="100" style="border-radius: 10px;">
        </div>
        <h1 style="margin: 0.3rem 0 0 0; font-size: 2rem; text-align: center; color: #ffffff; text-shadow: 0 0 20px rgba(0, 150, 255, 0.8), 2px 2px 4px rgba(0,0,0,0.8); font-weight: bold; position: relative; z-index: 1;">FitFact</h1>
        <p style="margin: 0.3rem 0 0 0; font-size: 0.95rem; text-align: center; color: #e0e8ff; text-shadow: 0 0 10px rgba(0, 150, 255, 0.5), 1px 1px 2px rgba(0,0,0,0.6); position: relative; z-index: 1;">Evidence-Based Fitness Advice from Peer-Reviewed Research</p>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <div style="background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 25%, #16213e 50%, #1a1a2e 75%, #0a0a0a 100%); padding: 1.5rem 2rem; border-radius: 10px; margin-bottom: 1.5rem; text-align: center; box-shadow: 0 8px 32px rgba(0, 100, 255, 0.3), 0 0 60px rgba(0, 150, 255, 0.2) inset; border: 1px solid rgba(0, 150, 255, 0.2);">
        <div style="font-size: 2rem; margin-bottom: 0.5rem;">💪</div>
        <h1 style="margin: 0.3rem 0 0 0; font-size: 2rem; color: #ffffff; text-shadow: 0 0 20px rgba(0, 150, 255, 0.8), 2px 2px 4px rgba(0,0,0,0.8); font-weight: bold;">FitFact</h1>
        <p style="margin: 0.3rem 0 0 0; font-size: 0.95rem; color: #e0e8ff; text-shadow: 0 0 10px rgba(0, 150, 255, 0.5), 1px 1px 2px rgba(0,0,0,0.6);">Evidence-Based Fitness Advice from Peer-Reviewed Research</p>
    </div>
    """, unsafe_allow_html=True)

# Quick Questions as horizontal cards in center (COMPACT VERSION)
if len(st.session_state.messages) == 0:
    st.markdown("""
    <div style="margin: 1rem 0 0.5rem 0;">
        <h3 style="text-align: center; color: #ffffff; font-size: 1.2rem; margin-bottom: 1rem; text-shadow: 0 0 15px rgba(0, 180, 255, 0.6); font-weight: bold;">
            🎯 Quick Start Questions
        </h3>
    </div>
    """, unsafe_allow_html=True)

    cols = st.columns(5)

    quick_questions_data = [
        ("💪", "Workout\nFrequency", "How many times a week should I work out?"),
        ("🥩", "Protein\nIntake", "What's the ideal protein intake for muscle gain?"),
        ("🔥", "HIIT vs\nCardio", "Is HIIT better than steady cardio for fat loss?"),
        ("🧘", "Recovery\nMethods", "Best recovery methods after training?"),
        ("💎", "Muscle\n& Cutting", "Can I build muscle while cutting?")
    ]

    for idx, (col, (emoji, title, question)) in enumerate(zip(cols, quick_questions_data)):
        with col:
            if st.button(
                f"{emoji}\n\n{title}",
                key=f"quick_center_{idx}",
                use_container_width=True
            ):
                st.session_state.pending_question = question
                st.rerun()

    st.markdown("<div style='margin-bottom: 0.5rem;'></div>", unsafe_allow_html=True)

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
    
    st.markdown("### ℹ️ About FitFact")
    st.info(
        "FitFact provides fitness advice based exclusively on "
        "peer-reviewed research from PubMed. Every response includes "
        "proper citations to scientific studies.\n\n"
        "🔬 Now with enhanced query optimization for better research matching!"
    )
    
    st.markdown("---")
    
    if st.session_state.db_connected:
        st.success("✅ Database Connected")
    else:
        st.error("❌ Database Disconnected")
    
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# Define casual responses
CASUAL_RESPONSES = {
    'thank you': "You're welcome! Let me know if you have any other fitness questions! 💪",
    'thanks': "Happy to help! Feel free to ask anything else about fitness or nutrition.",
    'thank': "You're welcome! What else can I help you with?",
    'ok': "Great! Anything else you'd like to know?",
    'okay': "Sounds good! Let me know if you need anything else.",
    'got it': "Perfect! I'm here if you have more questions.",
    'bye': "Goodbye! Stay healthy and keep training! 💪",
    'goodbye': "Take care! Come back anytime with fitness questions!",
    'hello': "Hello! I'm FitFact, your evidence-based fitness advisor. What fitness question can I help you with today?",
    'hi': "Hi there! What fitness or nutrition question do you have?",
    'hey': "Hey! How can I help you with your fitness goals today?",
}

def is_casual_message(prompt: str) -> tuple:
    """Check if message is casual, return (is_casual, response_text)"""
    prompt_lower = prompt.lower().strip()
    
    if prompt_lower in CASUAL_RESPONSES:
        return True, CASUAL_RESPONSES[prompt_lower]
    
    if len(prompt.split()) <= 3:
        for phrase, response in CASUAL_RESPONSES.items():
            if phrase in prompt_lower:
                return True, response
    
    return False, None

# Process pending question from quick buttons
if 'pending_question' in st.session_state and st.session_state.pending_question:
    prompt = st.session_state.pending_question
    st.session_state.pending_question = None
    
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.session_state.total_queries += 1
    
    is_casual, casual_text = is_casual_message(prompt)
    
    if is_casual:
        st.session_state.messages.append({
            "role": "assistant",
            "content": casual_text
        })
    else:
        if st.session_state.pipeline is None:
            st.session_state.pipeline = init_pipeline()
        
        if st.session_state.pipeline is None:
            st.session_state.messages.append({
                "role": "assistant",
                "content": "Failed to initialize the system. Please check your database connection."
            })
        else:
            result = st.session_state.pipeline.process_query(prompt, st.session_state.messages[:-1])
            
            st.session_state.messages.append({
                "role": "assistant",
                "content": result['response'],
                "metrics": result.get('metrics', {})
            })
    
    st.rerun()

# Display all existing messages FIRST
chat_container = st.container()

with chat_container:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
            if "metrics" in message:
                with st.expander("📈 Query Metrics", expanded=False):
                    metrics = message["metrics"]
                    
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
                    
                    if metrics.get('research_focuses'):
                        st.write(f"**Research Focus:** {', '.join(metrics['research_focuses'])}")
                    if metrics.get('keywords'):
                        st.write(f"**Keywords:** {', '.join(metrics['keywords'][:5])}")

# Handle new chat input
if prompt := st.chat_input("Ask me anything about fitness, nutrition, or training..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.session_state.total_queries += 1
    
    # Show just the new user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Process WITHOUT showing previous messages dimmed
    is_casual, casual_text = is_casual_message(prompt)
    
    if is_casual:
        st.session_state.messages.append({
            "role": "assistant",
            "content": casual_text
        })
        st.rerun()
    else:
        if st.session_state.pipeline is None:
            with st.spinner("Initializing FitFact system..."):
                st.session_state.pipeline = init_pipeline()
        
        if st.session_state.pipeline is None:
            st.session_state.messages.append({
                "role": "assistant",
                "content": "Failed to initialize the system. Please check your database connection."
            })
            st.rerun()
        else:
            # Create empty placeholder for response
            response_placeholder = st.empty()
            
            # Show spinner in the placeholder
            with response_placeholder:
                with st.spinner("🔬 Analyzing your question and searching research papers..."):
                    result = st.session_state.pipeline.process_query(prompt, st.session_state.messages[:-1])
            
            # Store and rerun to display cleanly
            st.session_state.messages.append({
                "role": "assistant",
                "content": result['response'],
                "metrics": result.get('metrics', {})
            })
            st.rerun()

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #888; font-size: 0.9rem;'>
        FitFact v1.0 | 
        <a href='https://github.com/rahulg2469/FitFact-Chatbot' target='_blank' style='color: #0096FF;'>GitHub</a>
    </div>
    """,
    unsafe_allow_html=True
)