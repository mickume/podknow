"""
Episode-related data models.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Episode:
    """Represents a podcast episode."""
    
    id: str
    title: str
    description: str
    audio_url: str
    publication_date: datetime
    duration: str
    
    def __post_init__(self):
        """Validate required fields."""
        if not self.id:
            raise ValueError("Episode ID is required")
        if not self.title:
            raise ValueError("Episode title is required")
        if not self.audio_url:
            raise ValueError("Audio URL is required")


@dataclass
class EpisodeMetadata:
    """Represents comprehensive episode metadata for output."""
    
    podcast_title: str
    episode_title: str
    episode_number: Optional[int]
    publication_date: datetime
    duration: str
    description: str
    audio_url: str
    file_size: Optional[int] = None
    
    def __post_init__(self):
        """Validate required fields."""
        if not self.podcast_title:
            raise ValueError("Podcast title is required")
        if not self.episode_title:
            raise ValueError("Episode title is required")
        if not self.audio_url:
            raise ValueError("Audio URL is required")