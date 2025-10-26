"""
Podcast-related data models.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class PodcastResult:
    """Represents a podcast search result from discovery APIs."""
    
    title: str
    author: str
    rss_url: str
    platform: str
    description: str
    
    def __post_init__(self):
        """Validate required fields."""
        if not self.title:
            raise ValueError("Podcast title is required")
        if not self.author:
            raise ValueError("Podcast author is required")
        if not self.rss_url:
            raise ValueError("RSS URL is required")


@dataclass
class PodcastMetadata:
    """Represents comprehensive podcast metadata."""
    
    title: str
    author: str
    description: str
    rss_url: str
    episode_count: int
    last_updated: datetime
    
    def __post_init__(self):
        """Validate required fields."""
        if not self.title:
            raise ValueError("Podcast title is required")
        if not self.author:
            raise ValueError("Podcast author is required")
        if self.episode_count < 0:
            raise ValueError("Episode count must be non-negative")