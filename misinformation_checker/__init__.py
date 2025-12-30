# Misinformation Checker Module
# Fact-check fitness videos from social media against PubMed research

from .checker import MisinformationChecker, CheckerConfig, format_report_for_display
from .claim_analyzer import ClaimAnalyzer, FitnessClaim, FactCheckResult, FactCheckReport, Verdict
from .video_extractors.url_parser import URLParser, PlatformType, ParsedURL
from .video_extractors.metadata_extractor import MetadataExtractor, VideoMetadata
from .video_extractors.video_transcriber import VideoTranscriber, TranscriptionResult

__all__ = [
    'MisinformationChecker',
    'CheckerConfig', 
    'format_report_for_display',
    'ClaimAnalyzer',
    'FitnessClaim',
    'FactCheckResult',
    'FactCheckReport',
    'Verdict',
    'URLParser',
    'PlatformType',
    'ParsedURL',
    'MetadataExtractor',
    'VideoMetadata',
    'VideoTranscriber',
    'TranscriptionResult',
]
