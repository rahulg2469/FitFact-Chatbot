"""
Metadata Extractor for Video Platforms

Extracts video metadata (title, description, captions, hashtags) without
downloading the actual video. This is the "fast path" for the fact-checker.

Uses yt-dlp for consistent extraction across platforms.
"""

import re
import json
import subprocess
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from .url_parser import URLParser, PlatformType, ParsedURL


@dataclass
class VideoMetadata:
    """Extracted metadata from a video"""
    platform: PlatformType
    video_id: str
    url: str
    
    # Core content
    title: str = ""
    description: str = ""
    
    # Additional context
    hashtags: List[str] = field(default_factory=list)
    captions: str = ""  # Auto-generated or manual captions
    
    # Creator info
    creator: str = ""
    creator_id: str = ""
    
    # Engagement (useful for context)
    view_count: Optional[int] = None
    like_count: Optional[int] = None
    comment_count: Optional[int] = None
    
    # Timestamps
    upload_date: str = ""
    duration: Optional[int] = None  # seconds
    
    # Extraction status
    extraction_successful: bool = False
    error_message: Optional[str] = None
    
    # Combined text for analysis
    @property
    def combined_text(self) -> str:
        """Combine all text content for claim analysis"""
        parts = []
        
        if self.title:
            parts.append(f"Title: {self.title}")
        
        if self.description:
            parts.append(f"Description: {self.description}")
        
        if self.captions:
            parts.append(f"Captions/Transcript: {self.captions}")
        
        if self.hashtags:
            parts.append(f"Hashtags: {' '.join(self.hashtags)}")
        
        return "\n\n".join(parts)
    
    @property
    def has_sufficient_content(self) -> bool:
        """Check if we have enough text to analyze without transcription"""
        combined = self.title + " " + self.description + " " + self.captions
        
        # Need at least 50 characters of content
        if len(combined.strip()) < 50:
            return False
        
        # Check for fitness-related keywords
        fitness_keywords = [
            'workout', 'exercise', 'fitness', 'gym', 'muscle', 'protein',
            'cardio', 'weight', 'fat', 'diet', 'nutrition', 'supplement',
            'creatine', 'training', 'lift', 'squat', 'bench', 'deadlift',
            'bulk', 'cut', 'lean', 'gains', 'reps', 'sets', 'hiit',
            'calories', 'macros', 'body', 'strength', 'health', 'fit'
        ]
        
        combined_lower = combined.lower()
        has_fitness_content = any(kw in combined_lower for kw in fitness_keywords)
        
        return has_fitness_content
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'platform': self.platform.value,
            'video_id': self.video_id,
            'url': self.url,
            'title': self.title,
            'description': self.description,
            'hashtags': self.hashtags,
            'captions': self.captions,
            'creator': self.creator,
            'creator_id': self.creator_id,
            'view_count': self.view_count,
            'like_count': self.like_count,
            'upload_date': self.upload_date,
            'duration': self.duration,
            'extraction_successful': self.extraction_successful,
            'error_message': self.error_message,
            'combined_text': self.combined_text,
            'has_sufficient_content': self.has_sufficient_content
        }


class MetadataExtractor:
    """
    Extract metadata from video URLs without downloading the video.
    
    Uses yt-dlp's JSON extraction feature for consistent results across platforms.
    """
    
    # yt-dlp options for metadata-only extraction
    YT_DLP_BASE_OPTS = [
        '--no-download',           # Don't download the video
        '--no-playlist',           # Single video only
        '--dump-json',             # Output as JSON
        '--no-warnings',           # Suppress warnings
        '--quiet',                 # Minimal output
        '--ignore-errors',         # Continue on errors
        '--no-check-certificates', # Skip SSL verification (some platforms have issues)
    ]
    
    @classmethod
    def extract(cls, url: str) -> VideoMetadata:
        """
        Extract metadata from a video URL.
        
        Args:
            url: The video URL
            
        Returns:
            VideoMetadata object with extracted information
        """
        # First, parse the URL
        parsed = URLParser.parse(url)
        
        if not parsed.is_valid:
            return VideoMetadata(
                platform=parsed.platform,
                video_id=parsed.video_id or "",
                url=url,
                extraction_successful=False,
                error_message=parsed.error_message
            )
        
        # Try yt-dlp extraction
        try:
            metadata = cls._extract_with_ytdlp(parsed)
            return metadata
        except Exception as e:
            return VideoMetadata(
                platform=parsed.platform,
                video_id=parsed.video_id or "",
                url=url,
                extraction_successful=False,
                error_message=f"Extraction failed: {str(e)}"
            )
    
    @classmethod
    def _extract_with_ytdlp(cls, parsed: ParsedURL) -> VideoMetadata:
        """Use yt-dlp to extract metadata"""
        
        # Build command
        cmd = ['yt-dlp'] + cls.YT_DLP_BASE_OPTS + [parsed.original_url]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30  # 30 second timeout
            )
            
            if result.returncode != 0:
                # Try to parse error message
                error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                
                # Common errors
                if 'Private video' in error_msg:
                    error_msg = "This video is private"
                elif 'Video unavailable' in error_msg:
                    error_msg = "This video is unavailable"
                elif 'Sign in' in error_msg:
                    error_msg = "This video requires login to view"
                
                return VideoMetadata(
                    platform=parsed.platform,
                    video_id=parsed.video_id or "",
                    url=parsed.original_url,
                    extraction_successful=False,
                    error_message=error_msg[:200]  # Truncate long errors
                )
            
            # Parse JSON output
            data = json.loads(result.stdout)
            
            return cls._parse_ytdlp_json(data, parsed)
            
        except subprocess.TimeoutExpired:
            return VideoMetadata(
                platform=parsed.platform,
                video_id=parsed.video_id or "",
                url=parsed.original_url,
                extraction_successful=False,
                error_message="Extraction timed out. The video may be too long or the server is slow."
            )
        except json.JSONDecodeError:
            return VideoMetadata(
                platform=parsed.platform,
                video_id=parsed.video_id or "",
                url=parsed.original_url,
                extraction_successful=False,
                error_message="Failed to parse video metadata"
            )
        except FileNotFoundError:
            return VideoMetadata(
                platform=parsed.platform,
                video_id=parsed.video_id or "",
                url=parsed.original_url,
                extraction_successful=False,
                error_message="yt-dlp not installed. Run: pip install yt-dlp"
            )
    
    @classmethod
    def _parse_ytdlp_json(cls, data: Dict[str, Any], parsed: ParsedURL) -> VideoMetadata:
        """Parse yt-dlp JSON output into VideoMetadata"""
        
        # Extract basic info
        title = data.get('title', '') or ''
        description = data.get('description', '') or ''
        
        # Extract hashtags from description
        hashtags = cls._extract_hashtags(description)
        
        # Also check for hashtags in tags field
        if 'tags' in data and data['tags']:
            for tag in data['tags']:
                if tag and not tag.startswith('#'):
                    tag = f"#{tag}"
                if tag not in hashtags:
                    hashtags.append(tag)
        
        # Try to get captions/subtitles
        captions = cls._extract_captions(data)
        
        # Creator info
        creator = data.get('uploader', '') or data.get('channel', '') or ''
        creator_id = data.get('uploader_id', '') or data.get('channel_id', '') or ''
        
        # Engagement metrics
        view_count = data.get('view_count')
        like_count = data.get('like_count')
        comment_count = data.get('comment_count')
        
        # Timestamps
        upload_date = data.get('upload_date', '')
        if upload_date and len(upload_date) == 8:
            # Format: YYYYMMDD -> YYYY-MM-DD
            upload_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:]}"
        
        duration = data.get('duration')
        
        return VideoMetadata(
            platform=parsed.platform,
            video_id=parsed.video_id or data.get('id', ''),
            url=parsed.original_url,
            title=title,
            description=description,
            hashtags=hashtags,
            captions=captions,
            creator=creator,
            creator_id=creator_id,
            view_count=view_count,
            like_count=like_count,
            comment_count=comment_count,
            upload_date=upload_date,
            duration=duration,
            extraction_successful=True
        )
    
    @staticmethod
    def _extract_hashtags(text: str) -> List[str]:
        """Extract hashtags from text"""
        if not text:
            return []
        
        # Find all hashtags
        hashtags = re.findall(r'#[\w]+', text)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_hashtags = []
        for tag in hashtags:
            tag_lower = tag.lower()
            if tag_lower not in seen:
                seen.add(tag_lower)
                unique_hashtags.append(tag)
        
        return unique_hashtags
    
    @staticmethod
    def _extract_captions(data: Dict[str, Any]) -> str:
        """Try to extract captions/subtitles from yt-dlp data"""
        captions = ""
        
        # Check for automatic captions (YouTube)
        if 'automatic_captions' in data and data['automatic_captions']:
            auto_caps = data['automatic_captions']
            # Prefer English
            for lang in ['en', 'en-US', 'en-GB']:
                if lang in auto_caps:
                    # This gives us caption format info, not the actual text
                    # We'd need to download captions separately
                    break
        
        # Check for subtitles
        if 'subtitles' in data and data['subtitles']:
            subtitles = data['subtitles']
            for lang in ['en', 'en-US', 'en-GB']:
                if lang in subtitles:
                    break
        
        # For now, we rely on description for text content
        # Full caption extraction requires downloading subtitle files
        # which we'll handle in the transcriber for the slow path
        
        return captions


# Test function
if __name__ == "__main__":
    print("Metadata Extractor Test")
    print("=" * 60)
    
    # Test with a public YouTube video about fitness
    test_urls = [
        "https://www.youtube.com/watch?v=U9ENCvFf9yQ",  # Example fitness video
    ]
    
    for url in test_urls:
        print(f"\nTesting: {url}")
        print("-" * 40)
        
        metadata = MetadataExtractor.extract(url)
        
        if metadata.extraction_successful:
            print(f"✅ Extraction successful!")
            print(f"   Title: {metadata.title[:60]}...")
            print(f"   Creator: {metadata.creator}")
            print(f"   Duration: {metadata.duration}s")
            print(f"   Views: {metadata.view_count:,}" if metadata.view_count else "   Views: N/A")
            print(f"   Hashtags: {metadata.hashtags[:5]}")
            print(f"   Has sufficient content: {metadata.has_sufficient_content}")
            print(f"\n   Description preview:")
            print(f"   {metadata.description[:200]}...")
        else:
            print(f"❌ Extraction failed: {metadata.error_message}")
