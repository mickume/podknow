"""Abstract interface for podcast discovery services."""

from abc import ABC, abstractmethod
from typing import List
from ..models.podcast import PodcastResult


class PodcastDiscoveryInterface(ABC):
    """Abstract interface for podcast discovery services."""
    
    @abstractmethod
    async def search_podcasts(self, query: str, limit: int = 10) -> List[PodcastResult]:
        """
        Search for podcasts using the provided query.
        
        Args:
            query: Search terms for podcast discovery
            limit: Maximum number of results to return
            
        Returns:
            List of podcast search results
            
        Raises:
            DiscoveryError: When search fails or service is unavailable
        """
        pass
    
    @abstractmethod
    async def get_podcast_details(self, podcast_id: str) -> PodcastResult:
        """
        Get detailed information about a specific podcast.
        
        Args:
            podcast_id: Unique identifier for the podcast
            
        Returns:
            Detailed podcast information
            
        Raises:
            DiscoveryError: When podcast details cannot be retrieved
        """
        pass
    
    @property
    @abstractmethod
    def service_name(self) -> str:
        """Return the name of the discovery service."""
        pass
    
    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the discovery service is currently available."""
        pass