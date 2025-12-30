"""
Video Transcriber for Deep Analysis

Downloads video audio and transcribes using OpenAI Whisper.
This is the "slow path" fallback when metadata extraction doesn't provide
enough content to analyze fitness claims.

Requires: yt-dlp, ffmpeg, openai-whisper
"""

import os
import tempfile
import subprocess
from typing import Optional, Dict, Any
from dataclasses import dataclass
from pathlib import Path

from .url_parser import URLParser, PlatformType, ParsedURL


@dataclass
class TranscriptionResult:
    """Result of video transcription"""
    success: bool
    transcript: str = ""
    language: str = ""
    duration: float = 0.0
    error_message: Optional[str] = None
    
    # Processing info
    download_time: float = 0.0
    transcription_time: float = 0.0
    total_time: float = 0.0


class VideoTranscriber:
    """
    Download and transcribe video audio using Whisper.
    
    This is computationally expensive and should only be used when:
    1. Metadata extraction didn't provide enough content
    2. User explicitly requests "deep analysis"
    """
    
    # Supported audio formats for Whisper
    AUDIO_FORMAT = 'mp3'
    
    # Maximum video duration (5 minutes) to prevent long processing times
    MAX_DURATION_SECONDS = 300
    
    # Whisper model size (tiny is fastest, but less accurate)
    # Options: tiny, base, small, medium, large
    WHISPER_MODEL = 'base'  # Good balance of speed and accuracy
    
    def __init__(self, model_size: str = None):
        """
        Initialize the transcriber.
        
        Args:
            model_size: Whisper model size (tiny/base/small/medium/large)
        """
        self.model_size = model_size or self.WHISPER_MODEL
        self._whisper_model = None
    
    def _get_whisper_model(self):
        """Lazy load Whisper model"""
        if self._whisper_model is None:
            try:
                import whisper
                print(f"Loading Whisper model: {self.model_size}...")
                self._whisper_model = whisper.load_model(self.model_size)
                print("Whisper model loaded successfully")
            except ImportError:
                raise ImportError(
                    "Whisper not installed. Run: pip install openai-whisper\n"
                    "Also requires ffmpeg: brew install ffmpeg (Mac) or apt install ffmpeg (Linux)"
                )
        return self._whisper_model
    
    def transcribe(self, url: str, force: bool = False) -> TranscriptionResult:
        """
        Download video and transcribe audio.
        
        Args:
            url: Video URL
            force: If True, transcribe even if video is long
            
        Returns:
            TranscriptionResult with transcript text
        """
        import time
        total_start = time.time()
        
        # Parse URL
        parsed = URLParser.parse(url)
        if not parsed.is_valid:
            return TranscriptionResult(
                success=False,
                error_message=parsed.error_message
            )
        
        # Create temp directory for downloads
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                # Step 1: Download audio
                download_start = time.time()
                audio_path, duration = self._download_audio(parsed.original_url, temp_dir)
                download_time = time.time() - download_start
                
                if not audio_path:
                    return TranscriptionResult(
                        success=False,
                        error_message="Failed to download audio from video"
                    )
                
                # Check duration
                if duration and duration > self.MAX_DURATION_SECONDS and not force:
                    return TranscriptionResult(
                        success=False,
                        error_message=f"Video is too long ({duration:.0f}s). Max allowed: {self.MAX_DURATION_SECONDS}s. Use force=True to override.",
                        duration=duration
                    )
                
                # Step 2: Transcribe audio
                transcribe_start = time.time()
                transcript, language = self._transcribe_audio(audio_path)
                transcribe_time = time.time() - transcribe_start
                
                total_time = time.time() - total_start
                
                return TranscriptionResult(
                    success=True,
                    transcript=transcript,
                    language=language,
                    duration=duration or 0.0,
                    download_time=download_time,
                    transcription_time=transcribe_time,
                    total_time=total_time
                )
                
            except Exception as e:
                return TranscriptionResult(
                    success=False,
                    error_message=str(e),
                    total_time=time.time() - total_start
                )
    
    def _download_audio(self, url: str, output_dir: str) -> tuple:
        """
        Download audio from video URL.
        
        Returns:
            (audio_file_path, duration_seconds) or (None, None) on failure
        """
        output_template = os.path.join(output_dir, 'audio.%(ext)s')
        
        cmd = [
            'yt-dlp',
            '--extract-audio',
            '--audio-format', self.AUDIO_FORMAT,
            '--audio-quality', '0',  # Best quality
            '--output', output_template,
            '--no-playlist',
            '--quiet',
            '--no-warnings',
            url
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120  # 2 minute timeout for download
            )
            
            if result.returncode != 0:
                print(f"yt-dlp error: {result.stderr}")
                return None, None
            
            # Find the downloaded file
            audio_path = os.path.join(output_dir, f'audio.{self.AUDIO_FORMAT}')
            if not os.path.exists(audio_path):
                # Try to find any audio file
                for ext in ['mp3', 'm4a', 'wav', 'opus', 'webm']:
                    candidate = os.path.join(output_dir, f'audio.{ext}')
                    if os.path.exists(candidate):
                        audio_path = candidate
                        break
            
            if not os.path.exists(audio_path):
                return None, None
            
            # Get duration using ffprobe
            duration = self._get_audio_duration(audio_path)
            
            return audio_path, duration
            
        except subprocess.TimeoutExpired:
            print("Download timed out")
            return None, None
        except FileNotFoundError:
            print("yt-dlp not found. Install with: pip install yt-dlp")
            return None, None
    
    def _get_audio_duration(self, audio_path: str) -> Optional[float]:
        """Get audio duration using ffprobe"""
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                audio_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return float(result.stdout.strip())
        except:
            pass
        
        return None
    
    def _transcribe_audio(self, audio_path: str) -> tuple:
        """
        Transcribe audio using Whisper.
        
        Returns:
            (transcript_text, detected_language)
        """
        model = self._get_whisper_model()
        
        # Transcribe
        result = model.transcribe(
            audio_path,
            language=None,  # Auto-detect language
            task='transcribe',
            verbose=False
        )
        
        transcript = result.get('text', '').strip()
        language = result.get('language', 'unknown')
        
        return transcript, language
    
    @staticmethod
    def check_dependencies() -> Dict[str, bool]:
        """Check if all required dependencies are available"""
        deps = {
            'yt-dlp': False,
            'ffmpeg': False,
            'ffprobe': False,
            'whisper': False
        }
        
        # Check yt-dlp
        try:
            result = subprocess.run(['yt-dlp', '--version'], capture_output=True, timeout=5)
            deps['yt-dlp'] = result.returncode == 0
        except:
            pass
        
        # Check ffmpeg
        try:
            result = subprocess.run(['ffmpeg', '-version'], capture_output=True, timeout=5)
            deps['ffmpeg'] = result.returncode == 0
        except:
            pass
        
        # Check ffprobe
        try:
            result = subprocess.run(['ffprobe', '-version'], capture_output=True, timeout=5)
            deps['ffprobe'] = result.returncode == 0
        except:
            pass
        
        # Check whisper
        try:
            import whisper
            deps['whisper'] = True
        except ImportError:
            pass
        
        return deps


# Test function
if __name__ == "__main__":
    print("Video Transcriber - Dependency Check")
    print("=" * 50)
    
    deps = VideoTranscriber.check_dependencies()
    
    for dep, installed in deps.items():
        status = "✅" if installed else "❌"
        print(f"  {status} {dep}")
    
    all_installed = all(deps.values())
    
    if all_installed:
        print("\n✅ All dependencies installed!")
        print("\nTo test transcription, run:")
        print("  transcriber = VideoTranscriber()")
        print("  result = transcriber.transcribe('https://youtube.com/shorts/...')")
    else:
        print("\n⚠️ Missing dependencies. Install with:")
        if not deps['yt-dlp']:
            print("  pip install yt-dlp")
        if not deps['ffmpeg'] or not deps['ffprobe']:
            print("  brew install ffmpeg  # Mac")
            print("  # or: apt install ffmpeg  # Linux")
        if not deps['whisper']:
            print("  pip install openai-whisper")
