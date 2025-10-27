"""
Analysis-related data models.
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class SponsorSegment:
    """Represents a detected sponsor content segment."""
    
    start_text: str
    end_text: str
    confidence: float
    
    def __post_init__(self):
        """Validate sponsor segment data."""
        if not self.start_text.strip():
            raise ValueError("Start text cannot be empty")
        if not self.end_text.strip():
            raise ValueError("End text cannot be empty")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")


@dataclass
class AnalysisResult:
    """Represents the complete AI analysis result."""

    summary: str
    topics: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    sponsor_segments: List[SponsorSegment] = field(default_factory=list)

    def __post_init__(self):
        """Validate analysis result."""
        if not self.summary or not self.summary.strip():
            raise ValueError("Summary is required and cannot be empty")