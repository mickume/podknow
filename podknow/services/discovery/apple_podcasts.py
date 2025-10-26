"""Apple Podcasts API integration for podcast discovery."""

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


class ApplePodcastsClient(PodcastDiscoveryInterface):
    """Client for Apple Podcasts API integration."""
    
    BASE_URL = "https://itunes.apple.com"
    SEARCH_ENDPOINT = "/search"
    LOOKUP_ENDPOINT = "/lookup"
    
    def __init__(self, timeout: int = 30, max_retries: int = 3):
        """
        Initialize Apple Podcasts client.
        
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
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
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
        return "Apple Podcasts"
    
    @property
    def is_available(self) -> bool:
        """Check if the discovery service is currently available."""
        # Apple Podcasts API doesn't require authentication, so it's always available
        return True
    
    async def search_podcasts(self, query: str, limit: int = 10) -> List[PodcastResult]:
        """
        Search for podcasts using Apple Podcasts API.
        
        Args:
            query: Search terms for podcast discovery
            limit: Maximum number of results to return (max 200)
            
        Returns:
            List of podcast search results
            
        Raises:
            DiscoveryError: When search fails or service is unavailable
        """
        if not query.strip():
            raise DiscoveryError("Search query cannot be empty")
        
        # Apple Podcasts API limits results to 200
        limit = min(limit, 200)
        
        params = {
            "term": query.strip(),
            "media": "podcast",
            "entity": "podcast",
            "limit": limit,
            "country": "US",  # Default to US store
            "explicit": "Yes"  # Include explicit content
        }
        
        try:
            response_data = await self._make_request(self.SEARCH_ENDPOINT, params)
            results = response_data.get("results", [])
            
            podcast_results = []
            for item in results:
                try:
                    podcast_result = self._parse_podcast_item(item)
                    if podcast_result:
                        podcast_results.append(podcast_result)
                except (ValidationError, KeyError) as e:
                    logger.warning(f"Failed to parse podcast item: {e}")
                    continue
            
            logger.info(f"Found {len(podcast_results)} podcasts for query: {query}")
            return podcast_results
            
        except Exception as e:
            logger.error(f"Apple Podcasts search failed for query '{query}': {e}")
            raise DiscoveryError(f"Apple Podcasts search failed: {str(e)}") from e
    
    async def get_podcast_details(self, podcast_id: str) -> PodcastResult:
        """
        Get detailed information about a specific podcast.
        
        Args:
            podcast_id: Apple Podcasts collection ID
            
        Returns:
            Detailed podcast information
            
        Raises:
            DiscoveryError: When podcast details cannot be retrieved
        """
        if not podcast_id.strip():
            raise DiscoveryError("Podcast ID cannot be empty")
        
        params = {
            "id": podcast_id.strip(),
            "entity": "podcast",
            "country": "US"
        }
        
        try:
            response_data = await self._make_request(self.LOOKUP_ENDPOINT, params)
            results = response_data.get("results", [])
            
            if not results:
                raise DiscoveryError(f"Podcast not found with ID: {podcast_id}")
            
            podcast_result = self._parse_podcast_item(results[0])
            if not podcast_result:
                raise DiscoveryError(f"Failed to parse podcast data for ID: {podcast_id}")
            
            logger.info(f"Retrieved podcast details for ID: {podcast_id}")
            return podcast_result
            
        except DiscoveryError:
            raise
        except Exception as e:
            logger.error(f"Apple Podcasts lookup failed for ID '{podcast_id}': {e}")
            raise DiscoveryError(f"Apple Podcasts lookup failed: {str(e)}") from e
    
    async def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make HTTP request to Apple Podcasts API with retry logic.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            
        Returns:
            Parsed JSON response
            
        Raises:
            DiscoveryError: When request fails after all retries
        """
        if not self._client:
            raise DiscoveryError("Client not initialized. Use async context manager.")
        
        url = f"{self.BASE_URL}{endpoint}"
        
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Making request to {url} (attempt {attempt + 1})")
                response = await self._client.get(url, params=params)
                response.raise_for_status()
                
                data = response.json()
                if not isinstance(data, dict):
                    raise DiscoveryError("Invalid response format from Apple Podcasts API")
                
                return data
                
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
    
    def _parse_podcast_item(self, item: Dict[str, Any]) -> Optional[PodcastResult]:
        """
        Parse Apple Podcasts API response item into PodcastResult.
        
        Args:
            item: Raw podcast data from API
            
        Returns:
            Parsed podcast result or None if parsing fails
        """
        try:
            # Extract required fields
            title = item.get("collectionName", "").strip()
            author = item.get("artistName", "").strip()
            description = item.get("description", "").strip()
            rss_url = item.get("feedUrl", "").strip()
            
            # Validate required fields
            if not all([title, author, rss_url]):
                logger.warning(f"Missing required fields in podcast item: {item.get('collectionId')}")
                return None
            
            # Extract optional fields
            artwork_url = item.get("artworkUrl600") or item.get("artworkUrl100")
            category = item.get("primaryGenreName", "Unknown")
            
            return PodcastResult(
                title=title,
                author=author,
                description=description,
                rss_url=rss_url,
                artwork_url=artwork_url,
                category=category
            )
            
        except (KeyError, ValueError, ValidationError) as e:
            logger.warning(f"Failed to parse podcast item: {e}")
            return None