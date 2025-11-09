"""
Citation Formatter - Elenta Suzan Jacob
Formats research paper citations in various styles
"""

def format_apa(paper):
    """Format paper in APA style"""
    authors = ", ".join(paper.get('authors', ['Unknown']))
    year = paper.get('publication_date', 'n.d.')[:4]
    title = paper.get('title', 'Untitled')
    journal = paper.get('journal', 'Unknown Journal')
    pmid = paper.get('pmid', 'Unknown')
    
    return f"{authors} ({year}). {title}. {journal}. PMID: {pmid}"

def format_mla(paper):
    """Format paper in MLA style"""
    authors = paper.get('authors', ['Unknown'])
    author_str = authors[0] if authors else "Unknown"
    title = paper.get('title', 'Untitled')
    journal = paper.get('journal', 'Unknown Journal')
    year = paper.get('publication_date', 'n.d.')[:4]
    pmid = paper.get('pmid', 'Unknown')
    
    return f'{author_str}. "{title}." {journal}, {year}. PMID: {pmid}.'

def format_inline(paper):
    """Format paper as inline citation for chatbot responses"""
    authors = paper.get('authors', ['Unknown'])
    first_author = authors[0].split()[0] if authors else "Unknown"
    year = paper.get('publication_date', 'n.d.')[:4]
    pmid = paper.get('pmid', 'Unknown')
    
    return f"({first_author} et al., {year}, PMID: {pmid})"

def format_for_response(papers):
    """Format multiple papers for chatbot response with links"""
    citations = []
    for i, paper in enumerate(papers, 1):
        pmid = paper.get('pmid', 'Unknown')
        authors = paper.get('authors', ['Unknown'])
        year = paper.get('publication_date', 'n.d.')[:4]
        title = paper.get('title', 'Untitled')
        
        first_author = authors[0].split()[0] if authors else "Unknown"
        
        citation = f"[{i}] {first_author} et al. ({year}). {title[:80]}... "
        citation += f"[PubMed: https://pubmed.ncbi.nlm.nih.gov/{pmid}/]"
        
        citations.append(citation)
    
    return "\n\n".join(citations)

def create_references_section(papers):
    """Create a full references section in APA style"""
    references = ["# References\n"]
    
    for paper in papers:
        references.append(format_apa(paper))
    
    return "\n\n".join(references)

# Example usage
if __name__ == "__main__":
    # Test with sample paper
    sample_paper = {
        'pmid': '27102172',
        'title': 'Effects of Resistance Training Frequency on Muscle Hypertrophy',
        'authors': ['Schoenfeld BJ', 'Ogborn D', 'Krieger JW'],
        'journal': 'Sports Medicine',
        'publication_date': '2016-10-01'
    }
    
    print("APA Style:")
    print(format_apa(sample_paper))
    print("\n" + "="*60 + "\n")
    
    print("MLA Style:")
    print(format_mla(sample_paper))
    print("\n" + "="*60 + "\n")
    
    print("Inline Citation:")
    print(format_inline(sample_paper))
    print("\n" + "="*60 + "\n")
    
    print("For Chatbot Response:")
    print(format_for_response([sample_paper]))