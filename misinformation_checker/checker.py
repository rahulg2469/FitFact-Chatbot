"""
Misinformation Checker - Main Orchestrator

This is the main entry point for the video fact-checking feature.
It coordinates:
1. URL parsing
2. Metadata extraction (fast path)
3. Video transcription (slow path, if needed)
4. Claim extraction
5. Fact-checking against PubMed
6. Report generation
"""

import os
import sys
import time
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

# Add parent path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from .video_extractors.url_parser import URLParser, PlatformType
from .video_extractors.metadata_extractor import MetadataExtractor, VideoMetadata
from .video_extractors.video_transcriber import VideoTranscriber, TranscriptionResult
from .claim_analyzer import ClaimAnalyzer, FitnessClaim, FactCheckResult, FactCheckReport, Verdict


@dataclass
class CheckerConfig:
    """Configuration for the misinformation checker"""
    # Fast path settings
    min_content_length: int = 50  # Minimum chars to skip transcription
    
    # Transcription settings
    enable_transcription: bool = True  # Allow fallback to transcription
    force_transcription: bool = False  # Always transcribe, even if metadata is sufficient
    max_video_duration: int = 300  # Max 5 minutes for transcription
    whisper_model: str = "base"  # tiny, base, small, medium, large
    
    # Fact-checking settings
    max_claims_to_check: int = 10  # Limit claims per video
    max_papers_per_claim: int = 10  # Papers to search per claim
    
    # PubMed settings
    use_local_db: bool = True  # Search local paper database first
    search_live_pubmed: bool = True  # Also search live PubMed


class MisinformationChecker:
    """
    Main class for checking fitness misinformation in videos.
    
    Usage:
        checker = MisinformationChecker()
        report = checker.check_video("https://tiktok.com/@user/video/123")
        
        # Or with deep analysis (transcription)
        report = checker.check_video(url, deep_analysis=True)
    """
    
    def __init__(self, config: CheckerConfig = None):
        self.config = config or CheckerConfig()
        self.claim_analyzer = ClaimAnalyzer()
        self.transcriber = None  # Lazy load
        
        # Try to import PubMed fetcher
        try:
            from src.etl.pubmed_fetcher import search_pubmed, fetch_paper_details
            self.search_pubmed = search_pubmed
            self.fetch_paper_details = fetch_paper_details
            self._pubmed_available = True
        except ImportError:
            print("Warning: PubMed fetcher not available")
            self._pubmed_available = False
        
        # Try to import local database
        try:
            from database_files.database import FitFactDB
            self.db = FitFactDB()
            self._db_available = True
        except Exception as e:
            print(f"Warning: Local database not available: {e}")
            self._db_available = False
    
    def check_video(self, url: str, deep_analysis: bool = False, 
                    progress_callback=None) -> FactCheckReport:
        """
        Check a video for fitness misinformation.
        
        Args:
            url: Video URL (YouTube, TikTok, Instagram, X)
            deep_analysis: If True, always transcribe the video
            progress_callback: Optional function to report progress
                              signature: callback(step: str, progress: float)
        
        Returns:
            FactCheckReport with claims and verdicts
        """
        start_time = time.time()
        
        def update_progress(step: str, progress: float):
            if progress_callback:
                progress_callback(step, progress)
            print(f"[{progress*100:.0f}%] {step}")
        
        # Step 1: Parse URL
        update_progress("Parsing URL...", 0.05)
        parsed = URLParser.parse(url)
        
        if not parsed.is_valid:
            return FactCheckReport(
                video_url=url,
                video_title="",
                creator="",
                content_analyzed="",
                content_source="none",
                error_message=parsed.error_message,
                processing_time=time.time() - start_time
            )
        
        # Step 2: Extract metadata (fast path)
        update_progress("Extracting video metadata...", 0.15)
        metadata = MetadataExtractor.extract(url)
        
        if not metadata.extraction_successful:
            return FactCheckReport(
                video_url=url,
                video_title="",
                creator="",
                content_analyzed="",
                content_source="metadata",
                error_message=f"Could not access video: {metadata.error_message}",
                processing_time=time.time() - start_time
            )
        
        # Step 3: Decide if we need transcription
        content_to_analyze = metadata.combined_text
        content_source = "metadata"
        
        needs_transcription = (
            deep_analysis or 
            self.config.force_transcription or
            not metadata.has_sufficient_content
        )
        
        if needs_transcription and self.config.enable_transcription:
            update_progress("Insufficient metadata, transcribing video...", 0.25)
            
            if self.transcriber is None:
                self.transcriber = VideoTranscriber(model_size=self.config.whisper_model)
            
            # Check dependencies first
            deps = VideoTranscriber.check_dependencies()
            missing_deps = [k for k, v in deps.items() if not v]
            
            if missing_deps:
                update_progress(f"Skipping transcription (missing: {', '.join(missing_deps)})", 0.30)
            else:
                transcription = self.transcriber.transcribe(
                    url, 
                    force=(metadata.duration or 0) <= self.config.max_video_duration
                )
                
                if transcription.success and transcription.transcript:
                    # Combine metadata with transcription
                    content_to_analyze = f"""
Title: {metadata.title}

Description: {metadata.description}

Transcript: {transcription.transcript}

Hashtags: {' '.join(metadata.hashtags)}
"""
                    content_source = "metadata+transcription"
                    update_progress("Transcription complete", 0.40)
                else:
                    update_progress(f"Transcription failed: {transcription.error_message}", 0.40)
        else:
            update_progress("Using metadata (sufficient content found)", 0.30)
        
        # Step 4: Extract claims
        update_progress("Analyzing content for fitness claims...", 0.45)
        claims = self.claim_analyzer.extract_claims(content_to_analyze, metadata.title)
        
        if not claims:
            return FactCheckReport(
                video_url=url,
                video_title=metadata.title,
                creator=metadata.creator,
                content_analyzed=content_to_analyze[:500],
                content_source=content_source,
                claims=[],
                results=[],
                overall_assessment="No verifiable fitness claims were found in this video.",
                credibility_score=50.0,
                processing_time=time.time() - start_time
            )
        
        update_progress(f"Found {len(claims)} fitness claims", 0.50)
        
        # Limit claims
        claims = claims[:self.config.max_claims_to_check]
        
        # Step 5: Fact-check each claim
        results = []
        total_papers_searched = 0
        
        for i, claim in enumerate(claims):
            progress = 0.50 + (0.40 * (i / len(claims)))
            update_progress(f"Fact-checking claim {i+1}/{len(claims)}...", progress)
            
            # Search for relevant papers
            papers = self._search_papers_for_claim(claim)
            total_papers_searched += len(papers)
            
            # Fact-check the claim
            result = self.claim_analyzer.fact_check_claim(claim, papers)
            results.append(result)
        
        # Step 6: Generate overall assessment
        update_progress("Generating assessment...", 0.95)
        overall_assessment, credibility_score = self.claim_analyzer.generate_overall_assessment(
            results, metadata.title
        )
        
        update_progress("Complete!", 1.0)
        
        return FactCheckReport(
            video_url=url,
            video_title=metadata.title,
            creator=metadata.creator,
            content_analyzed=content_to_analyze[:1000],
            content_source=content_source,
            claims=claims,
            results=results,
            overall_assessment=overall_assessment,
            credibility_score=credibility_score,
            papers_searched=total_papers_searched,
            processing_time=time.time() - start_time
        )
    
    def _search_papers_for_claim(self, claim: FitnessClaim) -> List[Dict]:
        """Search for papers relevant to a claim"""
        papers = []
        seen_pmids = set()
        
        # Build search query from claim
        search_query = self._build_search_query(claim)
        
        # Search local database first
        if self.config.use_local_db and self._db_available:
            try:
                local_papers = self.db.search_papers(search_query, limit=5)
                for paper in local_papers:
                    pmid = str(paper.get('pmid', ''))
                    if pmid and pmid not in seen_pmids:
                        seen_pmids.add(pmid)
                        papers.append(paper)
            except Exception as e:
                print(f"Local DB search failed: {e}")
        
        # Search live PubMed
        if self.config.search_live_pubmed and self._pubmed_available:
            try:
                # Search with claim text
                pmids = self.search_pubmed(search_query, max_results=self.config.max_papers_per_claim)
                
                for pmid in pmids:
                    if pmid not in seen_pmids and len(papers) < self.config.max_papers_per_claim:
                        paper = self.fetch_paper_details(pmid)
                        if paper:
                            seen_pmids.add(pmid)
                            papers.append(paper)
            except Exception as e:
                print(f"PubMed search failed: {e}")
        
        return papers
    
    def _build_search_query(self, claim: FitnessClaim) -> str:
        """Build a PubMed search query from a claim"""
        # Extract key terms from the claim
        claim_text = claim.claim_text.lower()
        
        # Category-specific keywords
        category_terms = {
            "nutrition": ["diet", "nutrition", "intake", "consumption"],
            "exercise": ["exercise", "training", "workout", "physical activity"],
            "supplement": ["supplementation", "supplement", "ergogenic"],
            "recovery": ["recovery", "rest", "sleep", "regeneration"],
            "weight_loss": ["weight loss", "fat loss", "body composition"],
            "muscle_building": ["muscle", "hypertrophy", "strength", "resistance training"],
        }
        
        # Start with the claim text (first 100 chars)
        query_parts = [claim_text[:100]]
        
        # Add category terms
        if claim.claim_type in category_terms:
            query_parts.extend(category_terms[claim.claim_type][:2])
        
        # Join and clean
        query = ' '.join(query_parts)
        
        # Remove common words that don't help searching
        stopwords = ['the', 'is', 'are', 'was', 'were', 'you', 'your', 'should', 'must', 'need', 'will']
        for word in stopwords:
            query = query.replace(f' {word} ', ' ')
        
        return query.strip()


def format_report_for_display(report: FactCheckReport) -> str:
    """Format a fact-check report for text display"""
    
    lines = []
    lines.append("=" * 60)
    lines.append("FITFACT MISINFORMATION CHECK REPORT")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"Video: {report.video_title}")
    lines.append(f"Creator: {report.creator}")
    lines.append(f"URL: {report.video_url}")
    lines.append(f"Content Source: {report.content_source}")
    lines.append("")
    
    # Overall assessment
    lines.append("-" * 60)
    lines.append("OVERALL ASSESSMENT")
    lines.append("-" * 60)
    lines.append(report.overall_assessment)
    lines.append(f"\nCredibility Score: {report.credibility_score:.0f}/100")
    lines.append("")
    
    # Individual claims
    if report.results:
        lines.append("-" * 60)
        lines.append(f"DETAILED ANALYSIS ({len(report.results)} claims)")
        lines.append("-" * 60)
        
        verdict_emojis = {
            Verdict.SUPPORTED: "✅",
            Verdict.PARTIALLY_TRUE: "⚠️",
            Verdict.NOT_SUPPORTED: "❌",
            Verdict.INSUFFICIENT: "❓",
            Verdict.NOT_FITNESS: "➖"
        }
        
        for i, result in enumerate(report.results, 1):
            emoji = verdict_emojis.get(result.verdict, "❓")
            lines.append(f"\n{i}. {emoji} {result.verdict.value.upper()}")
            lines.append(f"   Claim: \"{result.claim.claim_text}\"")
            lines.append(f"   {result.verdict_explanation}")
            
            if result.citations:
                lines.append("   Citations:")
                for cite in result.citations[:3]:
                    lines.append(f"     - {cite.get('title', 'Unknown')[:60]}... (PMID: {cite.get('pmid')})")
            
            if result.nuance:
                lines.append(f"   Note: {result.nuance}")
    
    # Footer
    lines.append("")
    lines.append("-" * 60)
    lines.append(f"Papers searched: {report.papers_searched}")
    lines.append(f"Processing time: {report.processing_time:.1f}s")
    lines.append("=" * 60)
    
    return "\n".join(lines)


# Command-line interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Check fitness videos for misinformation")
    parser.add_argument("url", help="Video URL to check")
    parser.add_argument("--deep", action="store_true", help="Force video transcription")
    parser.add_argument("--whisper-model", default="base", help="Whisper model size")
    
    args = parser.parse_args()
    
    print(f"\nChecking video: {args.url}")
    print("-" * 60)
    
    config = CheckerConfig(
        force_transcription=args.deep,
        whisper_model=args.whisper_model
    )
    
    checker = MisinformationChecker(config)
    report = checker.check_video(args.url, deep_analysis=args.deep)
    
    print("\n")
    print(format_report_for_display(report))
