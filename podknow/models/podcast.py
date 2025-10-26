"""Podcast-related data models."""

from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, HttpUrl


class PodcastResult(BaseModel):
    """Represents a podcast search result from external directories."""
    
    title: str = Field(..., description="Podcast title")
    author: str = Field(..., description="Podcast author/creator")
    description: str = Field(..., description="Podcast description")
    rss_url: HttpUrl = Field(..., description="RSS feed URL")
    artwork_url: Optional[HttpUrl] = Field(None, description="Podcast artwork URL")
    category: str = Field(..., description="Primary podcast category")


class PodcastMetadata(BaseModel):
    """Extended metadata for a podcast."""
    
    title: str
    author: str
    description: str
    category: str
    language: str
    artwork_url: Optional[HttpUrl] = None
    website_url: Optional[HttpUrl] = None
    total_episodes: Optional[int] = None
    last_build_date: Optional[datetime] = None


class Subscription(BaseModel):
    """Represents a local podcast subscription."""
    
    id: str = Field(..., description="Unique subscription identifier")
    title: str = Field(..., description="Podcast title")
    rss_url: HttpUrl = Field(..., description="RSS feed URL")
    last_checked: datetime = Field(..., description="Last time feed was checked")
    episode_count: int = Field(0, description="Number of episodes processed")
    metadata: PodcastMetadata = Field(..., description="Extended podcast metadata")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            HttpUrl: str,
        }


class Episode(BaseModel):
    """Represents a podcast episode."""
    
    title: str = Field(..., description="Episode title")
    description: str = Field(..., description="Episode description")
    media_url: HttpUrl = Field(..., description="Media file URL")
    publication_date: datetime = Field(..., description="Episode publication date")
    duration: int = Field(..., description="Episode duration in seconds")
    language: str = Field("en", description="Episode language code")
    podcast_id: str = Field(..., description="Associated podcast subscription ID")
    episode_id: Optional[str] = Field(None, description="Unique episode identifier")
    file_size: Optional[int] = Field(None, description="Media file size in bytes")
    media_type: Optional[str] = Field(None, description="Media MIME type")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            HttpUrl: str,
        }