"""
Claim Analyzer for Fitness Misinformation Detection

Uses Claude to:
1. Extract specific fitness claims from video content
2. Fact-check each claim against PubMed research
3. Return verdicts with citations

This is the brain of the misinformation detector.
"""

import os
import sys
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

# Add parent path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()


class Verdict(Enum):
    """Verdict for a fitness claim"""
    SUPPORTED = "supported"           # Research supports this claim
    PARTIALLY_TRUE = "partially_true" # Some truth, but oversimplified or context-dependent
    NOT_SUPPORTED = "not_supported"   # Research contradicts or doesn't support
    INSUFFICIENT = "insufficient"     # Not enough evidence to evaluate
    NOT_FITNESS = "not_fitness"       # Not a fitness/health claim


@dataclass
class FitnessClaim:
    """A single fitness claim extracted from content"""
    claim_text: str
    claim_type: str  # e.g., "nutrition", "exercise", "supplement", "recovery"
    confidence: float  # How confident we are this is actually a claim (0-1)


@dataclass 
class FactCheckResult:
    """Result of fact-checking a single claim"""
    claim: FitnessClaim
    verdict: Verdict
    verdict_explanation: str
    supporting_evidence: List[str]  # Quotes from research
    contradicting_evidence: List[str]
    citations: List[Dict[str, str]]  # List of {pmid, title, authors, year}
    nuance: str  # Important context or caveats
    confidence_score: float  # 0-1, how confident we are in this verdict


@dataclass
class FactCheckReport:
    """Complete fact-check report for a video"""
    video_url: str
    video_title: str
    creator: str
    
    # Extracted content
    content_analyzed: str
    content_source: str  # "metadata" or "transcription"
    
    # Claims and verdicts
    claims: List[FitnessClaim] = field(default_factory=list)
    results: List[FactCheckResult] = field(default_factory=list)
    
    # Summary
    overall_assessment: str = ""
    credibility_score: float = 0.0  # 0-100
    
    # Processing info
    papers_searched: int = 0
    processing_time: float = 0.0
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'video_url': self.video_url,
            'video_title': self.video_title,
            'creator': self.creator,
            'content_source': self.content_source,
            'claims': [
                {
                    'claim_text': c.claim_text,
                    'claim_type': c.claim_type,
                    'confidence': c.confidence
                }
                for c in self.claims
            ],
            'results': [
                {
                    'claim': r.claim.claim_text,
                    'verdict': r.verdict.value,
                    'explanation': r.verdict_explanation,
                    'citations': r.citations,
                    'confidence': r.confidence_score
                }
                for r in self.results
            ],
            'overall_assessment': self.overall_assessment,
            'credibility_score': self.credibility_score,
            'papers_searched': self.papers_searched
        }


class ClaimAnalyzer:
    """
    Analyze video content for fitness claims and fact-check them.
    """
    
    def __init__(self):
        self.client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        self.model = "claude-sonnet-4-20250514"
    
    def extract_claims(self, content: str, video_title: str = "") -> List[FitnessClaim]:
        """
        Extract fitness claims from video content.
        
        Args:
            content: Combined text from video (title, description, transcript)
            video_title: Video title for context
            
        Returns:
            List of FitnessClaim objects
        """
        prompt = f"""Analyze this video content and extract specific FITNESS or HEALTH claims that can be fact-checked against scientific research.

VIDEO TITLE: {video_title}

CONTENT:
{content}

---

INSTRUCTIONS:
1. Identify SPECIFIC, VERIFIABLE claims about fitness, nutrition, exercise, supplements, or health
2. Ignore opinions, motivational statements, or vague advice
3. Focus on claims that make factual assertions about what works, what doesn't, or health outcomes

For each claim, provide:
- The exact claim (paraphrased clearly)
- Category: nutrition, exercise, supplement, recovery, weight_loss, muscle_building, or general_health
- Confidence (0.0-1.0) that this is actually a verifiable claim

FORMAT YOUR RESPONSE AS:
CLAIM 1:
Text: [the claim]
Category: [category]
Confidence: [0.0-1.0]

CLAIM 2:
Text: [the claim]
Category: [category]
Confidence: [0.0-1.0]

(continue for all claims found)

If no verifiable fitness claims are found, respond with:
NO_CLAIMS_FOUND

Be thorough but only extract claims that make specific factual assertions."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response_text = response.content[0].text
            
            if "NO_CLAIMS_FOUND" in response_text:
                return []
            
            return self._parse_claims(response_text)
            
        except Exception as e:
            print(f"Error extracting claims: {e}")
            return []
    
    def _parse_claims(self, response_text: str) -> List[FitnessClaim]:
        """Parse Claude's response into FitnessClaim objects"""
        claims = []
        
        # Split by CLAIM markers
        claim_blocks = re.split(r'CLAIM\s*\d+:', response_text, flags=re.IGNORECASE)
        
        for block in claim_blocks:
            if not block.strip():
                continue
            
            # Extract fields
            text_match = re.search(r'Text:\s*(.+?)(?=Category:|$)', block, re.DOTALL | re.IGNORECASE)
            category_match = re.search(r'Category:\s*(\w+)', block, re.IGNORECASE)
            confidence_match = re.search(r'Confidence:\s*([\d.]+)', block, re.IGNORECASE)
            
            if text_match:
                claim_text = text_match.group(1).strip()
                category = category_match.group(1).lower() if category_match else "general_health"
                confidence = float(confidence_match.group(1)) if confidence_match else 0.7
                
                claims.append(FitnessClaim(
                    claim_text=claim_text,
                    claim_type=category,
                    confidence=min(1.0, max(0.0, confidence))
                ))
        
        return claims
    
    def fact_check_claim(self, claim: FitnessClaim, papers: List[Dict]) -> FactCheckResult:
        """
        Fact-check a single claim against research papers.
        
        Args:
            claim: The claim to check
            papers: List of relevant papers with {pmid, title, abstract, authors, year}
            
        Returns:
            FactCheckResult with verdict and evidence
        """
        if not papers:
            return FactCheckResult(
                claim=claim,
                verdict=Verdict.INSUFFICIENT,
                verdict_explanation="No relevant research papers found to evaluate this claim.",
                supporting_evidence=[],
                contradicting_evidence=[],
                citations=[],
                nuance="Consider searching for more specific research or consulting a healthcare professional.",
                confidence_score=0.3
            )
        
        # Build paper context
        papers_context = ""
        for i, paper in enumerate(papers[:10], 1):  # Limit to 10 papers
            papers_context += f"""
PAPER {i}:
Title: {paper.get('title', 'Unknown')}
Authors: {paper.get('authors', 'Unknown')[:100]}
Year: {paper.get('year', paper.get('publication_date', 'Unknown'))[:4] if paper.get('year') or paper.get('publication_date') else 'Unknown'}
PMID: {paper.get('pmid', 'Unknown')}
Abstract: {paper.get('abstract', 'No abstract available')[:800]}
---
"""
        
        prompt = f"""You are a scientific fact-checker. Evaluate this fitness claim against the provided research papers.

CLAIM TO EVALUATE:
"{claim.claim_text}"
Category: {claim.claim_type}

RESEARCH PAPERS:
{papers_context}

---

Evaluate the claim and provide:

1. VERDICT (choose one):
   - SUPPORTED: Research clearly supports this claim
   - PARTIALLY_TRUE: Claim has some truth but is oversimplified, exaggerated, or context-dependent
   - NOT_SUPPORTED: Research contradicts or does not support this claim
   - INSUFFICIENT: Not enough evidence in these papers to evaluate

2. EXPLANATION: 2-3 sentences explaining your verdict

3. SUPPORTING_EVIDENCE: Quote 1-2 relevant findings that support the claim (if any)

4. CONTRADICTING_EVIDENCE: Quote 1-2 findings that contradict the claim (if any)

5. CITATIONS: List the PMIDs of papers you're citing (e.g., "PMID: 12345678")

6. NUANCE: Important context, limitations, or caveats the viewer should know

7. CONFIDENCE: 0.0-1.0 how confident you are in this verdict based on the evidence

FORMAT YOUR RESPONSE EXACTLY AS:
VERDICT: [verdict]
EXPLANATION: [explanation]
SUPPORTING_EVIDENCE:
- [quote 1]
- [quote 2]
CONTRADICTING_EVIDENCE:
- [quote 1]
- [quote 2]
CITATIONS: [PMID: xxxxx, PMID: xxxxx]
NUANCE: [important context]
CONFIDENCE: [0.0-1.0]"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response_text = response.content[0].text
            return self._parse_fact_check(claim, response_text, papers)
            
        except Exception as e:
            print(f"Error fact-checking claim: {e}")
            return FactCheckResult(
                claim=claim,
                verdict=Verdict.INSUFFICIENT,
                verdict_explanation=f"Error during fact-checking: {str(e)}",
                supporting_evidence=[],
                contradicting_evidence=[],
                citations=[],
                nuance="",
                confidence_score=0.0
            )
    
    def _parse_fact_check(self, claim: FitnessClaim, response_text: str, papers: List[Dict]) -> FactCheckResult:
        """Parse fact-check response into FactCheckResult"""
        
        # Extract verdict
        verdict_match = re.search(r'VERDICT:\s*(\w+)', response_text, re.IGNORECASE)
        verdict_str = verdict_match.group(1).upper() if verdict_match else "INSUFFICIENT"
        
        verdict_map = {
            "SUPPORTED": Verdict.SUPPORTED,
            "PARTIALLY_TRUE": Verdict.PARTIALLY_TRUE,
            "PARTIALLY": Verdict.PARTIALLY_TRUE,
            "NOT_SUPPORTED": Verdict.NOT_SUPPORTED,
            "NOTSUPPORTED": Verdict.NOT_SUPPORTED,
            "INSUFFICIENT": Verdict.INSUFFICIENT,
        }
        verdict = verdict_map.get(verdict_str, Verdict.INSUFFICIENT)
        
        # Extract explanation
        explanation_match = re.search(r'EXPLANATION:\s*(.+?)(?=SUPPORTING_EVIDENCE:|$)', response_text, re.DOTALL | re.IGNORECASE)
        explanation = explanation_match.group(1).strip() if explanation_match else "Unable to parse explanation."
        
        # Extract supporting evidence
        supporting_match = re.search(r'SUPPORTING_EVIDENCE:\s*(.+?)(?=CONTRADICTING_EVIDENCE:|$)', response_text, re.DOTALL | re.IGNORECASE)
        supporting = []
        if supporting_match:
            supporting = [e.strip().lstrip('-').strip() for e in supporting_match.group(1).strip().split('\n') if e.strip() and e.strip() != '-']
        
        # Extract contradicting evidence
        contradicting_match = re.search(r'CONTRADICTING_EVIDENCE:\s*(.+?)(?=CITATIONS:|$)', response_text, re.DOTALL | re.IGNORECASE)
        contradicting = []
        if contradicting_match:
            contradicting = [e.strip().lstrip('-').strip() for e in contradicting_match.group(1).strip().split('\n') if e.strip() and e.strip() != '-']
        
        # Extract citations
        citations_match = re.search(r'CITATIONS:\s*(.+?)(?=NUANCE:|$)', response_text, re.DOTALL | re.IGNORECASE)
        citations = []
        if citations_match:
            pmid_matches = re.findall(r'PMID:\s*(\d+)', citations_match.group(1))
            for pmid in pmid_matches:
                # Find the paper details
                for paper in papers:
                    if str(paper.get('pmid')) == pmid:
                        citations.append({
                            'pmid': pmid,
                            'title': paper.get('title', 'Unknown'),
                            'authors': paper.get('authors', 'Unknown')[:50],
                            'year': str(paper.get('year', paper.get('publication_date', '')))[:4]
                        })
                        break
        
        # Extract nuance
        nuance_match = re.search(r'NUANCE:\s*(.+?)(?=CONFIDENCE:|$)', response_text, re.DOTALL | re.IGNORECASE)
        nuance = nuance_match.group(1).strip() if nuance_match else ""
        
        # Extract confidence
        confidence_match = re.search(r'CONFIDENCE:\s*([\d.]+)', response_text, re.IGNORECASE)
        confidence = float(confidence_match.group(1)) if confidence_match else 0.5
        confidence = min(1.0, max(0.0, confidence))
        
        return FactCheckResult(
            claim=claim,
            verdict=verdict,
            verdict_explanation=explanation,
            supporting_evidence=supporting,
            contradicting_evidence=contradicting,
            citations=citations,
            nuance=nuance,
            confidence_score=confidence
        )
    
    def generate_overall_assessment(self, results: List[FactCheckResult], video_title: str) -> tuple:
        """
        Generate an overall assessment of the video's credibility.
        
        Returns:
            (assessment_text, credibility_score)
        """
        if not results:
            return "No verifiable fitness claims were found in this video.", 50.0
        
        # Calculate stats
        verdicts = [r.verdict for r in results]
        supported = verdicts.count(Verdict.SUPPORTED)
        partial = verdicts.count(Verdict.PARTIALLY_TRUE)
        not_supported = verdicts.count(Verdict.NOT_SUPPORTED)
        insufficient = verdicts.count(Verdict.INSUFFICIENT)
        
        total = len(verdicts)
        
        # Calculate credibility score
        # Supported = 100, Partial = 60, Not supported = 0, Insufficient = 50
        score_sum = (supported * 100) + (partial * 60) + (not_supported * 0) + (insufficient * 50)
        credibility_score = score_sum / total if total > 0 else 50.0
        
        # Generate assessment
        if credibility_score >= 80:
            assessment = f"This video's fitness claims are largely supported by research. {supported} out of {total} claims are backed by scientific evidence."
        elif credibility_score >= 60:
            assessment = f"This video contains a mix of accurate and oversimplified information. {supported + partial} out of {total} claims have some scientific basis, but some details may be exaggerated or lack context."
        elif credibility_score >= 40:
            assessment = f"Caution advised. Only {supported} out of {total} claims are fully supported by research. {not_supported} claims are not supported by evidence."
        else:
            assessment = f"This video contains significant misinformation. {not_supported} out of {total} claims are not supported by scientific research. Verify information with credible sources before following this advice."
        
        return assessment, credibility_score


# Quick test
if __name__ == "__main__":
    print("Claim Analyzer Test")
    print("=" * 50)
    
    # Test claim extraction
    test_content = """
    Want to build muscle fast? Here's what actually works:
    
    1. You NEED to eat 2g of protein per pound of bodyweight to build muscle
    2. Creatine is dangerous for your kidneys - avoid it!
    3. You should train each muscle group 3x per week for optimal growth
    4. Cold showers boost testosterone by 500%
    5. Intermittent fasting burns more fat than regular dieting
    
    #fitness #muscle #gains #workout
    """
    
    analyzer = ClaimAnalyzer()
    
    print("\nExtracting claims from test content...")
    claims = analyzer.extract_claims(test_content, "BUILD MUSCLE FAST - What Actually Works!")
    
    print(f"\nFound {len(claims)} claims:")
    for i, claim in enumerate(claims, 1):
        print(f"\n{i}. [{claim.claim_type}] (conf: {claim.confidence:.2f})")
        print(f"   {claim.claim_text}")
