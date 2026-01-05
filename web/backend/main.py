"""
FitFact API Backend
FastAPI server connecting React frontend to PostgreSQL database
"""

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import sys
import time
import json
from datetime import datetime

# Get the project root directory
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.dirname(BACKEND_DIR)
PROJECT_ROOT = os.path.dirname(WEB_DIR)

# Add all necessary paths
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'database_files'))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'interface'))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'src', 'etl'))

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

from user_auth.user_manager import UserManager
from user_auth.session_manager import SessionManager

app = FastAPI(title="FitFact API", version="1.0.0")

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize managers
user_mgr = UserManager()
session_mgr = SessionManager()

# ==================== MODELS ====================

class GoogleAuthRequest(BaseModel):
    credential: str
    user_info: Optional[dict] = None

class ChatRequest(BaseModel):
    message: str
    conversation_history: Optional[List[dict]] = []

class ReferenceModel(BaseModel):
    num: int
    author: str
    year: str
    title: str
    journal: str
    pmid: str

class PointModel(BaseModel):
    title: str
    content: str

class StructuredDataModel(BaseModel):
    headline: str
    points: List[PointModel]
    takeaway: Optional[str] = None
    references: List[ReferenceModel]

class ChatResponse(BaseModel):
    response: str  # Plain text for backward compatibility
    structured: Optional[StructuredDataModel] = None  # New structured format
    papers_used: int
    response_time: float
    cached: bool

class PreferencesUpdate(BaseModel):
    fitness_goals: Optional[List[str]] = None
    experience_level: Optional[str] = None
    preferred_topics: Optional[List[str]] = None
    response_style: Optional[str] = None
    theme: Optional[str] = None

# ==================== AUTH HELPERS ====================

async def get_current_user(authorization: str = Header(None)) -> Optional[dict]:
    if not authorization:
        return None
    try:
        token = authorization.replace("Bearer ", "")
        user_id = session_mgr.validate_token(token)
        if user_id:
            user = user_mgr.get_user_by_id(user_id)
            if user:
                return user.to_dict()
    except:
        pass
    return None

async def require_auth(authorization: str = Header(...)) -> dict:
    user = await get_current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user

# ==================== AUTH ENDPOINTS ====================

@app.post("/api/auth/google")
async def google_auth(request: GoogleAuthRequest):
    try:
        user_info = request.user_info
        if not user_info or not user_info.get('sub'):
            raise HTTPException(status_code=401, detail="Missing user info")
        
        user = user_mgr.get_or_create_user(
            google_id=user_info.get('sub'),
            email=user_info.get('email'),
            display_name=user_info.get('name', user_info.get('email', '').split('@')[0]),
            profile_picture_url=user_info.get('picture')
        )
        
        session = session_mgr.create_session(user.user_id)
        
        return {
            "token": session.session_token,
            "user": {
                "user_id": user.user_id,
                "email": user.email,
                "display_name": user.display_name,
                "profile_picture_url": user.profile_picture_url,
                "account_type": user.account_type,
                "total_queries": user.total_queries,
            }
        }
    except Exception as e:
        print(f"Auth error: {e}")
        raise HTTPException(status_code=401, detail=str(e))

@app.post("/api/auth/logout")
async def logout(user: dict = Depends(require_auth), authorization: str = Header(...)):
    token = authorization.replace("Bearer ", "")
    session_mgr.invalidate_session(token)
    user_mgr.log_logout(user['user_id'])
    return {"success": True}

@app.get("/api/auth/me")
async def get_me(user: dict = Depends(require_auth)):
    return user

# ==================== CHAT ENDPOINTS ====================

def format_papers_as_references(papers: List[dict]) -> List[dict]:
    """Convert papers to reference format"""
    references = []
    for i, paper in enumerate(papers, 1):
        authors = paper.get('authors', [])
        if isinstance(authors, list):
            author_str = authors[0].split()[0] if authors else "Unknown"
        else:
            author_str = str(authors).split()[0] if authors else "Unknown"
        
        pub_date = paper.get('publication_date', '')
        year = pub_date.split('-')[0] if pub_date and '-' in pub_date else pub_date or "Unknown"
        
        references.append({
            "num": i,
            "author": author_str,
            "year": year,
            "title": paper.get('title', 'No title'),
            "journal": paper.get('journal', 'Unknown'),
            "pmid": paper.get('pmid', '')
        })
    return references

@app.post("/api/chat")
async def chat(request: ChatRequest, user: Optional[dict] = Depends(get_current_user)):
    """Process a chat message through FitFact pipeline with structured output."""
    start_time = time.time()
    
    try:
        from database import FitFactDB
        from cache_manager import CacheManager
        from claude_api import ClaudeProcessor
        from pubmed_query_optimizer import PubMedQueryOptimizer
        from pubmed_fetcher import search_pubmed, fetch_paper_details
        
        db = FitFactDB()
        cache = CacheManager(db)
        claude = ClaudeProcessor()
        optimizer = PubMedQueryOptimizer()
        
        user_query = request.message
        
        # Check cache first
        if len(user_query.split()) >= 8:
            cached = cache.smart_cache_lookup(user_query, threshold=0.7)
            if cached:
                response_time = time.time() - start_time
                
                if user:
                    user_mgr.add_to_history(
                        user_id=user['user_id'],
                        query_text=user_query,
                        response_text=cached['response_text'],
                        papers_used=0,
                        response_time_ms=int(response_time * 1000),
                        was_cached=True
                    )
                
                return {
                    "response": cached['response_text'],
                    "structured": None,
                    "papers_used": 0,
                    "response_time": response_time,
                    "cached": True
                }
        
        # Optimize query and search PubMed
        optimized = optimizer.optimize_query(user_query)
        
        papers = []
        seen_pmids = set()
        
        for search_query in optimized['search_strategies'][:3]:
            if len(papers) >= 10:
                break
            try:
                pmids = search_pubmed(search_query, max_results=5)
                for pmid in pmids:
                    if pmid not in seen_pmids and len(papers) < 10:
                        paper = fetch_paper_details(pmid)
                        if paper:
                            seen_pmids.add(pmid)
                            papers.append(paper)
            except:
                continue
        
        if not papers:
            return {
                "response": "I couldn't find relevant research papers for your question. Please try rephrasing.",
                "structured": None,
                "papers_used": 0,
                "response_time": time.time() - start_time,
                "cached": False
            }
        
        # Generate response with Claude
        claude_response = claude.generate_response(
            papers[:10], 
            user_query, 
            request.conversation_history
        )
        
        response_text = claude_response.get('text', 'Error generating response')
        structured_data = claude_response.get('structured_data')
        response_time = time.time() - start_time
        
        # If we got structured data from Claude, use it
        # Otherwise, build structured data from papers
        if not structured_data:
            # Build basic structured response from the text
            references = format_papers_as_references(papers[:6])
            structured_data = {
                "headline": response_text.split('.')[0] + '.' if response_text else "",
                "points": [],
                "takeaway": None,
                "references": references
            }
        else:
            # Ensure references have correct PMIDs from actual papers
            if structured_data.get('references'):
                for ref in structured_data['references']:
                    # Find matching paper by author/year
                    for paper in papers:
                        pub_date = paper.get('publication_date', '')
                        year = pub_date.split('-')[0] if '-' in pub_date else pub_date
                        if year == ref.get('year'):
                            ref['pmid'] = paper.get('pmid', ref.get('pmid', ''))
                            ref['title'] = paper.get('title', ref.get('title', ''))
                            ref['journal'] = paper.get('journal', ref.get('journal', ''))
                            break
        
        # Cache the response
        try:
            paper_ids = []
            for paper in papers:
                paper_id = db.save_paper(
                    pmid=paper['pmid'],
                    title=paper['title'],
                    abstract=paper['abstract'],
                    authors=str(paper.get('authors', [])),
                    pub_date=paper.get('publication_date', '2024-01-01'),
                    journal=paper.get('journal', 'Unknown'),
                    study_type='research'
                )
                paper_ids.append(paper_id)
            
            if paper_ids:
                cache.store_in_cache(user_query, response_text, paper_ids)
        except:
            pass
        
        # Save to history if authenticated
        if user:
            user_mgr.add_to_history(
                user_id=user['user_id'],
                query_text=user_query,
                response_text=response_text,
                papers_used=len(papers),
                response_time_ms=int(response_time * 1000),
                was_cached=False
            )
        
        db.close()
        
        return {
            "response": response_text,
            "structured": structured_data,
            "papers_used": len(papers),
            "response_time": response_time,
            "cached": False
        }
        
    except Exception as e:
        print(f"Chat error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# ==================== USER ENDPOINTS ====================

@app.get("/api/user/history")
async def get_history(user: dict = Depends(require_auth), limit: int = 50):
    history = user_mgr.get_history(user['user_id'], limit=limit)
    return [
        {
            "history_id": h.history_id,
            "query": h.query_text,
            "response": h.response_text,
            "papers_used": h.papers_used,
            "created_at": h.created_at.isoformat(),
            "is_saved": h.is_saved,
            "is_favorite": h.is_favorite,
        }
        for h in history
    ]

@app.get("/api/user/preferences")
async def get_preferences(user: dict = Depends(require_auth)):
    prefs = user_mgr.get_preferences(user['user_id'])
    if prefs:
        return prefs.to_dict()
    return {}

@app.put("/api/user/preferences")
async def update_preferences(updates: PreferencesUpdate, user: dict = Depends(require_auth)):
    update_dict = {k: v for k, v in updates.dict().items() if v is not None}
    prefs = user_mgr.update_preferences(user['user_id'], update_dict)
    return prefs.to_dict()

@app.post("/api/user/save/{history_id}")
async def save_response(history_id: int, user: dict = Depends(require_auth)):
    saved_id = user_mgr.save_response(user['user_id'], history_id)
    return {"saved_id": saved_id}

@app.delete("/api/user/save/{history_id}")
async def unsave_response(history_id: int, user: dict = Depends(require_auth)):
    success = user_mgr.unsave_response(user['user_id'], history_id)
    return {"success": success}

@app.get("/api/user/saved")
async def get_saved(user: dict = Depends(require_auth)):
    saved = user_mgr.get_saved_responses(user['user_id'])
    return saved

# ==================== HEALTH CHECK ====================

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
