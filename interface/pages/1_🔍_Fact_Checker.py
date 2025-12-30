"""
FitFact Misinformation Checker - Streamlit Page

A dedicated page for fact-checking fitness videos from social media.
Paste a TikTok, Instagram, YouTube, or X link and get a research-backed verdict.
"""

import streamlit as st
import sys
import os
import base64
from pathlib import Path

# Add paths for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
interface_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(interface_dir)
sys.path.append(project_root)

from misinformation_checker import (
    MisinformationChecker, 
    CheckerConfig, 
    format_report_for_display,
    URLParser, 
    PlatformType,
    Verdict
)

# Page config
st.set_page_config(
    page_title="FitFact - Misinformation Checker",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Get paths for assets
BG_PATH = os.path.join(project_root, "assets", "gym_bg.jpg")
logo_path = os.path.join(project_root, "assets", "fitfact_logo.jpg")


def get_base64_image(path: str) -> str:
    if os.path.exists(path):
        return base64.b64encode(Path(path).read_bytes()).decode()
    return ""


# Styling
bg_base64 = get_base64_image(BG_PATH) if os.path.exists(BG_PATH) else ""

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&family=Orbitron:wght@900&display=swap');

body, p, div, span, button, input, textarea {{
    font-family: 'Poppins', sans-serif;
}}

.stApp {{
    background-color: #0a0f1a;
    {"background-image: linear-gradient(rgba(0, 0, 0, 0.75), rgba(0, 0, 0, 0.75)), url('data:image/jpg;base64," + bg_base64 + "');" if bg_base64 else ""}
    background-position: center top;
    background-repeat: no-repeat;
    background-attachment: fixed;
    background-size: cover;
}}

.main-title {{
    font-family: 'Orbitron', sans-serif;
    color: #ffffff;
    font-size: 2.5rem;
    font-weight: 900;
    text-align: center;
    letter-spacing: 3px;
    text-shadow: 0 2px 10px rgba(0, 0, 0, 0.5);
    margin-bottom: 0.5rem;
}}

.subtitle {{
    color: #b0c4de;
    font-size: 1.1rem;
    text-align: center;
    margin-bottom: 2rem;
}}

.url-input-container {{
    background: rgba(20, 30, 50, 0.9);
    border-radius: 15px;
    padding: 2rem;
    margin: 1rem 0;
    border: 1px solid rgba(100, 120, 150, 0.3);
}}

.credibility-score {{
    font-size: 3rem;
    font-weight: bold;
    text-align: center;
}}

.score-high {{ color: #4CAF50; }}
.score-medium {{ color: #FFC107; }}
.score-low {{ color: #f44336; }}

.platform-badge {{
    display: inline-block;
    padding: 0.3rem 0.8rem;
    border-radius: 20px;
    font-size: 0.85rem;
    font-weight: 500;
    margin-right: 0.5rem;
}}

.platform-youtube {{ background: #FF0000; color: white; }}
.platform-tiktok {{ background: #000000; color: white; border: 1px solid #69C9D0; }}
.platform-instagram {{ background: linear-gradient(45deg, #f09433, #e6683c, #dc2743, #cc2366, #bc1888); color: white; }}
.platform-twitter {{ background: #1DA1F2; color: white; }}

.stTextInput > div > div > input {{
    background-color: rgba(40, 50, 70, 0.8) !important;
    border: 1px solid rgba(100, 120, 150, 0.4) !important;
    color: white !important;
    border-radius: 10px !important;
    padding: 0.75rem 1rem !important;
}}

.stButton > button {{
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 0.75rem 2rem !important;
    font-weight: 600 !important;
    transition: all 0.3s ease !important;
}}

.stButton > button:hover {{
    transform: translateY(-2px) !important;
    box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4) !important;
}}

.stProgress > div > div > div {{
    background: linear-gradient(90deg, #667eea, #764ba2) !important;
}}
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'fact_check_result' not in st.session_state:
    st.session_state.fact_check_result = None
if 'checking_in_progress' not in st.session_state:
    st.session_state.checking_in_progress = False


# Header
st.markdown('<h1 class="main-title">🔍 MISINFORMATION CHECKER</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Paste a fitness video link. Get research-backed verdicts.</p>', unsafe_allow_html=True)

# Platform badges
st.markdown("""
<div style="text-align: center; margin-bottom: 2rem;">
    <span class="platform-badge platform-youtube">YouTube</span>
    <span class="platform-badge platform-tiktok">TikTok</span>
    <span class="platform-badge platform-instagram">Instagram</span>
    <span class="platform-badge platform-twitter">X / Twitter</span>
</div>
""", unsafe_allow_html=True)

# URL Input Section
col1, col2, col3 = st.columns([1, 3, 1])

with col2:
    st.markdown('<div class="url-input-container">', unsafe_allow_html=True)
    
    video_url = st.text_input(
        "Paste video URL",
        placeholder="https://tiktok.com/@user/video/... or youtube.com/watch?v=...",
        label_visibility="collapsed"
    )
    
    # Options
    col_opt1, col_opt2 = st.columns(2)
    with col_opt1:
        deep_analysis = st.checkbox(
            "🎤 Deep Analysis (transcribe audio)", 
            help="Downloads and transcribes the video. Takes longer but catches claims only spoken, not written."
        )
    
    with col_opt2:
        # Show detected platform
        if video_url:
            platform = URLParser.detect_platform(video_url)
            if platform != PlatformType.UNKNOWN:
                platform_names = {
                    PlatformType.YOUTUBE: "🎬 YouTube",
                    PlatformType.TIKTOK: "🎵 TikTok",
                    PlatformType.INSTAGRAM: "📸 Instagram",
                    PlatformType.TWITTER: "🐦 X/Twitter"
                }
                st.success(f"Detected: {platform_names.get(platform, 'Unknown')}")
            else:
                st.warning("⚠️ Unknown platform")
    
    # Check button
    check_button = st.button("🔬 Fact-Check This Video", use_container_width=True, type="primary")
    
    st.markdown('</div>', unsafe_allow_html=True)

# Process the URL
if check_button and video_url:
    st.session_state.checking_in_progress = True
    st.session_state.fact_check_result = None
    
    # Validate URL first
    parsed = URLParser.parse(video_url)
    
    if not parsed.is_valid:
        st.error(f"❌ {parsed.error_message}")
    else:
        # Progress container
        progress_container = st.container()
        
        with progress_container:
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            def update_progress(step: str, progress: float):
                progress_bar.progress(progress)
                status_text.markdown(f"**{step}**")
            
            try:
                # Initialize checker
                config = CheckerConfig(
                    force_transcription=deep_analysis,
                    enable_transcription=deep_analysis,
                    whisper_model="base"
                )
                checker = MisinformationChecker(config)
                
                # Run fact-check
                report = checker.check_video(
                    video_url, 
                    deep_analysis=deep_analysis,
                    progress_callback=update_progress
                )
                
                st.session_state.fact_check_result = report
                
            except Exception as e:
                st.error(f"Error: {str(e)}")
            
            finally:
                progress_bar.empty()
                status_text.empty()
                st.session_state.checking_in_progress = False

# Display Results
if st.session_state.fact_check_result:
    report = st.session_state.fact_check_result
    
    if report.error_message:
        st.error(f"❌ {report.error_message}")
    else:
        st.markdown("---")
        
        # Video Info Header
        col_info1, col_info2 = st.columns([2, 1])
        
        with col_info1:
            st.markdown(f"### 📹 {report.video_title or 'Video'}")
            if report.creator:
                st.markdown(f"**Creator:** {report.creator}")
            st.caption(f"Content source: {report.content_source} | Processed in {report.processing_time:.1f}s")
        
        with col_info2:
            # Credibility Score
            score = report.credibility_score
            score_class = "score-high" if score >= 70 else ("score-medium" if score >= 40 else "score-low")
            st.markdown(f"""
            <div style="text-align: center; background: rgba(30, 40, 60, 0.9); border-radius: 15px; padding: 1rem;">
                <div style="color: #b0c4de; font-size: 0.9rem;">CREDIBILITY SCORE</div>
                <div class="credibility-score {score_class}">{score:.0f}</div>
                <div style="color: #888; font-size: 0.8rem;">out of 100</div>
            </div>
            """, unsafe_allow_html=True)
        
        # Overall Assessment
        st.markdown("### 📋 Overall Assessment")
        
        assessment_color = "#4CAF50" if score >= 70 else ("#FFC107" if score >= 40 else "#f44336")
        st.markdown(f"""
        <div style="background: rgba(30, 40, 60, 0.9); border-radius: 12px; padding: 1.5rem; 
                    border-left: 4px solid {assessment_color}; margin: 1rem 0;">
            <p style="color: white; font-size: 1.1rem; margin: 0;">{report.overall_assessment}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Individual Claims
        if report.results:
            st.markdown(f"### 🔎 Claim-by-Claim Analysis ({len(report.results)} claims)")
            
            verdict_styles = {
                Verdict.SUPPORTED: ("✅", "SUPPORTED", "#4CAF50"),
                Verdict.PARTIALLY_TRUE: ("⚠️", "PARTIALLY TRUE", "#FFC107"),
                Verdict.NOT_SUPPORTED: ("❌", "NOT SUPPORTED", "#f44336"),
                Verdict.INSUFFICIENT: ("❓", "INSUFFICIENT EVIDENCE", "#9E9E9E"),
                Verdict.NOT_FITNESS: ("➖", "NOT A FITNESS CLAIM", "#9E9E9E"),
            }
            
            for i, result in enumerate(report.results, 1):
                emoji, label, color = verdict_styles.get(
                    result.verdict, 
                    ("❓", "UNKNOWN", "#9E9E9E")
                )
                
                with st.expander(f"{emoji} Claim {i}: {result.claim.claim_text[:80]}...", expanded=(i <= 3)):
                    # Verdict header
                    st.markdown(f"""
                    <div style="display: flex; align-items: center; margin-bottom: 1rem;">
                        <span style="background: {color}; color: white; padding: 0.3rem 0.8rem; 
                                     border-radius: 20px; font-weight: 600; font-size: 0.85rem;">
                            {emoji} {label}
                        </span>
                        <span style="color: #888; margin-left: 1rem; font-size: 0.85rem;">
                            Confidence: {result.confidence_score*100:.0f}%
                        </span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Full claim
                    st.markdown(f"**Claim:** \"{result.claim.claim_text}\"")
                    st.markdown(f"**Category:** {result.claim.claim_type}")
                    
                    # Explanation
                    st.markdown("---")
                    st.markdown(f"**Analysis:** {result.verdict_explanation}")
                    
                    # Evidence columns
                    ev_col1, ev_col2 = st.columns(2)
                    
                    with ev_col1:
                        if result.supporting_evidence:
                            st.markdown("**✅ Supporting Evidence:**")
                            for evidence in result.supporting_evidence[:2]:
                                if evidence and evidence.strip():
                                    st.markdown(f"> _{evidence}_")
                    
                    with ev_col2:
                        if result.contradicting_evidence:
                            st.markdown("**❌ Contradicting Evidence:**")
                            for evidence in result.contradicting_evidence[:2]:
                                if evidence and evidence.strip():
                                    st.markdown(f"> _{evidence}_")
                    
                    # Nuance
                    if result.nuance:
                        st.info(f"💡 **Important context:** {result.nuance}")
                    
                    # Citations
                    if result.citations:
                        st.markdown("**📚 Citations:**")
                        for cite in result.citations[:3]:
                            pmid = cite.get('pmid', '')
                            title = cite.get('title', 'Unknown')[:70]
                            st.markdown(f"- [{title}...](https://pubmed.ncbi.nlm.nih.gov/{pmid}/) (PMID: {pmid})")
        
        # Footer stats
        st.markdown("---")
        stat_cols = st.columns(4)
        with stat_cols[0]:
            st.metric("Claims Analyzed", len(report.results))
        with stat_cols[1]:
            st.metric("Papers Searched", report.papers_searched)
        with stat_cols[2]:
            supported = sum(1 for r in report.results if r.verdict == Verdict.SUPPORTED)
            st.metric("Claims Supported", f"{supported}/{len(report.results)}")
        with stat_cols[3]:
            st.metric("Processing Time", f"{report.processing_time:.1f}s")

# Sidebar - Back to main app
with st.sidebar:
    st.markdown("### 🏠 Navigation")
    st.page_link("app.py", label="← Back to FitFact Chat", icon="💬")
    
    st.markdown("---")
    st.markdown("### ℹ️ How it works")
    st.markdown("""
    1. **Paste a link** from YouTube, TikTok, Instagram, or X
    2. We **extract** the video's title, description, and captions
    3. **AI identifies** specific fitness claims
    4. Each claim is **fact-checked** against PubMed research
    5. You get a **verdict** with citations
    """)
    
    st.markdown("---")
    st.markdown("### 🎤 Deep Analysis")
    st.markdown("""
    Enable this option to **transcribe the audio** of the video. 
    This catches claims that are spoken but not written in the description.
    
    **Note:** Requires ffmpeg and whisper installed.
    """)
