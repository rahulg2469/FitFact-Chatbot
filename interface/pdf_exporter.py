from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_CENTER
from reportlab.lib.colors import HexColor
from datetime import datetime
import io
import re


class FitFactPDFExporter:
    """
    Export FitFact Q&A responses to professionally formatted PDF
    """
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Create custom paragraph styles for FitFact branding"""
        
        # Title style
        self.styles.add(ParagraphStyle(
            name='FitFactTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=HexColor('#667eea'),
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Subtitle style
        self.styles.add(ParagraphStyle(
            name='FitFactSubtitle',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=HexColor('#888888'),
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName='Helvetica'
        ))
        
        # Question style
        self.styles.add(ParagraphStyle(
            name='Question',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=HexColor('#2196F3'),
            spaceAfter=12,
            spaceBefore=12,
            fontName='Helvetica-Bold'
        ))
        
        # Answer style
        self.styles.add(ParagraphStyle(
            name='Answer',
            parent=self.styles['BodyText'],
            fontSize=11,
            textColor=HexColor('#333333'),
            spaceAfter=10,
            alignment=TA_JUSTIFY,
            leading=16,
            fontName='Helvetica'
        ))
        
        # Citation style
        self.styles.add(ParagraphStyle(
            name='Citation',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=HexColor('#1976D2'),
            spaceAfter=6,
            leftIndent=20,
            fontName='Helvetica'
        ))
        
        # References header
        self.styles.add(ParagraphStyle(
            name='ReferencesHeader',
            parent=self.styles['Heading2'],
            fontSize=12,
            textColor=HexColor('#9C27B0'),
            spaceAfter=10,
            spaceBefore=20,
            fontName='Helvetica-Bold'
        ))
        
        # Footer style
        self.styles.add(ParagraphStyle(
            name='Footer',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=HexColor('#AAAAAA'),
            alignment=TA_CENTER,
            fontName='Helvetica'
        ))
    
    def _extract_references(self, response_text: str) -> tuple:
        """
        Extract main content and references from response
        Returns: (main_content, references_list)
        """
        # Split on common reference section markers
        patterns = [
            r'\n\s*References?\s*:?\s*\n',
            r'\n\s*Citations?\s*:?\s*\n',
            r'\n\s*Sources?\s*:?\s*\n'
        ]
        
        for pattern in patterns:
            parts = re.split(pattern, response_text, flags=re.IGNORECASE)
            if len(parts) > 1:
                main_content = parts[0].strip()
                references = parts[1].strip()
                # Split references into individual citations
                ref_list = [ref.strip() for ref in references.split('\n') if ref.strip()]
                return main_content, ref_list
        
        # If no references section found, return all as main content
        return response_text.strip(), []
    
    def generate_pdf(self, question: str, response: str, metrics: dict = None) -> bytes:
        """
        Generate PDF from question and response
        
        Args:
            question: User's fitness question
            response: FitFact's evidence-based response
            metrics: Optional dict with cache_hit, response_time, etc.
        
        Returns:
            bytes: PDF file content
        """
        # Create PDF in memory
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        # Container for PDF elements
        story = []
        
        # Header
        story.append(Paragraph("FitFact", self.styles['FitFactTitle']))
        story.append(Paragraph(
            "Evidence-Based Fitness Advisor | Powered by PubMed Research",
            self.styles['FitFactSubtitle']
        ))
        story.append(Spacer(1, 0.2*inch))
        
        # Date and metadata
        date_str = datetime.now().strftime("%B %d, %Y at %I:%M %p")
        story.append(Paragraph(
            f"<i>Generated on {date_str}</i>",
            self.styles['FitFactSubtitle']
        ))
        story.append(Spacer(1, 0.3*inch))
        
        # Question section
        story.append(Paragraph("Your Question:", self.styles['Question']))
        story.append(Paragraph(question, self.styles['Answer']))
        story.append(Spacer(1, 0.2*inch))
        
        # Metrics (if provided)
        if metrics:
            metrics_text = []
            if metrics.get('cache_hit'):
                metrics_text.append("✓ Retrieved from cache")
            if metrics.get('response_time'):
                metrics_text.append(f"Response time: {metrics['response_time']:.2f}s")
            if metrics.get('papers_found'):
                metrics_text.append(f"Research papers consulted: {metrics['papers_found']}")
            
            if metrics_text:
                story.append(Paragraph(
                    f"<i>{' | '.join(metrics_text)}</i>",
                    self.styles['FitFactSubtitle']
                ))
                story.append(Spacer(1, 0.2*inch))
        
        # Response section
        story.append(Paragraph("Evidence-Based Answer:", self.styles['Question']))
        
        # Extract main content and references
        main_content, references = self._extract_references(response)
        
        # Add main content (split into paragraphs)
        paragraphs = main_content.split('\n\n')
        for para in paragraphs:
            if para.strip():
                # Clean up the paragraph text
                clean_para = para.strip().replace('\n', ' ')
                story.append(Paragraph(clean_para, self.styles['Answer']))
                story.append(Spacer(1, 0.1*inch))
        
        # Add references section if found
        if references:
            story.append(Spacer(1, 0.2*inch))
            story.append(Paragraph("References:", self.styles['ReferencesHeader']))
            
            for i, ref in enumerate(references, 1):
                # Clean reference text and add numbering if not present
                clean_ref = ref.strip()
                if not clean_ref[0].isdigit():
                    clean_ref = f"{i}. {clean_ref}"
                story.append(Paragraph(clean_ref, self.styles['Citation']))
        
        # Footer
        story.append(Spacer(1, 0.5*inch))
        story.append(Paragraph(
            "_______________________________________________",
            self.styles['Footer']
        ))
        story.append(Paragraph(
            "This response is based on peer-reviewed research from PubMed. "
            "Always consult healthcare professionals for personalized medical advice.",
            self.styles['Footer']
        ))
        story.append(Spacer(1, 0.1*inch))
        story.append(Paragraph(
            "FitFact | github.com/rahulg2469/FitFact-Chatbot",
            self.styles['Footer']
        ))
        
        # Build PDF
        doc.build(story)
        
        # Get PDF bytes
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return pdf_bytes
    
    def save_pdf(self, question: str, response: str, filepath: str, metrics: dict = None):
        """
        Generate and save PDF to file
        
        Args:
            question: User's fitness question
            response: FitFact's evidence-based response
            filepath: Output file path (e.g., 'output.pdf')
            metrics: Optional metrics dict
        """
        pdf_bytes = self.generate_pdf(question, response, metrics)
        
        with open(filepath, 'wb') as f:
            f.write(pdf_bytes)
        
        return filepath


# Test function
def test_pdf_exporter():
    """Test the PDF exporter with sample data"""
    
    exporter = FitFactPDFExporter()
    
    sample_question = "What are the benefits of creatine supplementation for strength training?"
    
    sample_response = """Creatine supplementation has been extensively studied and shows significant benefits for strength training. Research demonstrates that creatine monohydrate supplementation increases muscle strength and power output during resistance training (Kreider et al., 2017, PMID: 28615996).

The typical loading protocol involves consuming 20g/day for 5-7 days, followed by a maintenance dose of 3-5g/day. This approach has been shown to increase lean muscle mass by approximately 2.2 kg compared to placebo (Branch et al., 2003, PMID: 12945830).

Creatine works by increasing phosphocreatine stores in muscles, which helps regenerate ATP during high-intensity exercise. Studies spanning several decades have consistently shown creatine supplementation to be safe when consumed at recommended doses (Kreider & Stout, 2021, PMID: 34049503).

References:
Kreider RB, Kalman DS, Antonio J, et al. (2017). Creatine supplementation and resistance training: effects on body composition. PMID: 28615996
Branch JD (2003). Effects of creatine supplementation on muscle strength: a meta-analysis. PMID: 12945830
Kreider RB, Stout JR (2021). International Society of Sports Nutrition position stand: safety and efficacy of creatine supplementation. PMID: 34049503"""
    
    sample_metrics = {
        'cache_hit': False,
        'response_time': 3.45,
        'papers_found': 3,
        'citations': 3
    }
    
    # Generate PDF
    print("Testing PDF Export...")
    pdf_bytes = exporter.generate_pdf(sample_question, sample_response, sample_metrics)
    
    # Save to file
    output_path = "fitfact_sample_export.pdf"
    exporter.save_pdf(sample_question, sample_response, output_path, sample_metrics)
    
    print(f"PDF generated successfully!")
    print(f"Saved to: {output_path}")
    print(f"File size: {len(pdf_bytes) / 1024:.2f} KB")


if __name__ == "__main__":
    test_pdf_exporter()
