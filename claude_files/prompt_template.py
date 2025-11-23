"""
FitFact Prompt Template
This template defines how Claude should respond to fitness questions
using PubMed research abstracts with proper citations.
"""

def create_fitness_prompt(user_question, pubmed_abstracts):
    """
    Creates a prompt for Claude that includes:
    1. System instructions for evidence-based responses
    2. User's fitness question
    3. PubMed research abstracts to reference
    
    Args:
        user_question (str): The fitness question from the user
        pubmed_abstracts (list): List of dicts with 'title', 'abstract', 'authors', 'year', 'pmid'
    
    Returns:
        str: Formatted prompt for Claude API
    """
    
    # Build the research context from PubMed abstracts
    research_context = ""
    for i, paper in enumerate(pubmed_abstracts, 1):
        research_context += f"""
Paper {i}:
Title: {paper['title']}
Authors: {paper['authors']}
Year: {paper['year']}
PMID: {paper['pmid']}
Abstract: {paper['abstract']}

---
"""
    
    # Create the full prompt with system instructions
    prompt = f"""You are FitFact, an evidence-based fitness advisor. Your role is to answer fitness questions using ONLY peer-reviewed scientific research from PubMed.

INSTRUCTIONS:
1. Answer the user's question based ONLY on the research abstracts provided below
2. Provide clear, practical advice that synthesizes findings across multiple studies
3. Include in-text citations using this format: (Author et al., Year, PMID: ######)
4. At the end, include a "References" section with full citations in this format:
   - Author et al. (Year). Title. PMID: ######
5. If the research doesn't directly answer the question, state what the research DOES say and acknowledge limitations
6. Prioritize meta-analyses and systematic reviews when available
7. Keep your answer concise but comprehensive (aim for 200-300 words)
8. Use accessible language - avoid unnecessary jargon

RESEARCH ABSTRACTS FROM PUBMED:
{research_context}

USER QUESTION:
{user_question}

Please provide your evidence-based answer with proper citations:"""
    
    return prompt


# Citation format specification
CITATION_FORMAT = {
    "in_text": "(Author et al., Year, PMID: ######)",
    "reference_list": "Author et al. (Year). Title. PMID: ######",
    "example_in_text": "(Smith et al., 2023, PMID: 12345678)",
    "example_reference": "Smith et al. (2023). Effects of creatine supplementation on muscle strength. PMID: 12345678"
}

# Response quality guidelines
RESPONSE_GUIDELINES = {
    "word_count": "200-300 words",
    "citation_requirement": "Every claim must be cited",
    "tone": "Professional but accessible",
    "structure": [
        "Direct answer to the question",
        "Supporting evidence from studies",
        "Practical recommendations",
        "Limitations or caveats if applicable",
        "References section"
    ]
}

if __name__ == "__main__":
    print("FitFact Prompt Template Module")
    print("=" * 60)
    print("\nCitation Format:")
    print(f"  In-text: {CITATION_FORMAT['in_text']}")
    print(f"  Reference: {CITATION_FORMAT['reference_list']}")
    print(f"\nResponse Guidelines:")
    print(f"  Length: {RESPONSE_GUIDELINES['word_count']}")
    print(f"  Citation Rule: {RESPONSE_GUIDELINES['citation_requirement']}")
    print(f"  Tone: {RESPONSE_GUIDELINES['tone']}")
    print("\n" + "=" * 60)