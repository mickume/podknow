"""
Episode management service for listing and formatting podcast episodes.
"""

from typing import List, Optional
from datetime import datetime, timedelta

from ..models.episode import Episode
from ..models.podcast import PodcastMetadata
from .rss import RSSFeedParser, RSSParsingError
from ..exceptions import PodKnowError


class EpisodeManagementError(PodKnowError):
    """Raised when episode management operations fail."""
    pass


class EpisodeListingService:
    """Handles episode listing, filtering, and formatting operations."""
    
    def __init__(self):
        """Initialize the episode listing service."""
        self.rss_parser = RSSFeedParser()
    
    def list_episodes(
        self, 
        rss_url: str, 
        count: Optional[int] = 10,
        sort_by_date: bool = True
    ) -> List[Episode]:
        """
        List episodes from RSS feed with filtering and sorting.
        
        Args:
            rss_url: URL of the RSS feed to parse
            count: Maximum number of episodes to return (None for all)
            sort_by_date: Whether to sort episodes by publication date (newest first)
            
        Returns:
            List of Episode objects with unique identifiers assigned
            
        Raises:
            EpisodeManagementError: If episode listing fails
        """
        if count is not None and count <= 0:
            raise EpisodeManagementError("Episode count must be positive")
        
        try:
            # Get episodes from RSS feed
            episodes = self.rss_parser.get_episodes(rss_url, count)
            
            # Sort by publication date if requested (default behavior)
            if sort_by_date:
                episodes.sort(key=lambda ep: ep.publication_date, reverse=True)
            
            return episodes
            
        except RSSParsingError as e:
            raise EpisodeManagementError(f"Failed to list episodes: {str(e)}")
        except Exception as e:
            raise EpisodeManagementError(f"Unexpected error listing episodes: {str(e)}")
    
    def get_podcast_info(self, rss_url: str) -> PodcastMetadata:
        """
        Get podcast metadata from RSS feed.
        
        Args:
            rss_url: URL of the RSS feed to parse
            
        Returns:
            PodcastMetadata object with podcast information
            
        Raises:
            EpisodeManagementError: If podcast info retrieval fails
        """
        try:
            return self.rss_parser.parse_feed(rss_url)
        except RSSParsingError as e:
            raise EpisodeManagementError(f"Failed to get podcast info: {str(e)}")
        except Exception as e:
            raise EpisodeManagementError(f"Unexpected error getting podcast info: {str(e)}")
    
    def find_episode_by_id(self, rss_url: str, episode_id: str) -> Optional[Episode]:
        """
        Find a specific episode by its ID.
        
        Args:
            rss_url: URL of the RSS feed to search
            episode_id: Unique identifier of the episode to find
            
        Returns:
            Episode object if found, None otherwise
            
        Raises:
            EpisodeManagementError: If episode search fails
        """
        try:
            # Get all episodes (no count limit for search)
            episodes = self.rss_parser.get_episodes(rss_url, count=None)
            
            # Find episode with matching ID
            for episode in episodes:
                if episode.id == episode_id:
                    return episode
            
            return None
            
        except RSSParsingError as e:
            raise EpisodeManagementError(f"Failed to find episode: {str(e)}")
        except Exception as e:
            raise EpisodeManagementError(f"Unexpected error finding episode: {str(e)}")
    
    def format_episode_list(self, episodes: List[Episode], show_descriptions: bool = False) -> str:
        """
        Format episode list for display.
        
        Args:
            episodes: List of episodes to format
            show_descriptions: Whether to include episode descriptions
            
        Returns:
            Formatted string representation of episodes
        """
        if not episodes:
            return "No episodes found."
        
        lines = []
        lines.append(f"Found {len(episodes)} episode(s):\n")
        
        for i, episode in enumerate(episodes, 1):
            # Format publication date
            date_str = episode.publication_date.strftime("%Y-%m-%d")
            
            # Create episode line
            episode_line = f"{i:2d}. [{episode.id}] {episode.title}"
            lines.append(episode_line)
            
            # Add metadata line
            metadata_line = f"    Date: {date_str} | Duration: {episode.duration}"
            lines.append(metadata_line)
            
            # Add description if requested
            if show_descriptions and episode.description:
                # Truncate long descriptions
                desc = episode.description[:200] + "..." if len(episode.description) > 200 else episode.description
                desc_line = f"    Description: {desc}"
                lines.append(desc_line)
            
            lines.append("")  # Empty line between episodes
        
        return "\n".join(lines)
    
    def format_podcast_info(self, podcast: PodcastMetadata) -> str:
        """
        Format podcast metadata for display.
        
        Args:
            podcast: PodcastMetadata object to format
            
        Returns:
            Formatted string representation of podcast info
        """
        lines = []
        lines.append(f"Podcast: {podcast.title}")
        lines.append(f"Author: {podcast.author}")
        lines.append(f"Episodes: {podcast.episode_count}")
        lines.append(f"Last Updated: {podcast.last_updated.strftime('%Y-%m-%d %H:%M')}")
        lines.append(f"RSS URL: {podcast.rss_url}")
        
        if podcast.description:
            # Truncate long descriptions
            desc = podcast.description[:300] + "..." if len(podcast.description) > 300 else podcast.description
            lines.append(f"Description: {desc}")
        
        return "\n".join(lines)
    
    def get_recent_episodes(
        self, 
        rss_url: str, 
        days: int = 30, 
        count: Optional[int] = None
    ) -> List[Episode]:
        """
        Get episodes published within the last N days.
        
        Args:
            rss_url: URL of the RSS feed to parse
            days: Number of days to look back
            count: Maximum number of episodes to return
            
        Returns:
            List of recent Episode objects
            
        Raises:
            EpisodeManagementError: If recent episodes retrieval fails
        """
        if days <= 0:
            raise EpisodeManagementError("Days must be positive")
        
        try:
            # Get all episodes
            all_episodes = self.rss_parser.get_episodes(rss_url, count=None)
            
            # Filter by date
            cutoff_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            cutoff_date = cutoff_date - timedelta(days=days)
            
            recent_episodes = [
                ep for ep in all_episodes 
                if ep.publication_date >= cutoff_date
            ]
            
            # Sort by date (newest first)
            recent_episodes.sort(key=lambda ep: ep.publication_date, reverse=True)
            
            # Apply count limit if specified
            if count is not None and count > 0:
                recent_episodes = recent_episodes[:count]
            
            return recent_episodes
            
        except RSSParsingError as e:
            raise EpisodeManagementError(f"Failed to get recent episodes: {str(e)}")
        except Exception as e:
            raise EpisodeManagementError(f"Unexpected error getting recent episodes: {str(e)}")