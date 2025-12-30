"""
URL Parser for Video Platforms

Detects the platform (YouTube, TikTok, Instagram, X/Twitter) and extracts
the video ID from a given URL.
"""

import re
from enum import Enum
from typing import Optional, Tuple
from dataclasses import dataclass


class PlatformType(Enum):
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"
    TWITTER = "twitter"  # Also covers X
    UNKNOWN = "unknown"


@dataclass
class ParsedURL:
    """Result of parsing a video URL"""
    platform: PlatformType
    video_id: Optional[str]
    original_url: str
    clean_url: Optional[str]  # Normalized URL without tracking params
    is_valid: bool
    error_message: Optional[str] = None


class URLParser:
    """
    Parse social media video URLs to extract platform and video ID.
    
    Supported platforms:
    - YouTube (youtube.com, youtu.be, shorts)
    - TikTok (tiktok.com, vm.tiktok.com)
    - Instagram (instagram.com/reel/, /p/)
    - X/Twitter (twitter.com, x.com)
    """
    
    # YouTube patterns
    YOUTUBE_PATTERNS = [
        # Standard watch URL: youtube.com/watch?v=VIDEO_ID
        r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
        # Short URL: youtu.be/VIDEO_ID
        r'(?:https?://)?(?:www\.)?youtu\.be/([a-zA-Z0-9_-]{11})',
        # Shorts: youtube.com/shorts/VIDEO_ID
        r'(?:https?://)?(?:www\.)?youtube\.com/shorts/([a-zA-Z0-9_-]{11})',
        # Embed URL: youtube.com/embed/VIDEO_ID
        r'(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})',
        # Mobile: m.youtube.com/watch?v=VIDEO_ID
        r'(?:https?://)?m\.youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
    ]
    
    # TikTok patterns
    TIKTOK_PATTERNS = [
        # Standard: tiktok.com/@username/video/VIDEO_ID
        r'(?:https?://)?(?:www\.)?tiktok\.com/@[\w.-]+/video/(\d+)',
        # Short URL: vm.tiktok.com/CODE
        r'(?:https?://)?vm\.tiktok\.com/([\w]+)',
        # Mobile share: tiktok.com/t/CODE
        r'(?:https?://)?(?:www\.)?tiktok\.com/t/([\w]+)',
        # Without username: tiktok.com/video/VIDEO_ID (some regions)
        r'(?:https?://)?(?:www\.)?tiktok\.com/video/(\d+)',
    ]
    
    # Instagram patterns
    INSTAGRAM_PATTERNS = [
        # Reel: instagram.com/reel/CODE
        r'(?:https?://)?(?:www\.)?instagram\.com/reel/([\w-]+)',
        # Post (can be video): instagram.com/p/CODE
        r'(?:https?://)?(?:www\.)?instagram\.com/p/([\w-]+)',
        # Reels tab: instagram.com/reels/CODE
        r'(?:https?://)?(?:www\.)?instagram\.com/reels/([\w-]+)',
        # TV (IGTV): instagram.com/tv/CODE
        r'(?:https?://)?(?:www\.)?instagram\.com/tv/([\w-]+)',
    ]
    
    # Twitter/X patterns
    TWITTER_PATTERNS = [
        # Twitter: twitter.com/username/status/TWEET_ID
        r'(?:https?://)?(?:www\.)?twitter\.com/[\w]+/status/(\d+)',
        # X.com: x.com/username/status/TWEET_ID
        r'(?:https?://)?(?:www\.)?x\.com/[\w]+/status/(\d+)',
        # Mobile twitter
        r'(?:https?://)?mobile\.twitter\.com/[\w]+/status/(\d+)',
    ]
    
    @classmethod
    def parse(cls, url: str) -> ParsedURL:
        """
        Parse a URL and return platform info and video ID.
        
        Args:
            url: The video URL to parse
            
        Returns:
            ParsedURL object with platform, video_id, and validation info
        """
        if not url or not isinstance(url, str):
            return ParsedURL(
                platform=PlatformType.UNKNOWN,
                video_id=None,
                original_url=url or "",
                clean_url=None,
                is_valid=False,
                error_message="Empty or invalid URL"
            )
        
        url = url.strip()
        
        # Try each platform
        for platform, patterns, url_builder in [
            (PlatformType.YOUTUBE, cls.YOUTUBE_PATTERNS, cls._build_youtube_url),
            (PlatformType.TIKTOK, cls.TIKTOK_PATTERNS, cls._build_tiktok_url),
            (PlatformType.INSTAGRAM, cls.INSTAGRAM_PATTERNS, cls._build_instagram_url),
            (PlatformType.TWITTER, cls.TWITTER_PATTERNS, cls._build_twitter_url),
        ]:
            for pattern in patterns:
                match = re.search(pattern, url, re.IGNORECASE)
                if match:
                    video_id = match.group(1)
                    clean_url = url_builder(video_id)
                    return ParsedURL(
                        platform=platform,
                        video_id=video_id,
                        original_url=url,
                        clean_url=clean_url,
                        is_valid=True
                    )
        
        # Check if it looks like a URL but we couldn't parse it
        if re.match(r'https?://', url):
            return ParsedURL(
                platform=PlatformType.UNKNOWN,
                video_id=None,
                original_url=url,
                clean_url=None,
                is_valid=False,
                error_message="URL not recognized. Supported: YouTube, TikTok, Instagram, X/Twitter"
            )
        
        return ParsedURL(
            platform=PlatformType.UNKNOWN,
            video_id=None,
            original_url=url,
            clean_url=None,
            is_valid=False,
            error_message="Invalid URL format. Please paste a complete URL starting with http:// or https://"
        )
    
    @staticmethod
    def _build_youtube_url(video_id: str) -> str:
        return f"https://www.youtube.com/watch?v={video_id}"
    
    @staticmethod
    def _build_tiktok_url(video_id: str) -> str:
        # For short codes, we keep them as-is since we need to resolve them
        if video_id.isdigit():
            return f"https://www.tiktok.com/video/{video_id}"
        return f"https://vm.tiktok.com/{video_id}"
    
    @staticmethod
    def _build_instagram_url(video_id: str) -> str:
        return f"https://www.instagram.com/reel/{video_id}/"
    
    @staticmethod
    def _build_twitter_url(video_id: str) -> str:
        return f"https://x.com/i/status/{video_id}"
    
    @classmethod
    def detect_platform(cls, url: str) -> PlatformType:
        """Quick check to just get the platform without full parsing"""
        url_lower = url.lower()
        
        if 'youtube.com' in url_lower or 'youtu.be' in url_lower:
            return PlatformType.YOUTUBE
        elif 'tiktok.com' in url_lower:
            return PlatformType.TIKTOK
        elif 'instagram.com' in url_lower:
            return PlatformType.INSTAGRAM
        elif 'twitter.com' in url_lower or 'x.com' in url_lower:
            return PlatformType.TWITTER
        
        return PlatformType.UNKNOWN
    
    @classmethod
    def is_supported_url(cls, url: str) -> bool:
        """Quick check if URL is from a supported platform"""
        return cls.detect_platform(url) != PlatformType.UNKNOWN


# Quick test
if __name__ == "__main__":
    test_urls = [
        # YouTube
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://youtube.com/shorts/abc123def45",
        
        # TikTok
        "https://www.tiktok.com/@username/video/7234567890123456789",
        "https://vm.tiktok.com/ZMrKxYz/",
        
        # Instagram
        "https://www.instagram.com/reel/CxYz123AbCd/",
        "https://instagram.com/p/CxYz123AbCd",
        
        # Twitter/X
        "https://twitter.com/user/status/1234567890123456789",
        "https://x.com/user/status/1234567890123456789",
        
        # Invalid
        "https://facebook.com/video/123",
        "not a url",
        "",
    ]
    
    print("URL Parser Test Results:")
    print("=" * 60)
    
    for url in test_urls:
        result = URLParser.parse(url)
        status = "✅" if result.is_valid else "❌"
        print(f"\n{status} Input: {url[:50]}...")
        print(f"   Platform: {result.platform.value}")
        print(f"   Video ID: {result.video_id}")
        if result.clean_url:
            print(f"   Clean URL: {result.clean_url}")
        if result.error_message:
            print(f"   Error: {result.error_message}")
