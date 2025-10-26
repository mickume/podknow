"""
Transcription-related data models.
"""

from dataclasses import dataclass
from typing import List


@dataclass
class TranscriptionSegment:
    """Represents a segment of transcribed audio."""
    
    start_time: float
    end_time: float
    text: str
    is_paragraph_start: bool = False
    
    def __post_init__(self):
        """Validate segment data."""
        if self.start_time < 0:
            raise ValueError("Start time must be non-negative")
        if self.end_time <= self.start_time:
            raise ValueError("End time must be greater than start time")
        if not self.text.strip():
            raise ValueError("Segment text cannot be empty")


@dataclass
class TranscriptionResult:
    """Represents the complete transcription result."""
    
    text: str
    segments: List[TranscriptionSegment]
    language: str
    confidence: float
    
    def __post_init__(self):
        """Validate transcription result."""
        if not self.text.strip():
            raise ValueError("Transcription text cannot be empty")
        if not self.language:
            raise ValueError("Language is required")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")