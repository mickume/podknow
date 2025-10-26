"""
RSS feed parsing service for podcast episodes.
"""

import feedparser
import hashlib
from datetime import datetime
from typing import List, Optional
from urllib.parse import urlparse

from ..models.episode import Episode
from ..models.podcast import PodcastMetadata
from ..exceptions import PodKnowError


class RSSParsingError(PodKnowError):
    """Raised when RSS feed parsing fails."""
    pass


class RSSFeedParser:
    """Handles RSS feed parsing and episode extraction."""
    
    def __init__(self):
        """Initialize the RSS feed parser."""
        pass
    
    def parse_feed(self, rss_url: str) -> PodcastMetadata:
        """
        Parse RSS feed and extract podcast metadata.
        
        Args:
            rss_url: URL of the RSS feed to parse
            
        Returns:
            PodcastMetadata object with podcast information
            
        Raises:
            RSSParsingError: If feed parsing fails or feed is invalid
        """
        if not rss_url or not isinstance(rss_url, str):
            raise RSSParsingError("RSS URL must be a non-empty string")
        
        # Validate URL format
        parsed_url = urlparse(rss_url)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise RSSParsingError(f"Invalid RSS URL format: {rss_url}")
        
        try:
            # Parse the RSS feed
            feed = feedparser.parse(rss_url)
            
            # Check for parsing errors
            if hasattr(feed, 'bozo') and feed.bozo:
                if hasattr(feed, 'bozo_exception'):
                    raise RSSParsingError(f"Feed parsing error: {feed.bozo_exception}")
                else:
                    raise RSSParsingError("Feed parsing failed with unknown error")
            
            # Check if feed has required elements
            if not hasattr(feed, 'feed') or not feed.feed:
                raise RSSParsingError("Invalid RSS feed: missing feed element")
            
            # Extract podcast metadata
            feed_info = feed.feed
            
            title = getattr(feed_info, 'title', '').strip()
            if not title:
                raise RSSParsingError("RSS feed missing required title")
            
            # Try multiple fields for author/creator
            author = (
                getattr(feed_info, 'author', '') or
                getattr(feed_info, 'itunes_author', '') or
                getattr(feed_info, 'managingEditor', '') or
                'Unknown Author'
            ).strip()
            
            description = (
                getattr(feed_info, 'description', '') or
                getattr(feed_info, 'subtitle', '') or
                getattr(feed_info, 'itunes_summary', '') or
                ''
            ).strip()
            
            # Get episode count
            episode_count = len(feed.entries) if hasattr(feed, 'entries') else 0
            
            # Get last updated date
            last_updated = datetime.now()
            if hasattr(feed_info, 'updated_parsed') and feed_info.updated_parsed:
                try:
                    last_updated = datetime(*feed_info.updated_parsed[:6])
                except (TypeError, ValueError):
                    pass  # Use current time as fallback
            
            return PodcastMetadata(
                title=title,
                author=author,
                description=description,
                rss_url=rss_url,
                episode_count=episode_count,
                last_updated=last_updated
            )
            
        except feedparser.CharacterEncodingOverride:
            # This is usually not a fatal error, retry without encoding detection
            try:
                feed = feedparser.parse(rss_url)
                # Continue with normal processing...
                return self._extract_metadata_from_feed(feed, rss_url)
            except Exception as e:
                raise RSSParsingError(f"Failed to parse RSS feed after encoding retry: {str(e)}")
        except Exception as e:
            if isinstance(e, RSSParsingError):
                raise
            raise RSSParsingError(f"Failed to parse RSS feed: {str(e)}")
    
    def _extract_metadata_from_feed(self, feed, rss_url: str) -> PodcastMetadata:
        """Helper method to extract metadata from parsed feed."""
        if not hasattr(feed, 'feed') or not feed.feed:
            raise RSSParsingError("Invalid RSS feed: missing feed element")
        
        feed_info = feed.feed
        
        title = getattr(feed_info, 'title', '').strip()
        if not title:
            raise RSSParsingError("RSS feed missing required title")
        
        author = (
            getattr(feed_info, 'author', '') or
            getattr(feed_info, 'itunes_author', '') or
            getattr(feed_info, 'managingEditor', '') or
            'Unknown Author'
        ).strip()
        
        description = (
            getattr(feed_info, 'description', '') or
            getattr(feed_info, 'subtitle', '') or
            getattr(feed_info, 'itunes_summary', '') or
            ''
        ).strip()
        
        episode_count = len(feed.entries) if hasattr(feed, 'entries') else 0
        
        last_updated = datetime.now()
        if hasattr(feed_info, 'updated_parsed') and feed_info.updated_parsed:
            try:
                last_updated = datetime(*feed_info.updated_parsed[:6])
            except (TypeError, ValueError):
                pass
        
        return PodcastMetadata(
            title=title,
            author=author,
            description=description,
            rss_url=rss_url,
            episode_count=episode_count,
            last_updated=last_updated
        )
    
    def get_episodes(self, rss_url: str, count: Optional[int] = None) -> List[Episode]:
        """
        Extract episodes from RSS feed.
        
        Args:
            rss_url: URL of the RSS feed to parse
            count: Maximum number of episodes to return (None for all)
            
        Returns:
            List of Episode objects sorted by publication date (newest first)
            
        Raises:
            RSSParsingError: If feed parsing fails or episodes cannot be extracted
        """
        if not rss_url or not isinstance(rss_url, str):
            raise RSSParsingError("RSS URL must be a non-empty string")
        
        try:
            # Parse the RSS feed
            feed = feedparser.parse(rss_url)
            
            # Check for parsing errors
            if hasattr(feed, 'bozo') and feed.bozo:
                if hasattr(feed, 'bozo_exception'):
                    raise RSSParsingError(f"Feed parsing error: {feed.bozo_exception}")
            
            if not hasattr(feed, 'entries') or not feed.entries:
                return []  # Empty feed is valid, just return empty list
            
            episodes = []
            
            for entry in feed.entries:
                try:
                    episode = self._parse_episode_entry(entry, rss_url)
                    if episode:
                        episodes.append(episode)
                except Exception as e:
                    # Log the error but continue processing other episodes
                    print(f"Warning: Failed to parse episode '{getattr(entry, 'title', 'Unknown')}': {e}")
                    continue
            
            # Sort episodes by publication date (newest first)
            episodes.sort(key=lambda ep: ep.publication_date, reverse=True)
            
            # Limit results if count is specified
            if count is not None and count > 0:
                episodes = episodes[:count]
            
            return episodes
            
        except Exception as e:
            if isinstance(e, RSSParsingError):
                raise
            raise RSSParsingError(f"Failed to extract episodes from RSS feed: {str(e)}")
    
    def _parse_episode_entry(self, entry, rss_url: str) -> Optional[Episode]:
        """
        Parse a single episode entry from RSS feed.
        
        Args:
            entry: feedparser entry object
            rss_url: RSS feed URL for context
            
        Returns:
            Episode object or None if entry cannot be parsed
        """
        # Extract title
        title = getattr(entry, 'title', '').strip()
        if not title:
            return None  # Skip episodes without titles
        
        # Extract description
        description = (
            getattr(entry, 'description', '') or
            getattr(entry, 'summary', '') or
            getattr(entry, 'itunes_summary', '') or
            ''
        ).strip()
        
        # Extract audio URL from enclosures
        audio_url = self._extract_audio_url(entry)
        if not audio_url:
            return None  # Skip episodes without audio
        
        # Extract publication date
        publication_date = self._extract_publication_date(entry)
        
        # Extract duration
        duration = self._extract_duration(entry)
        
        # Generate unique episode ID
        episode_id = self._generate_episode_id(title, audio_url, rss_url)
        
        return Episode(
            id=episode_id,
            title=title,
            description=description,
            audio_url=audio_url,
            publication_date=publication_date,
            duration=duration
        )
    
    def _extract_audio_url(self, entry) -> Optional[str]:
        """Extract audio URL from episode entry."""
        # Check enclosures first
        if hasattr(entry, 'enclosures') and entry.enclosures:
            for enclosure in entry.enclosures:
                if hasattr(enclosure, 'type') and enclosure.type:
                    # Look for audio MIME types
                    if enclosure.type.startswith('audio/'):
                        return getattr(enclosure, 'href', None) or getattr(enclosure, 'url', None)
        
        # Check links as fallback
        if hasattr(entry, 'links') and entry.links:
            for link in entry.links:
                if hasattr(link, 'type') and link.type and link.type.startswith('audio/'):
                    return getattr(link, 'href', None)
        
        # Check for direct audio link in entry
        audio_url = getattr(entry, 'link', None)
        if audio_url and any(ext in audio_url.lower() for ext in ['.mp3', '.m4a', '.wav', '.ogg']):
            return audio_url
        
        return None
    
    def _extract_publication_date(self, entry) -> datetime:
        """Extract publication date from episode entry."""
        # Try published_parsed first
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            try:
                return datetime(*entry.published_parsed[:6])
            except (TypeError, ValueError):
                pass
        
        # Try updated_parsed as fallback
        if hasattr(entry, 'updated_parsed') and entry.updated_parsed:
            try:
                return datetime(*entry.updated_parsed[:6])
            except (TypeError, ValueError):
                pass
        
        # Use current time as last resort
        return datetime.now()
    
    def _extract_duration(self, entry) -> str:
        """Extract duration from episode entry."""
        # Try iTunes duration first
        duration = getattr(entry, 'itunes_duration', None)
        if duration:
            return str(duration).strip()
        
        # Try other duration fields
        for field in ['duration', 'length']:
            if hasattr(entry, field):
                value = getattr(entry, field)
                if value:
                    return str(value).strip()
        
        return "Unknown"
    
    def _generate_episode_id(self, title: str, audio_url: str, rss_url: str) -> str:
        """Generate a unique episode ID based on title, audio URL, and RSS URL."""
        # Create a hash from title + audio_url + rss_url for uniqueness
        content = f"{title}|{audio_url}|{rss_url}"
        hash_object = hashlib.md5(content.encode('utf-8'))
        return hash_object.hexdigest()[:12]  # Use first 12 characters for readability