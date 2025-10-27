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
from ..utils.progress import ProgressContext
import logging
from ..constants import (
    DEFAULT_LANGUAGE_DETECTION_SKIP_MINUTES,
    LANGUAGE_DETECTION_SAMPLE_DURATION,
    PARAGRAPH_TIME_GAP_THRESHOLD
)

logger = logging.getLogger(__name__)


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
            
            # Import rich for progress bar
            from rich.progress import Progress, BarColumn, TextColumn, DownloadColumn, TransferSpeedColumn
            
            with Progress(
                TextColumn("[bold blue]Downloading", justify="right"),
                BarColumn(bar_width=None),
                "[progress.percentage]{task.percentage:>3.1f}%",
                "•",
                DownloadColumn(),
                "•",
                TransferSpeedColumn(),
                refresh_per_second=10,
            ) as progress:
                
                task = progress.add_task("download", total=total_size)
                
                with open(temp_file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded_size += len(chunk)
                            progress.update(task, advance=len(chunk))
            
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
    
    def detect_language(self, audio_path: str, skip_minutes: float = DEFAULT_LANGUAGE_DETECTION_SKIP_MINUTES, sample_duration: float = LANGUAGE_DETECTION_SAMPLE_DURATION) -> str:
        """
        Detect the language of the audio file using MLX-Whisper.
        Skips the first few minutes to avoid ads/intros in different languages.
        
        Args:
            audio_path: Path to the audio file
            skip_minutes: Minutes to skip from the beginning (default: 2.0)
            sample_duration: Duration of sample to analyze in seconds (default: 30.0)
            
        Returns:
            str: Detected language code (e.g., 'en', 'es', 'fr')
            
        Raises:
            LanguageDetectionError: If language detection fails
            AudioProcessingError: If audio file cannot be processed
        """
        try:
            import mlx_whisper
            import sys
            import os
            import time
            from contextlib import redirect_stdout, redirect_stderr
            from io import StringIO
            
            # Validate audio file exists
            if not os.path.exists(audio_path):
                raise AudioProcessingError(f"Audio file not found: {audio_path}")
            
            # Create a temporary sample file from the middle of the audio
            sample_path = self._create_audio_sample(audio_path, skip_minutes, sample_duration)
            
            try:
                if ProgressContext.should_show_progress():
                    # Show progress for language detection
                    from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
                    import threading
                    
                    with Progress(
                        SpinnerColumn(),
                        TextColumn("[bold yellow]Detecting language"),
                        TextColumn("•"),
                        TimeElapsedColumn(),
                        refresh_per_second=4,
                    ) as progress:
                        
                        task = progress.add_task("language_detection", total=None)
                        
                        # Function to run language detection in background
                        def run_language_detection():
                            nonlocal result
                            # Suppress MLX-Whisper model download progress
                            with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                                # Use MLX-Whisper to detect language on the sample
                                result = mlx_whisper.transcribe(
                                    sample_path,
                                    language=None,  # Auto-detect
                                    task="transcribe",
                                    word_timestamps=False,
                                    condition_on_previous_text=False,
                                    initial_prompt=None,
                                    fp16=True  # Use half precision for speed
                                )
                        
                        # Start language detection in background thread
                        result = None
                        detection_thread = threading.Thread(target=run_language_detection)
                        detection_thread.start()
                        
                        # Update progress while detection is running
                        while detection_thread.is_alive():
                            progress.update(task, advance=0.1)
                            time.sleep(0.1)
                        
                        # Wait for detection to complete
                        detection_thread.join()
                        
                        # Mark as completed
                        progress.update(task, completed=True)
                else:
                    # Direct execution without progress bar
                    # Suppress MLX-Whisper model download progress
                    with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                        # Use MLX-Whisper to detect language on the sample
                        result = mlx_whisper.transcribe(
                            sample_path,
                            language=None,  # Auto-detect
                            task="transcribe",
                            word_timestamps=False,
                            condition_on_previous_text=False,
                            initial_prompt=None,
                            fp16=True  # Use half precision for speed
                        )
                
                detected_language = result.get("language", "unknown")
                
                # Show detection result
                logger.info(f"Language detected: {detected_language.upper()}")
                
                # Validate English requirement
                if detected_language != "en":
                    raise LanguageDetectionError(
                        f"Non-English content detected. Language: {detected_language}. "
                        "Only English podcasts are supported. "
                        f"(Analyzed sample from {skip_minutes:.1f} minutes into the audio)"
                    )
                
                return detected_language
                
            finally:
                # Clean up sample file
                if os.path.exists(sample_path):
                    os.remove(sample_path)
            
        except ImportError:
            raise LanguageDetectionError(
                "MLX-Whisper not available. Please install mlx-whisper package."
            )
        except Exception as e:
            if isinstance(e, (LanguageDetectionError, AudioProcessingError)):
                raise
            raise LanguageDetectionError(f"Language detection failed: {str(e)}")
    
    def _create_audio_sample(self, audio_path: str, skip_minutes: float, sample_duration: float) -> str:
        """
        Create a temporary audio sample from the middle of the file.
        
        Args:
            audio_path: Path to the original audio file
            skip_minutes: Minutes to skip from the beginning
            sample_duration: Duration of sample in seconds
            
        Returns:
            str: Path to the temporary sample file
            
        Raises:
            AudioProcessingError: If audio sampling fails
        """
        try:
            import librosa
            import soundfile as sf
            
            # Show progress for audio loading (can be slow for large files)
            from rich.progress import Progress, SpinnerColumn, TextColumn
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[bold cyan]Preparing audio sample"),
                refresh_per_second=4,
            ) as progress:
                
                task = progress.add_task("audio_sample", total=None)
                
                # Load audio file
                y, sr = librosa.load(audio_path, sr=None)
                
                progress.update(task, completed=True)
            
            # Calculate sample positions
            skip_samples = int(skip_minutes * 60 * sr)
            sample_length = int(sample_duration * sr)
            
            # Ensure we don't go beyond the audio length
            if skip_samples >= len(y):
                # If audio is shorter than skip time, use the last 30 seconds or entire audio
                if len(y) > sample_length:
                    start_sample = len(y) - sample_length
                    end_sample = len(y)
                else:
                    start_sample = 0
                    end_sample = len(y)
            else:
                start_sample = skip_samples
                end_sample = min(skip_samples + sample_length, len(y))
            
            # Extract sample
            sample = y[start_sample:end_sample]
            
            # Create temporary file for sample
            sample_filename = f"language_sample_{hash(audio_path) % 10000}.wav"
            sample_path = os.path.join(self.temp_dir, sample_filename)
            
            # Save sample
            sf.write(sample_path, sample, sr)
            
            return sample_path
            
        except ImportError:
            raise AudioProcessingError(
                "librosa and soundfile are required for audio sampling. "
                "Please install them: pip install librosa soundfile"
            )
        except Exception as e:
            raise AudioProcessingError(f"Failed to create audio sample: {str(e)}")
    
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
            import sys
            import os
            import time
            from contextlib import redirect_stdout, redirect_stderr
            from io import StringIO
            
            # Validate audio file exists
            if not os.path.exists(audio_path):
                raise AudioProcessingError(f"Audio file not found: {audio_path}")
            
            # Record start time for performance metrics
            start_time = time.time()

            if ProgressContext.should_show_progress():
                logger.info(f"Starting transcription of {audio_path}...")

            # Get audio duration for progress estimation
            audio_duration = self._get_audio_duration(audio_path)

            if ProgressContext.should_show_progress():
                # Create progress bar for transcription
                from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn, BarColumn
                import threading
                
                # Estimate transcription time (typically 10-20% of audio duration for MLX-Whisper)
                estimated_time = max(audio_duration * 0.15, 10.0) if audio_duration > 0 else None
                
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[bold blue]Transcribing audio"),
                    BarColumn(bar_width=None) if estimated_time else TextColumn(""),
                    TextColumn("[progress.percentage]{task.percentage:>3.0f}%") if estimated_time else TextColumn(""),
                    TextColumn("•"),
                    TimeElapsedColumn(),
                    refresh_per_second=4,
                ) as progress:
                    
                    # Add transcription task with estimated total if available
                    if estimated_time:
                        task = progress.add_task("transcription", total=100)
                        duration_text = f" ({audio_duration:.1f}s audio)" if audio_duration > 0 else ""
                        progress.update(task, description=f"[bold blue]Transcribing audio{duration_text}")
                    else:
                        task = progress.add_task("transcription", total=None)
                    
                    # Function to run transcription in background
                    def run_transcription():
                        nonlocal result
                        # Suppress MLX-Whisper model download progress
                        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                            # Perform transcription with word timestamps for paragraph detection
                            result = mlx_whisper.transcribe(
                                audio_path,
                                language="en",  # We've already validated it's English
                                task="transcribe",
                                word_timestamps=True,  # Enable for paragraph detection
                                condition_on_previous_text=True,
                                fp16=True,  # Use half precision for Apple Silicon optimization
                                prepend_punctuations="\"'([{-",
                                append_punctuations="\"'.,:!?)]}-"
                            )
                    
                    # Start transcription in background thread
                    result = None
                    transcription_thread = threading.Thread(target=run_transcription)
                    transcription_thread.start()
                    start_time = time.time()
                    
                    # Update progress while transcription is running
                    while transcription_thread.is_alive():
                        if estimated_time:
                            # Calculate progress based on elapsed time vs estimated time
                            elapsed = time.time() - start_time
                            progress_percent = min((elapsed / estimated_time) * 100, 95)  # Cap at 95% until done
                            progress.update(task, completed=progress_percent)
                        else:
                            # Just show activity
                            progress.update(task, advance=0.1)
                        time.sleep(0.25)
                    
                    # Wait for transcription to complete
                    transcription_thread.join()
                    
                    # Mark as completed
                    if estimated_time:
                        progress.update(task, completed=100)
                    else:
                        progress.update(task, completed=True)
            else:
                # Direct execution without progress bar
                # Suppress MLX-Whisper model download progress
                with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                    # Perform transcription with word timestamps for paragraph detection
                    result = mlx_whisper.transcribe(
                        audio_path,
                        language="en",  # We've already validated it's English
                        task="transcribe",
                        word_timestamps=True,  # Enable for paragraph detection
                        condition_on_previous_text=True,
                        fp16=True,  # Use half precision for Apple Silicon optimization
                        prepend_punctuations="\"'([{-",
                        append_punctuations="\"'.,:!?)]}-"
                    )
            
            # Extract basic transcription info
            full_text = result.get("text", "").strip()
            language = result.get("language", "en")
            
            # Process segments for paragraph detection
            segments = []
            raw_segments = result.get("segments", [])
            
            for i, segment in enumerate(raw_segments):
                # Extract and validate timing
                start_time = segment.get("start", 0.0)
                end_time = segment.get("end", 0.0)
                text = segment.get("text", "").strip()
                
                # Skip segments with invalid timing or empty text
                if not text or end_time <= start_time:
                    continue
                
                # Detect paragraph boundaries using various heuristics
                is_paragraph_start = self._detect_paragraph_boundary(
                    segment, 
                    raw_segments[i-1] if i > 0 else None,
                    i == 0
                )
                
                transcription_segment = TranscriptionSegment(
                    start_time=start_time,
                    end_time=end_time,
                    text=text,
                    is_paragraph_start=is_paragraph_start
                )
                
                segments.append(transcription_segment)
            
            # Calculate overall confidence (average of segment confidences if available)
            confidence = self._calculate_confidence(raw_segments)
            
            # Calculate actual transcription time
            actual_time = time.time() - start_time
            speed_ratio = audio_duration / actual_time if audio_duration > 0 and actual_time > 0 else 0
            
            logger.info("Transcription completed!")
            logger.info(f"   Language: {language}")
            logger.info(f"   Confidence: {confidence:.2f}")
            if audio_duration > 0 and actual_time > 0:
                logger.info(f"   Speed: {speed_ratio:.1f}x realtime ({actual_time:.1f}s for {audio_duration:.1f}s audio)")
            
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
        if time_gap > PARAGRAPH_TIME_GAP_THRESHOLD:  # 2+ second gap
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
    
    def _get_audio_duration(self, audio_path: str) -> float:
        """
        Get the duration of an audio file in seconds.
        
        Args:
            audio_path: Path to the audio file
            
        Returns:
            float: Duration in seconds, or 0.0 if unable to determine
        """
        try:
            import librosa
            
            # Load audio file to get duration
            duration = librosa.get_duration(path=audio_path)
            return duration
            
        except ImportError:
            # Fallback: estimate based on file size (very rough approximation)
            try:
                file_size = os.path.getsize(audio_path)
                # Rough estimate: 1MB ≈ 1 minute for typical podcast audio
                estimated_duration = file_size / (1024 * 1024) * 60
                return estimated_duration
            except:
                return 0.0
        except Exception:
            return 0.0
    
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
            
            logger.info(f"Transcription saved to: {output_path}")
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
                logger.debug(f"Cleaned up temporary file: {audio_path}")
        except OSError as e:
            raise FileOperationError(f"Failed to cleanup audio file {audio_path}: {str(e)}")