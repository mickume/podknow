"""
Transcription service for audio download and transcription using MLX-Whisper.
"""

import os
import tempfile
import requests
from pathlib import Path
from typing import Optional
import mimetypes
from urllib.parse import urlparse
from datetime import datetime
import yaml

from ..models.transcription import TranscriptionResult, TranscriptionSegment
from ..models.episode import EpisodeMetadata
from ..exceptions import (
    TranscriptionError, 
    AudioProcessingError, 
    LanguageDetectionError,
    FileOperationError,
    NetworkError
)


class TranscriptionService:
    """Service for audio download and transcription using MLX-Whisper."""
    
    def __init__(self, temp_dir: Optional[str] = None):
        """Initialize transcription service with optional temp directory."""
        self.temp_dir = temp_dir or tempfile.gettempdir()
        self.supported_formats = {'.mp3', '.wav', '.m4a', '.aac', '.ogg', '.flac'}
        
    def download_audio(self, url: str) -> str:
        """
        Download audio file and return local file path.
        
        Args:
            url: URL of the audio file to download
            
        Returns:
            str: Path to the downloaded audio file
            
        Raises:
            NetworkError: If download fails
            AudioProcessingError: If file format is not supported
            FileOperationError: If file operations fail
        """
        try:
            # Parse URL to get filename
            parsed_url = urlparse(url)
            filename = os.path.basename(parsed_url.path)
            
            # If no filename in URL, generate one
            if not filename or '.' not in filename:
                filename = f"audio_{hash(url) % 10000}.mp3"
            
            # Create temporary file path
            temp_file_path = os.path.join(self.temp_dir, f"podknow_{filename}")
            
            # Download with progress tracking
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            # Validate content type
            content_type = response.headers.get('content-type', '')
            if not self._is_audio_content(content_type, filename):
                raise AudioProcessingError(
                    f"Unsupported audio format. Content-Type: {content_type}, File: {filename}"
                )
            
            # Write file with progress tracking
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0
            
            with open(temp_file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        # Simple progress indication (could be enhanced with callback)
                        if total_size > 0:
                            progress = (downloaded_size / total_size) * 100
                            if downloaded_size % (1024 * 1024) == 0:  # Log every MB
                                print(f"Download progress: {progress:.1f}%")
            
            # Validate downloaded file
            if not os.path.exists(temp_file_path) or os.path.getsize(temp_file_path) == 0:
                raise FileOperationError("Downloaded file is empty or does not exist")
            
            return temp_file_path
            
        except requests.RequestException as e:
            raise NetworkError(f"Failed to download audio from {url}: {str(e)}")
        except OSError as e:
            raise FileOperationError(f"File operation failed: {str(e)}")
    
    def _is_audio_content(self, content_type: str, filename: str) -> bool:
        """
        Validate if content is audio based on content-type and file extension.
        
        Args:
            content_type: HTTP content-type header
            filename: Name of the file
            
        Returns:
            bool: True if content appears to be audio
        """
        # Check content type
        if content_type and content_type.startswith('audio/'):
            return True
        
        # Check file extension
        file_ext = Path(filename).suffix.lower()
        if file_ext in self.supported_formats:
            return True
        
        # Check MIME type by extension
        guessed_type, _ = mimetypes.guess_type(filename)
        if guessed_type and guessed_type.startswith('audio/'):
            return True
        
        return False
    
    def detect_language(self, audio_path: str) -> str:
        """
        Detect the language of the audio file using MLX-Whisper.
        
        Args:
            audio_path: Path to the audio file
            
        Returns:
            str: Detected language code (e.g., 'en', 'es', 'fr')
            
        Raises:
            LanguageDetectionError: If language detection fails
            AudioProcessingError: If audio file cannot be processed
        """
        try:
            import mlx_whisper
            
            # Validate audio file exists
            if not os.path.exists(audio_path):
                raise AudioProcessingError(f"Audio file not found: {audio_path}")
            
            # Use MLX-Whisper to detect language
            # We'll use a small sample for language detection to be efficient
            result = mlx_whisper.transcribe(
                audio_path,
                language=None,  # Auto-detect
                task="transcribe",
                word_timestamps=False,
                condition_on_previous_text=False,
                initial_prompt=None,
                decode_options={
                    "language": None,  # Auto-detect
                    "task": "transcribe",
                    "fp16": True,  # Use half precision for speed
                }
            )
            
            detected_language = result.get("language", "unknown")
            
            # Validate English requirement
            if detected_language != "en":
                raise LanguageDetectionError(
                    f"Non-English content detected. Language: {detected_language}. "
                    "Only English podcasts are supported."
                )
            
            return detected_language
            
        except ImportError:
            raise LanguageDetectionError(
                "MLX-Whisper not available. Please install mlx-whisper package."
            )
        except Exception as e:
            if isinstance(e, (LanguageDetectionError, AudioProcessingError)):
                raise
            raise LanguageDetectionError(f"Language detection failed: {str(e)}")
    
    def transcribe_audio(self, audio_path: str) -> TranscriptionResult:
        """
        Transcribe audio file using MLX-Whisper with paragraph detection.
        
        Args:
            audio_path: Path to the audio file
            
        Returns:
            TranscriptionResult: Complete transcription with segments and metadata
            
        Raises:
            TranscriptionError: If transcription fails
            AudioProcessingError: If audio file cannot be processed
        """
        try:
            import mlx_whisper
            
            # Validate audio file exists
            if not os.path.exists(audio_path):
                raise AudioProcessingError(f"Audio file not found: {audio_path}")
            
            print(f"Starting transcription of {audio_path}...")
            
            # Perform transcription with word timestamps for paragraph detection
            result = mlx_whisper.transcribe(
                audio_path,
                language="en",  # We've already validated it's English
                task="transcribe",
                word_timestamps=True,  # Enable for paragraph detection
                condition_on_previous_text=True,
                decode_options={
                    "language": "en",
                    "task": "transcribe",
                    "fp16": True,  # Use half precision for Apple Silicon optimization
                    "word_timestamps": True,
                    "prepend_punctuations": "\"'([{-",
                    "append_punctuations": "\"'.,:!?)]}-",
                }
            )
            
            # Extract basic transcription info
            full_text = result.get("text", "").strip()
            language = result.get("language", "en")
            
            # Process segments for paragraph detection
            segments = []
            raw_segments = result.get("segments", [])
            
            for i, segment in enumerate(raw_segments):
                # Detect paragraph boundaries using various heuristics
                is_paragraph_start = self._detect_paragraph_boundary(
                    segment, 
                    raw_segments[i-1] if i > 0 else None,
                    i == 0
                )
                
                transcription_segment = TranscriptionSegment(
                    start_time=segment.get("start", 0.0),
                    end_time=segment.get("end", 0.0),
                    text=segment.get("text", "").strip(),
                    is_paragraph_start=is_paragraph_start
                )
                
                segments.append(transcription_segment)
            
            # Calculate overall confidence (average of segment confidences if available)
            confidence = self._calculate_confidence(raw_segments)
            
            print(f"Transcription completed. Language: {language}, Confidence: {confidence:.2f}")
            
            return TranscriptionResult(
                text=full_text,
                segments=segments,
                language=language,
                confidence=confidence
            )
            
        except ImportError:
            raise TranscriptionError(
                "MLX-Whisper not available. Please install mlx-whisper package."
            )
        except Exception as e:
            if isinstance(e, (TranscriptionError, AudioProcessingError)):
                raise
            raise TranscriptionError(f"Transcription failed: {str(e)}")
    
    def _detect_paragraph_boundary(self, current_segment: dict, previous_segment: dict, is_first: bool) -> bool:
        """
        Detect if a segment should start a new paragraph using various heuristics.
        
        Args:
            current_segment: Current segment data
            previous_segment: Previous segment data (None if first)
            is_first: Whether this is the first segment
            
        Returns:
            bool: True if this segment should start a new paragraph
        """
        if is_first:
            return True
        
        if not previous_segment:
            return True
        
        current_text = current_segment.get("text", "").strip()
        previous_text = previous_segment.get("text", "").strip()
        
        # Time gap heuristic - long pause suggests paragraph break
        time_gap = current_segment.get("start", 0) - previous_segment.get("end", 0)
        if time_gap > 2.0:  # 2+ second gap
            return True
        
        # Sentence ending heuristic - previous segment ends with sentence punctuation
        if previous_text.endswith(('.', '!', '?')):
            # Additional check for capitalization or common paragraph starters
            if (current_text and current_text[0].isupper()) or \
               any(current_text.lower().startswith(starter) for starter in 
                   ['so', 'now', 'but', 'and', 'well', 'okay', 'alright', 'um']):
                return True
        
        # Topic shift indicators
        topic_indicators = [
            'moving on', 'next up', 'speaking of', 'by the way', 'anyway',
            'let me tell you', 'here\'s the thing', 'you know what'
        ]
        if any(indicator in current_text.lower() for indicator in topic_indicators):
            return True
        
        return False
    
    def _calculate_confidence(self, segments: list) -> float:
        """
        Calculate overall transcription confidence from segments.
        
        Args:
            segments: List of transcription segments
            
        Returns:
            float: Overall confidence score (0.0 to 1.0)
        """
        if not segments:
            return 0.0
        
        # If segments have confidence scores, use them
        confidences = []
        for segment in segments:
            # MLX-Whisper may provide confidence in different ways
            if 'confidence' in segment:
                confidences.append(segment['confidence'])
            elif 'avg_logprob' in segment:
                # Convert log probability to confidence approximation
                logprob = segment['avg_logprob']
                confidence = max(0.0, min(1.0, (logprob + 1.0) / 1.0))
                confidences.append(confidence)
        
        if confidences:
            return sum(confidences) / len(confidences)
        
        # Fallback: estimate confidence based on segment characteristics
        total_segments = len(segments)
        valid_segments = sum(1 for s in segments if s.get('text', '').strip())
        
        return valid_segments / total_segments if total_segments > 0 else 0.0
    
    def generate_markdown_output(
        self, 
        transcription_result: TranscriptionResult, 
        episode_metadata: EpisodeMetadata,
        output_dir: Optional[str] = None
    ) -> str:
        """
        Generate markdown file with episode metadata and transcription.
        
        Args:
            transcription_result: The transcription result
            episode_metadata: Episode metadata for frontmatter
            output_dir: Output directory (defaults to ~/Documents/PodKnow)
            
        Returns:
            str: Path to the generated markdown file
            
        Raises:
            FileOperationError: If file generation fails
        """
        try:
            # Set default output directory
            if not output_dir:
                output_dir = os.path.expanduser("~/Documents/PodKnow")
            
            # Create output directory if it doesn't exist
            os.makedirs(output_dir, exist_ok=True)
            
            # Generate filename
            filename = self._generate_filename(episode_metadata)
            output_path = os.path.join(output_dir, filename)
            
            # Generate markdown content
            markdown_content = self._format_markdown_content(transcription_result, episode_metadata)
            
            # Write to file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            print(f"Transcription saved to: {output_path}")
            return output_path
            
        except OSError as e:
            raise FileOperationError(f"Failed to generate output file: {str(e)}")
    
    def _generate_filename(self, episode_metadata: EpisodeMetadata) -> str:
        """
        Generate filename based on episode metadata.
        
        Args:
            episode_metadata: Episode metadata
            
        Returns:
            str: Generated filename
        """
        # Clean podcast title for filename
        podcast_title = self._sanitize_filename(episode_metadata.podcast_title)
        
        # Use episode number if available, otherwise use date
        if episode_metadata.episode_number:
            episode_part = f"ep{episode_metadata.episode_number:03d}"
        else:
            date_str = episode_metadata.publication_date.strftime("%Y%m%d")
            episode_part = f"episode_{date_str}"
        
        return f"{podcast_title}_{episode_part}.md"
    
    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize string for use in filename.
        
        Args:
            filename: Original filename string
            
        Returns:
            str: Sanitized filename
        """
        # Replace invalid characters with underscores
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # Replace spaces with underscores and limit length
        filename = filename.replace(' ', '_').lower()
        
        # Remove multiple consecutive underscores
        while '__' in filename:
            filename = filename.replace('__', '_')
        
        # Limit length and remove trailing underscores
        return filename[:50].strip('_')
    
    def _format_markdown_content(
        self, 
        transcription_result: TranscriptionResult, 
        episode_metadata: EpisodeMetadata
    ) -> str:
        """
        Format the complete markdown content with frontmatter and transcription.
        
        Args:
            transcription_result: The transcription result
            episode_metadata: Episode metadata
            
        Returns:
            str: Formatted markdown content
        """
        # Create frontmatter
        frontmatter = {
            'podcast_title': episode_metadata.podcast_title,
            'episode_title': episode_metadata.episode_title,
            'episode_number': episode_metadata.episode_number,
            'publication_date': episode_metadata.publication_date.isoformat(),
            'duration': episode_metadata.duration,
            'transcribed_at': datetime.now().isoformat(),
            'language': transcription_result.language,
            'confidence': round(transcription_result.confidence, 3),
            'audio_url': episode_metadata.audio_url
        }
        
        # Remove None values
        frontmatter = {k: v for k, v in frontmatter.items() if v is not None}
        
        # Format transcription with paragraph breaks
        formatted_transcription = self._format_transcription_text(transcription_result)
        
        # Combine into markdown
        markdown_content = f"""---
{yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True)}---

# {episode_metadata.episode_title}

**Podcast:** {episode_metadata.podcast_title}  
**Published:** {episode_metadata.publication_date.strftime('%B %d, %Y')}  
**Duration:** {episode_metadata.duration}  
**Language:** {transcription_result.language.upper()}  
**Transcription Confidence:** {transcription_result.confidence:.1%}

## Episode Description

{episode_metadata.description or 'No description available.'}

## Transcription

{formatted_transcription}

---

*Transcribed using MLX-Whisper on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}*
"""
        
        return markdown_content
    
    def _format_transcription_text(self, transcription_result: TranscriptionResult) -> str:
        """
        Format transcription text with proper paragraph breaks.
        
        Args:
            transcription_result: The transcription result
            
        Returns:
            str: Formatted transcription text
        """
        if not transcription_result.segments:
            return transcription_result.text
        
        formatted_lines = []
        current_paragraph = []
        
        for segment in transcription_result.segments:
            if segment.is_paragraph_start and current_paragraph:
                # End current paragraph
                formatted_lines.append(' '.join(current_paragraph))
                current_paragraph = []
            
            # Add segment text to current paragraph
            if segment.text.strip():
                current_paragraph.append(segment.text.strip())
        
        # Add final paragraph
        if current_paragraph:
            formatted_lines.append(' '.join(current_paragraph))
        
        # Join paragraphs with double newlines
        return '\n\n'.join(formatted_lines)
    
    def cleanup_audio_file(self, audio_path: str) -> None:
        """
        Clean up temporary audio files.
        
        Args:
            audio_path: Path to the audio file to delete
            
        Raises:
            FileOperationError: If cleanup fails
        """
        try:
            if os.path.exists(audio_path):
                os.remove(audio_path)
                print(f"Cleaned up temporary file: {audio_path}")
        except OSError as e:
            raise FileOperationError(f"Failed to cleanup audio file {audio_path}: {str(e)}")