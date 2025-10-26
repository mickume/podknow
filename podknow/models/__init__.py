"""
Data models for PodKnow application.

This module contains all the dataclasses and type definitions used throughout
the application for representing podcasts, episodes, transcriptions, and analysis results.
"""

from .podcast import PodcastResult, PodcastMetadata
from .episode import Episode, EpisodeMetadata
from .transcription import TranscriptionResult, TranscriptionSegment
from .analysis import AnalysisResult, SponsorSegment
from .output import OutputDocument

__all__ = [
    "PodcastResult",
    "PodcastMetadata", 
    "Episode",
    "EpisodeMetadata",
    "TranscriptionResult",
    "TranscriptionSegment",
    "AnalysisResult",
    "SponsorSegment",
    "OutputDocument",
]