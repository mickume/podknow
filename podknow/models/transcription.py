"""Transcription-related data models."""

from typing import List, Optional
from pydantic import BaseModel, Field


class TranscriptionSegment(BaseModel):
    """Represents a segment of transcribed audio with timing information."""
    
    start: float = Field(..., description="Segment start time in seconds")
    end: float = Field(..., description="Segment end time in seconds")
    text: str = Field(..., description="Transcribed text for this segment")
    confidence: Optional[float] = Field(None, description="Confidence score (0-1)")


class Transcription(BaseModel):
    """Represents a complete transcription of an audio file."""
    
    text: str = Field(..., description="Complete transcribed text")
    segments: List[TranscriptionSegment] = Field(
        default_factory=list, 
        description="Individual transcription segments with timing"
    )
    language: str = Field(..., description="Detected language code")
    confidence: float = Field(..., description="Overall confidence score (0-1)")
    processing_time: float = Field(..., description="Time taken to process in seconds")
    model_used: Optional[str] = Field(None, description="Transcription model identifier")
    
    @property
    def duration(self) -> float:
        """Calculate total duration from segments."""
        if not self.segments:
            return 0.0
        return max(segment.end for segment in self.segments)
    
    @property
    def word_count(self) -> int:
        """Calculate approximate word count."""
        return len(self.text.split())
    
    def get_segment_at_time(self, timestamp: float) -> Optional[TranscriptionSegment]:
        """Get the transcription segment at a specific timestamp."""
        for segment in self.segments:
            if segment.start <= timestamp <= segment.end:
                return segment
        return None