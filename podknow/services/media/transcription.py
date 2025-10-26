"""MLX-Whisper transcription engine with language detection and progress tracking."""

import os
import time
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List
import logging

try:
    import mlx_whisper
except ImportError:
    mlx_whisper = None

from podknow.models.transcription import Transcription, TranscriptionSegment
from podknow.exceptions import TranscriptionError, ValidationError


class TranscriptionProgress:
    """Progress tracking for transcription operations."""
    
    def __init__(self, total_duration: Optional[float] = None):
        self.total_duration = total_duration
        self.current_position = 0.0
        self.start_time = time.time()
        self.stage = "initializing"
        self.message = ""
    
    @property
    def percentage(self) -> float:
        """Calculate transcription percentage."""
        if not self.total_duration or self.total_duration == 0:
            return 0.0
        return min((self.current_position / self.total_duration) * 100, 100.0)
    
    @property
    def elapsed_time(self) -> float:
        """Get elapsed processing time."""
        return time.time() - self.start_time
    
    @property
    def eta(self) -> Optional[float]:
        """Estimate time remaining in seconds."""
        if self.percentage == 0 or self.percentage >= 100:
            return None
        
        elapsed = self.elapsed_time
        rate = self.percentage / elapsed
        remaining_percentage = 100 - self.percentage
        return remaining_percentage / rate


class TranscriptionEngine:
    """MLX-Whisper transcription engine optimized for Apple Silicon."""
    
    # Supported models ordered by size/accuracy tradeoff
    AVAILABLE_MODELS = [
        "tiny",
        "base", 
        "small",
        "medium",
        "large",
        "large-v2",
        "large-v3"
    ]
    
    # Language codes that should be transcribed (English variants)
    ENGLISH_LANGUAGE_CODES = {
        "en", "en-US", "en-GB", "en-CA", "en-AU", "en-NZ", "en-IE", "en-ZA"
    }
    
    def __init__(
        self,
        model: str = "base",
        english_only: bool = True,
        language_detection_threshold: float = 0.7,
        chunk_length: int = 30,  # seconds
    ):
        """Initialize the transcription engine.
        
        Args:
            model: Whisper model to use
            english_only: Whether to only transcribe English content
            language_detection_threshold: Confidence threshold for language detection
            chunk_length: Length of audio chunks for processing
        """
        if mlx_whisper is None:
            raise TranscriptionError(
                "mlx-whisper is not installed. Please install it with: pip install mlx-whisper"
            )
        
        if model not in self.AVAILABLE_MODELS:
            raise ValidationError(f"Unsupported model: {model}. Available: {self.AVAILABLE_MODELS}")
        
        self.model = model
        self.english_only = english_only
        self.language_detection_threshold = language_detection_threshold
        self.chunk_length = chunk_length
        
        # Model will be loaded lazily
        self._loaded_model = None
        self._loaded_model_name = None
        
        self.logger = logging.getLogger(__name__)
    
    def transcribe_audio(
        self,
        file_path: str,
        progress_callback: Optional[Callable[[TranscriptionProgress], None]] = None,
    ) -> Transcription:
        """Transcribe audio file to text.
        
        Args:
            file_path: Path to the audio file
            progress_callback: Optional callback for progress updates
            
        Returns:
            Transcription object with results
            
        Raises:
            TranscriptionError: If transcription fails
            ValidationError: If file is invalid or unsupported
        """
        start_time = time.time()
        
        # Validate input file
        if not Path(file_path).exists():
            raise ValidationError(f"Audio file does not exist: {file_path}")
        
        # Initialize progress tracking
        progress = TranscriptionProgress()
        progress.stage = "loading_model"
        progress.message = f"Loading {self.model} model..."
        
        if progress_callback:
            progress_callback(progress)
        
        try:
            # Load model if needed
            self._ensure_model_loaded()
            
            # Detect language first if english_only is enabled
            if self.english_only:
                progress.stage = "detecting_language"
                progress.message = "Detecting audio language..."
                if progress_callback:
                    progress_callback(progress)
                
                detected_language = self.detect_language(file_path)
                if not self._is_english_language(detected_language):
                    raise TranscriptionError(
                        f"Audio language '{detected_language}' is not English. "
                        f"English-only mode is enabled."
                    )
            
            # Start transcription
            progress.stage = "transcribing"
            progress.message = "Transcribing audio..."
            if progress_callback:
                progress_callback(progress)
            
            # Perform transcription
            result = mlx_whisper.transcribe(
                file_path,
                path_or_hf_repo=self.model,
                verbose=False,
                word_timestamps=True,
            )
            
            # Process results
            progress.stage = "processing_results"
            progress.message = "Processing transcription results..."
            if progress_callback:
                progress_callback(progress)
            
            # Extract segments with timing information
            segments = []
            if "segments" in result:
                for segment_data in result["segments"]:
                    segment = TranscriptionSegment(
                        start=float(segment_data.get("start", 0.0)),
                        end=float(segment_data.get("end", 0.0)),
                        text=segment_data.get("text", "").strip(),
                        confidence=segment_data.get("avg_logprob", None),
                    )
                    segments.append(segment)
            
            # Create transcription object
            transcription = Transcription(
                text=result.get("text", "").strip(),
                segments=segments,
                language=result.get("language", "unknown"),
                confidence=self._calculate_overall_confidence(segments),
                processing_time=time.time() - start_time,
                model_used=self.model,
            )
            
            # Final progress update
            progress.stage = "complete"
            progress.message = "Transcription complete"
            progress.current_position = progress.total_duration or 100
            if progress_callback:
                progress_callback(progress)
            
            self.logger.info(
                f"Transcribed {file_path} in {transcription.processing_time:.2f}s "
                f"({transcription.word_count} words, {len(segments)} segments)"
            )
            
            return transcription
            
        except Exception as e:
            if isinstance(e, (TranscriptionError, ValidationError)):
                raise
            raise TranscriptionError(f"Transcription failed: {str(e)}")
    
    def detect_language(self, file_path: str) -> str:
        """Detect the language of an audio file.
        
        Args:
            file_path: Path to the audio file
            
        Returns:
            Detected language code
            
        Raises:
            TranscriptionError: If language detection fails
        """
        try:
            self._ensure_model_loaded()
            
            # Use MLX-Whisper's language detection
            result = mlx_whisper.transcribe(
                file_path,
                path_or_hf_repo=self.model,
                verbose=False,
                language=None,  # Auto-detect
                task="transcribe",
                # Only process first 30 seconds for language detection
                duration=30,
            )
            
            detected_language = result.get("language", "unknown")
            self.logger.debug(f"Detected language: {detected_language}")
            
            return detected_language
            
        except Exception as e:
            raise TranscriptionError(f"Language detection failed: {str(e)}")
    
    def _ensure_model_loaded(self) -> None:
        """Ensure the transcription model is loaded."""
        if self._loaded_model_name != self.model:
            self.logger.info(f"Loading MLX-Whisper model: {self.model}")
            # MLX-Whisper loads models automatically, so we just track the name
            self._loaded_model_name = self.model
    
    def _is_english_language(self, language_code: str) -> bool:
        """Check if a language code represents English.
        
        Args:
            language_code: Language code to check
            
        Returns:
            True if the language is English, False otherwise
        """
        return language_code.lower() in {code.lower() for code in self.ENGLISH_LANGUAGE_CODES}
    
    def _calculate_overall_confidence(self, segments: List[TranscriptionSegment]) -> float:
        """Calculate overall confidence score from segments.
        
        Args:
            segments: List of transcription segments
            
        Returns:
            Overall confidence score (0-1)
        """
        if not segments:
            return 0.0
        
        # Filter segments with confidence scores
        confident_segments = [s for s in segments if s.confidence is not None]
        
        if not confident_segments:
            return 0.5  # Default confidence when no scores available
        
        # Calculate weighted average by segment length
        total_weight = 0.0
        weighted_confidence = 0.0
        
        for segment in confident_segments:
            duration = segment.end - segment.start
            if duration > 0:
                weight = duration
                weighted_confidence += segment.confidence * weight
                total_weight += weight
        
        if total_weight == 0:
            return sum(s.confidence for s in confident_segments) / len(confident_segments)
        
        return weighted_confidence / total_weight
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model.
        
        Returns:
            Dictionary with model information
        """
        return {
            "model": self.model,
            "english_only": self.english_only,
            "language_detection_threshold": self.language_detection_threshold,
            "chunk_length": self.chunk_length,
            "available_models": self.AVAILABLE_MODELS,
        }
    
    def estimate_processing_time(self, audio_duration: float) -> float:
        """Estimate processing time for given audio duration.
        
        Args:
            audio_duration: Duration of audio in seconds
            
        Returns:
            Estimated processing time in seconds
        """
        # Rough estimates based on model size and Apple Silicon performance
        model_multipliers = {
            "tiny": 0.1,
            "base": 0.15,
            "small": 0.25,
            "medium": 0.4,
            "large": 0.6,
            "large-v2": 0.6,
            "large-v3": 0.7,
        }
        
        multiplier = model_multipliers.get(self.model, 0.3)
        return audio_duration * multiplier
    
    @classmethod
    def get_optimal_model_for_duration(cls, duration: float) -> str:
        """Get optimal model recommendation based on audio duration.
        
        Args:
            duration: Audio duration in seconds
            
        Returns:
            Recommended model name
        """
        if duration < 300:  # < 5 minutes
            return "base"
        elif duration < 1800:  # < 30 minutes
            return "small"
        elif duration < 3600:  # < 1 hour
            return "medium"
        else:
            return "large"