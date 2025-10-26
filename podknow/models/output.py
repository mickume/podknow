"""
Output document data models.
"""

from dataclasses import dataclass
from datetime import datetime
from .episode import EpisodeMetadata
from .analysis import AnalysisResult


@dataclass
class OutputDocument:
    """Represents the final output document structure."""
    
    metadata: EpisodeMetadata
    transcription: str
    analysis: AnalysisResult
    processing_timestamp: datetime
    
    def __post_init__(self):
        """Validate output document."""
        if not self.transcription.strip():
            raise ValueError("Transcription cannot be empty")
        if not isinstance(self.metadata, EpisodeMetadata):
            raise ValueError("Metadata must be EpisodeMetadata instance")
        if not isinstance(self.analysis, AnalysisResult):
            raise ValueError("Analysis must be AnalysisResult instance")