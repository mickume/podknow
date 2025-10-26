"""
Analysis-related data models.
"""

from dataclasses import dataclass
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
    topics: List[str]
    keywords: List[str]
    sponsor_segments: List[SponsorSegment]
    
    def __post_init__(self):
        """Validate analysis result."""
        if not self.summary.strip():
            raise ValueError("Summary cannot be empty")
        if not self.topics:
            raise ValueError("At least one topic is required")
        if not self.keywords:
            raise ValueError("At least one keyword is required")