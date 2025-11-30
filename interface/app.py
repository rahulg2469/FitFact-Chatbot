"""
FitFact - Research-Backed Fitness Q&A Chatbot
Production-grade Streamlit interface with PubMed Query Optimizer
"""

import streamlit as st
import time
from datetime import datetime
import sys
import os
import base64
from pathlib import Path

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

load_dotenv()


# Get absolute path to logo
script_dir = os.path.dirname(os.path.abspath(__file__))  # Get full path to interface folder
parent_dir = os.path.dirname(script_dir)  # Go up to FitFact-Chatbot
logo_path = os.path.join(parent_dir, "assets", "fitfact_logo.jpg")
BG_PATH = os.path.join(parent_dir, "assets", "gym_bg.jpg")

def get_base64_image(path: str) -> str:
    return base64.b64encode(Path(path).read_bytes()).decode()

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


bg_base64 = get_base64_image(BG_PATH)

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap');

/* Apply Poppins to specific elements only, not headings */
body, p, div, span, button, input, textarea, select {{
    font-family: 'Poppins', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}}

/* Custom loading animation */
@keyframes rotate {{
    0% {{ transform: rotate(0deg); }}
    100% {{ transform: rotate(360deg); }}
}}

.loading-container {{
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 1rem;
    padding: 1rem;
    margin: 1rem auto 3rem auto;
    max-width: 600px;
    background: rgba(30, 40, 55, 0.6);
    border-radius: 15px;
    border: 1px solid rgba(100, 120, 150, 0.3);
}}

.loading-icon {{
    font-size: 1rem;
    animation: rotate 2s linear infinite;
}}

.loading-text {{
    color: #ffffff;
    font-size: 1.1rem;
    font-weight: 500;
}}

/* Full gym background throughout */
.stApp {{
    background-color: #000;
    background-image: 
        linear-gradient(rgba(0, 0, 0, 0.65), rgba(0, 0, 0, 0.65)),
        url("data:image/jpg;base64,{bg_base64}");
    background-position: center top;
    background-repeat: no-repeat;
    background-attachment: fixed;
    background-size: cover;
}}

.main {{
    padding: 0rem 1rem 3rem 1rem;
    background: transparent;
}}

[data-testid="stSidebar"] {{
    background: rgba(0, 0, 0, 0.85);
    backdrop-filter: blur(6px);
    -webkit-backdrop-filter: blur(6px);
    border-right: 1px solid rgba(100, 120, 150, 0.2);
}}

.stChatInput {{
    background-color: rgba(15, 20, 30, 0.9) !important;
}}

.metric-card {{
    background: rgba(15, 20, 30, 0.9);
    padding: 1rem;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.3);
    text-align: center;
    border: 1px solid rgba(100, 120, 150, 0.2);
}}

[data-testid="stExpander"] {{
    background-color: rgba(40, 50, 70, 0.3);
    border: 1px solid rgba(100, 120, 150, 0.2);
    border-radius: 8px;
}}

[data-testid="stMetricValue"] {{
    color: #ffffff;
}}

[data-testid="stMetricLabel"] {{
    color: #b0c4de;
}}

/* Prevent footer overlap */
.main > div:last-child {{
    position: relative;
    z-index: 10;
    margin-top: 3rem;
}}

/* Completely remove Streamlit's keyboard helper overlay */
div[data-testid="stBottomBlock"],
div[data-testid="stKeyboard"],
span[class*="key_"],
span[class*="cursor"] {{
    display: none !important;
    visibility: hidden !important;
    opacity: 0 !important;
    height: 0 !important;
    width: 0 !important;
    overflow: hidden !important;
    pointer-events: none !important;
}}

/* Hide stray debug text elements */
.main p:empty,
.main div:has(> p:only-child:empty) {{
    display: none !important;
}}

/* Hide specific Streamlit debug/accessibility text */
.main p:only-child,
[class*="cursor"],
[class*="key_"] {{
    color: transparent !important;
    font-size: 0 !important;
    line-height: 0 !important;
    height: 0 !important;
    overflow: hidden !important;
}}

/* Hide any small text near the bottom */
.main > div:last-of-type p:not(:has(a)) {{
    display: none !important;
}}

.stMarkdown p:only-child:not(:has(a)):not(:has(strong)):not(:has(em)) {{
    display: none !important;
}}
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

# Simple Title with Logo - White FITFACT title
if os.path.exists(logo_path):
    with open(logo_path, "rb") as f:
        img_data = base64.b64encode(f.read()).decode()
    
    st.markdown(f"""
    <link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Orbitron:wght@900&family=Righteous&family=Russo+One&display=swap" rel="stylesheet">
    <div style="width: 100%; margin: 2rem 0 1.5rem 0;">
        <div style="display: flex; justify-content: center;">
            <img src="data:image/jpeg;base64,{img_data}" width="90" style="border-radius: 50%; margin-bottom: 1rem; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5); border: 3px solid rgba(100, 120, 150, 0.3); margin-left: -60px;">
        </div>
        <h1 style="
            color: #ffffff; 
            font-size: 3rem; 
            font-weight: 900; 
            margin: 0; 
            letter-spacing: 3px;
            font-family: 'Orbitron', 'Bebas Neue', sans-serif !important;
            text-transform: uppercase;
            text-align: center;
            text-shadow: 0 2px 10px rgba(0, 0, 0, 0.5);
        ">
            FITFACT
        </h1>
        <p style="color: #b0c4de; font-size: 1.1rem; margin: 0.8rem 0 0 0; opacity: 0.95; letter-spacing: 0.5px; font-family: 'Poppins', sans-serif; text-align: center; font-weight: 600;">
            Evidence-Based Fitness Advice from Peer-Reviewed Research
        </p>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Orbitron:wght@900&family=Righteous&family=Russo+One&display=swap" rel="stylesheet">
    <div style="width: 100%; margin: 2rem 0 1.5rem 0;">
        <div style="text-align: center;">
            <div style="font-size: 3rem; margin-bottom: 0.8rem;">💪</div>
        </div>
        <h1 style="
            color: #ffffff; 
            font-size: 3rem; 
            font-weight: 900; 
            margin: 0; 
            letter-spacing: 3px;
            font-family: 'Orbitron', 'Bebas Neue', sans-serif !important;
            text-transform: uppercase;
            text-align: center;
            text-shadow: 0 2px 10px rgba(0, 0, 0, 0.5);
        ">
            FITFACT
        </h1>
        <p style="color: #b0c4de; font-size: 1.1rem; margin: 0.8rem 0 0 0; opacity: 0.95; letter-spacing: 0.5px; font-family: 'Poppins', sans-serif; text-align: center; font-weight: 600;">
            Evidence-Based Fitness Advice from Peer-Reviewed Research
        </p>
    </div>
    """, unsafe_allow_html=True)

# Feature Cards Section - Clickable Cards (No separate button)
if len(st.session_state.messages) == 0:
    st.markdown("""
    <div style="margin: 1.5rem 0 1rem 0;">
        <h3 style="text-align: center; color: #ffffff; font-size: 1.2rem; margin-bottom: 1.5rem; font-weight: bold;">
            ⚡︎ ⚡︎ Quick Start Questions
        </h3>
    </div>
    """, unsafe_allow_html=True)

    # All 5 cards in one row
    cols = st.columns(5)
    
    feature_cards = [
        {
            "icon": "⏲",
            "title": "Workout Frequency",
            "description": "How many times a week should I work out?",
            "question": "How many times a week should I work out?"
        },
        {
            "icon": "🍽️",
            "title": "Protein Intake",
            "description": "What's the ideal protein intake for muscle gain?",
            "question": "What's the ideal protein intake for muscle gain?"
        },
        {
            "icon": "♨",
            "title": "HIIT vs Cardio",
            "description": "Is HIIT better than steady cardio for fat loss?",
            "question": "Is HIIT better than steady cardio for fat loss?"
        },
        {
            "icon": "⟳",
            "title": "Recovery Methods",
            "description": "Best recovery methods after training?",
            "question": "Best recovery methods after training?"
        },
        {
            "icon": "🦾",
            "title": "Muscle & Cutting",
            "description": "Can I build muscle while cutting?",
            "question": "Can I build muscle while cutting?"
        }
    ]

    for idx, (col, card) in enumerate(zip(cols, feature_cards)):
        with col:
            # Create button that looks like a card
            if st.button(
                f"{card['icon']}\n\n{card['title']}\n\n{card['description']}",
                key=f"feature_{idx}",
                use_container_width=True
            ):
                st.session_state.pending_question = card['question']
                st.rerun()

    # Add styling CSS for clickable cards
    st.markdown("""
    <style>
    /* Feature card styling - entire card is clickable */
    div[data-testid="column"] button[kind="primary"] {
        background: linear-gradient(135deg, rgba(20, 30, 50, 0.95) 0%, rgba(30, 40, 60, 0.8) 100%) !important;
        border: 2px solid rgba(100, 120, 150, 0.4) !important;
        border-radius: 15px !important;
        padding: 1.5rem 1rem !important;
        min-height: 180px !important;
        color: white !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
        line-height: 1.5 !important;
        white-space: pre-line !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3) !important;
        cursor: pointer !important;
        font-family: 'Poppins', sans-serif !important;
    }
    
    /* Target all elements inside buttons with maximum specificity */
    button[kind="primary"] *,
    button[kind="primary"]::before,
    button[kind="primary"]::after,
    div[data-testid="column"] button *,
    div[data-testid="column"] button p,
    div[data-testid="column"] button div,
    div[data-testid="column"] button span,
    .stButton button *,
    .stButton button {
        font-family: 'Poppins', sans-serif !important;
    }
    
    /* Hover effect for cards */
    div[data-testid="column"] button[kind="primary"]:hover {
        transform: translateY(-8px) scale(1.03) !important;
        box-shadow: 0 12px 35px rgba(0, 0, 0, 0.5) !important;
        border-color: rgba(150, 170, 200, 0.6) !important;
        background: linear-gradient(135deg, rgba(30, 40, 60, 1) 0%, rgba(40, 50, 70, 0.95) 100%) !important;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("<div style='margin-bottom: 1.5rem;'></div>", unsafe_allow_html=True)

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
            try:
                result = st.session_state.pipeline.process_query(prompt, st.session_state.messages[:-1])
                
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": result['response'],
                    "metrics": result.get('metrics', {})
                })
            except Exception as e:
                print(f"❌ Error processing query: {e}")
                # Reinitialize pipeline on error
                st.session_state.pipeline = None
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": "I encountered a database error. Please try asking your question again."
                })
    
    st.rerun()

# Display all existing messages with custom alignment
chat_container = st.container()

with chat_container:
    for message in st.session_state.messages:
        role = message["role"]
        content = message["content"]
        
        if role == "user":
            # User message on the RIGHT with darker sky blue background
            st.markdown(f"""
            <div style="display: flex; justify-content: flex-end; margin: 1rem 0;">
                <div style="background-color: rgba(70, 130, 180, 0.85); border-radius: 15px; border-right: 3px solid #87CEEB; padding: 1rem; max-width: 70%; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);">
                    <div style="color: white; font-size: 0.95rem; line-height: 1.6; font-family: 'Poppins', sans-serif; font-weight: 400;">{content}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            # Assistant message on the LEFT
            st.markdown(f"""
            <div style="display: flex; justify-content: flex-start; margin: 1rem 0;">
                <div style="background-color: rgba(30, 40, 55, 0.85); border-radius: 15px; border-left: 3px solid #8b9dc3; padding: 1rem; max-width: 70%; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);">
                    <div style="color: white; font-size: 0.95rem; line-height: 1.6; font-family: 'Poppins', sans-serif; font-weight: 400;">{content}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Show metrics if available
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
    # Add user message immediately
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.session_state.total_queries += 1
    
    # Force rerun to display the user message
    st.rerun()

# Process the last message if it hasn't been processed yet
if (st.session_state.messages and 
    st.session_state.messages[-1]["role"] == "user" and 
    len(st.session_state.messages) > 0):
    
    # Check if this is the last message and if we need to process it
    # (i.e., there's no assistant response after it)
    needs_processing = True
    if len(st.session_state.messages) >= 2:
        if st.session_state.messages[-1]["role"] == "assistant":
            needs_processing = False
    
    if needs_processing and len(st.session_state.messages) > 0:
        last_user_message = st.session_state.messages[-1]["content"]
        
        # Check if it's a casual message
        is_casual, casual_text = is_casual_message(last_user_message)
        
        if is_casual:
            st.session_state.messages.append({
                "role": "assistant",
                "content": casual_text
            })
            st.rerun()
        else:
            if st.session_state.pipeline is None:
                loading_placeholder = st.empty()
                loading_placeholder.markdown("""
                <div class="loading-container" id="loading-init">
                    <div class="loading-icon">❚█══█❚</div>
                    <div class="loading-text">Initializing FitFact system...</div>
                </div>
                """, unsafe_allow_html=True)
                
                st.session_state.pipeline = init_pipeline()
                loading_placeholder.empty()
            
            if st.session_state.pipeline is None:
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": "Failed to initialize the system. Please check your database connection."
                })
                st.rerun()
            else:
                loading_placeholder = st.empty()
                loading_placeholder.markdown("""
                <div class="loading-container" id="loading-query">
                    <div class="loading-icon">❚█══█❚</div>
                    <div class="loading-text">Analyzing your question and searching research papers...</div>
                </div>
                """, unsafe_allow_html=True)
                
                result = st.session_state.pipeline.process_query(
                    last_user_message, 
                    st.session_state.messages[:-1]
                )
                
                loading_placeholder.empty()
                
                # Store assistant response and rerun
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
    <style>
    /* Hide any Streamlit debug text that appears after footer */
    .main > .block-container > div:last-child {
        display: none !important;
    }
    .main .element-container:has(+ div:empty) + div {
        display: none !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)