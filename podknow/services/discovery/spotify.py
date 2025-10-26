"""Spotify public API integration for podcast discovery."""

import asyncio
import logging
from typing import List, Optional, Dict, Any
from urllib.parse import quote_plus

import httpx
from pydantic import ValidationError

from ...exceptions import DiscoveryError
from ...interfaces.discovery import PodcastDiscoveryInterface
from ...models.podcast import PodcastResult


logger = logging.getLogger(__name__)


class SpotifyPublicClient(PodcastDiscoveryInterface):
    """Client for Spotify public endpoints integration."""
    
    # Using Spotify's public search endpoints that don't require authentication
    BASE_URL = "https://open.spotify.com"
    SEARCH_ENDPOINT = "/search"
    
    def __init__(self, timeout: int = 30, max_retries: int = 3):
        """
        Initialize Spotify public client.
        
        Args:
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            headers={
                "User-Agent": "PodKnow/1.0 (Podcast Discovery Tool)"
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    @property
    def service_name(self) -> str:
        """Return the name of the discovery service."""
        return "Spotify"
    
    @property
    def is_available(self) -> bool:
        """Check if the discovery service is currently available."""
        return True  # Public endpoints don't require authentication
    
    async def search_podcasts(self, query: str, limit: int = 10) -> List[PodcastResult]:
        """
        Search for podcasts using Spotify public search.
        
        Note: This implementation uses public Spotify search which has limitations.
        For production use, consider using the authenticated API or alternative sources.
        
        Args:
            query: Search terms for podcast discovery
            limit: Maximum number of results to return
            
        Returns:
            List of podcast search results
            
        Raises:
            DiscoveryError: When search fails or service is unavailable
        """
        if not query.strip():
            raise DiscoveryError("Search query cannot be empty")
        
        # Limit results for public search
        limit = min(limit, 20)
        
        try:
            # Use Spotify's public search page
            search_url = f"{self.BASE_URL}/search/{quote_plus(query.strip())}/shows"
            
            response_data = await self._make_request(search_url)
            podcast_results = await self._parse_search_results(response_data, limit)
            
            logger.info(f"Found {len(podcast_results)} podcasts for query: {query}")
            return podcast_results
            
        except Exception as e:
            logger.error(f"Spotify search failed for query '{query}': {e}")
            raise DiscoveryError(f"Spotify search failed: {str(e)}") from e
    
    async def get_podcast_details(self, podcast_id: str) -> PodcastResult:
        """
        Get detailed information about a specific podcast.
        
        Args:
            podcast_id: Spotify show ID or URL
            
        Returns:
            Detailed podcast information
            
        Raises:
            DiscoveryError: When podcast details cannot be retrieved
        """
        if not podcast_id.strip():
            raise DiscoveryError("Podcast ID cannot be empty")
        
        try:
            # Construct Spotify show URL
            if podcast_id.startswith("http"):
                show_url = podcast_id
            else:
                show_url = f"{self.BASE_URL}/show/{podcast_id.strip()}"
            
            response_data = await self._make_request(show_url)
            podcast_result = await self._parse_show_page(response_data)
            
            if not podcast_result:
                raise DiscoveryError(f"Failed to parse podcast data for ID: {podcast_id}")
            
            logger.info(f"Retrieved podcast details for ID: {podcast_id}")
            return podcast_result
            
        except DiscoveryError:
            raise
        except Exception as e:
            logger.error(f"Spotify lookup failed for ID '{podcast_id}': {e}")
            raise DiscoveryError(f"Spotify lookup failed: {str(e)}") from e
    
    async def _make_request(self, url: str) -> str:
        """
        Make HTTP request to Spotify public pages with retry logic.
        
        Args:
            url: Full URL to request
            
        Returns:
            Response text content
            
        Raises:
            DiscoveryError: When request fails after all retries
        """
        if not self._client:
            raise DiscoveryError("Client not initialized. Use async context manager.")
        
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Making request to {url} (attempt {attempt + 1})")
                response = await self._client.get(url)
                response.raise_for_status()
                
                return response.text
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:  # Rate limited
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(f"Rate limited, waiting {wait_time}s before retry")
                    await asyncio.sleep(wait_time)
                    continue
                elif e.response.status_code >= 500:  # Server error
                    if attempt < self.max_retries - 1:
                        wait_time = 2 ** attempt
                        logger.warning(f"Server error, waiting {wait_time}s before retry")
                        await asyncio.sleep(wait_time)
                        continue
                
                raise DiscoveryError(f"HTTP {e.response.status_code}: {e.response.text}")
                
            except httpx.RequestError as e:
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(f"Request error, waiting {wait_time}s before retry: {e}")
                    await asyncio.sleep(wait_time)
                    continue
                
                raise DiscoveryError(f"Request failed: {str(e)}")
        
        raise DiscoveryError(f"Request failed after {self.max_retries} attempts")
    
    async def _parse_search_results(self, html_content: str, limit: int) -> List[PodcastResult]:
        """
        Parse Spotify search results from HTML content.
        
        Note: This is a simplified implementation. For production use,
        consider using a proper HTML parser like BeautifulSoup.
        
        Args:
            html_content: HTML content from Spotify search page
            limit: Maximum number of results to return
            
        Returns:
            List of parsed podcast results
        """
        podcast_results = []
        
        # This is a simplified implementation that would need proper HTML parsing
        # For demonstration purposes, we'll return a limited set of results
        # In a real implementation, you would:
        # 1. Use BeautifulSoup or similar to parse HTML
        # 2. Extract show information from the page structure
        # 3. Handle pagination and dynamic content loading
        
        logger.warning("Spotify public search has limited functionality. Consider using iTunes Search API as primary source.")
        
        # Return empty results for now - this would need proper implementation
        # with HTML parsing to extract show data from Spotify's search pages
        return podcast_results
    
    async def _parse_show_page(self, html_content: str) -> Optional[PodcastResult]:
        """
        Parse Spotify show page HTML content.
        
        Args:
            html_content: HTML content from Spotify show page
            
        Returns:
            Parsed podcast result or None if parsing fails
        """
        # This would need proper HTML parsing implementation
        # For now, return None to indicate limited functionality
        logger.warning("Spotify show page parsing not fully implemented. Use iTunes Search API for better results.")
        return None