"""Spotify API integration for podcast discovery."""

import asyncio
import base64
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

import httpx
from pydantic import ValidationError

from ...exceptions import DiscoveryError, ConfigurationError
from ...interfaces.discovery import PodcastDiscoveryInterface
from ...models.podcast import PodcastResult


logger = logging.getLogger(__name__)


class SpotifyClient(PodcastDiscoveryInterface):
    """Client for Spotify Web API integration."""
    
    BASE_URL = "https://api.spotify.com/v1"
    AUTH_URL = "https://accounts.spotify.com/api/token"
    SEARCH_ENDPOINT = "/search"
    SHOW_ENDPOINT = "/shows"
    
    def __init__(
        self, 
        client_id: str, 
        client_secret: str, 
        timeout: int = 30, 
        max_retries: int = 3
    ):
        """
        Initialize Spotify client.
        
        Args:
            client_id: Spotify application client ID
            client_secret: Spotify application client secret
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            
        Raises:
            ConfigurationError: When credentials are missing
        """
        if not client_id or not client_secret:
            raise ConfigurationError("Spotify client ID and secret are required")
        
        self.client_id = client_id
        self.client_secret = client_secret
        self.timeout = timeout
        self.max_retries = max_retries
        
        self._client: Optional[httpx.AsyncClient] = None
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
        await self._ensure_valid_token()
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
        return bool(self.client_id and self.client_secret)
    
    async def search_podcasts(self, query: str, limit: int = 10) -> List[PodcastResult]:
        """
        Search for podcasts using Spotify Web API.
        
        Args:
            query: Search terms for podcast discovery
            limit: Maximum number of results to return (max 50)
            
        Returns:
            List of podcast search results
            
        Raises:
            DiscoveryError: When search fails or service is unavailable
        """
        if not query.strip():
            raise DiscoveryError("Search query cannot be empty")
        
        # Spotify API limits results to 50
        limit = min(limit, 50)
        
        params = {
            "q": query.strip(),
            "type": "show",
            "limit": limit,
            "market": "US"  # Default to US market
        }
        
        try:
            await self._ensure_valid_token()
            response_data = await self._make_authenticated_request(self.SEARCH_ENDPOINT, params)
            
            shows = response_data.get("shows", {}).get("items", [])
            
            podcast_results = []
            for show in shows:
                try:
                    podcast_result = await self._parse_show_item(show)
                    if podcast_result:
                        podcast_results.append(podcast_result)
                except (ValidationError, KeyError) as e:
                    logger.warning(f"Failed to parse show item: {e}")
                    continue
            
            logger.info(f"Found {len(podcast_results)} podcasts for query: {query}")
            return podcast_results
            
        except Exception as e:
            logger.error(f"Spotify search failed for query '{query}': {e}")
            raise DiscoveryError(f"Spotify search failed: {str(e)}") from e
    
    async def get_podcast_details(self, podcast_id: str) -> PodcastResult:
        """
        Get detailed information about a specific podcast.
        
        Args:
            podcast_id: Spotify show ID
            
        Returns:
            Detailed podcast information
            
        Raises:
            DiscoveryError: When podcast details cannot be retrieved
        """
        if not podcast_id.strip():
            raise DiscoveryError("Podcast ID cannot be empty")
        
        params = {
            "market": "US"
        }
        
        try:
            await self._ensure_valid_token()
            endpoint = f"{self.SHOW_ENDPOINT}/{podcast_id.strip()}"
            response_data = await self._make_authenticated_request(endpoint, params)
            
            podcast_result = await self._parse_show_item(response_data)
            if not podcast_result:
                raise DiscoveryError(f"Failed to parse podcast data for ID: {podcast_id}")
            
            logger.info(f"Retrieved podcast details for ID: {podcast_id}")
            return podcast_result
            
        except DiscoveryError:
            raise
        except Exception as e:
            logger.error(f"Spotify lookup failed for ID '{podcast_id}': {e}")
            raise DiscoveryError(f"Spotify lookup failed: {str(e)}") from e
    
    async def _ensure_valid_token(self) -> None:
        """Ensure we have a valid access token."""
        if (
            self._access_token is None 
            or self._token_expires_at is None 
            or datetime.now() >= self._token_expires_at
        ):
            await self._get_access_token()
    
    async def _get_access_token(self) -> None:
        """Get access token using client credentials flow."""
        if not self._client:
            raise DiscoveryError("Client not initialized. Use async context manager.")
        
        # Prepare credentials
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        headers = {
            "Authorization": f"Basic {encoded_credentials}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        data = {
            "grant_type": "client_credentials"
        }
        
        try:
            response = await self._client.post(self.AUTH_URL, headers=headers, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            self._access_token = token_data["access_token"]
            expires_in = token_data.get("expires_in", 3600)
            
            # Set expiration time with 5-minute buffer
            self._token_expires_at = datetime.now() + timedelta(seconds=expires_in - 300)
            
            logger.debug("Successfully obtained Spotify access token")
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get Spotify access token: {e.response.text}")
            raise DiscoveryError(f"Spotify authentication failed: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Spotify authentication error: {e}")
            raise DiscoveryError(f"Spotify authentication failed: {str(e)}")
    
    async def _make_authenticated_request(
        self, 
        endpoint: str, 
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make authenticated HTTP request to Spotify API with retry logic.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            
        Returns:
            Parsed JSON response
            
        Raises:
            DiscoveryError: When request fails after all retries
        """
        if not self._client or not self._access_token:
            raise DiscoveryError("Client not initialized or not authenticated")
        
        url = f"{self.BASE_URL}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json"
        }
        
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Making request to {url} (attempt {attempt + 1})")
                response = await self._client.get(url, headers=headers, params=params)
                
                if response.status_code == 401:  # Token expired
                    logger.info("Access token expired, refreshing...")
                    await self._get_access_token()
                    headers["Authorization"] = f"Bearer {self._access_token}"
                    continue
                
                response.raise_for_status()
                
                data = response.json()
                if not isinstance(data, dict):
                    raise DiscoveryError("Invalid response format from Spotify API")
                
                return data
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:  # Rate limited
                    retry_after = int(e.response.headers.get("Retry-After", 1))
                    logger.warning(f"Rate limited, waiting {retry_after}s before retry")
                    await asyncio.sleep(retry_after)
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
    
    async def _parse_show_item(self, show: Dict[str, Any]) -> Optional[PodcastResult]:
        """
        Parse Spotify show data into PodcastResult.
        
        Args:
            show: Raw show data from Spotify API
            
        Returns:
            Parsed podcast result or None if parsing fails
        """
        try:
            # Extract required fields
            title = show.get("name", "").strip()
            author = show.get("publisher", "").strip()
            description = show.get("description", "").strip()
            
            # Spotify doesn't provide RSS URLs directly, we need to construct or find them
            # For now, we'll use the external_urls as a fallback
            external_urls = show.get("external_urls", {})
            spotify_url = external_urls.get("spotify", "")
            
            # Try to get RSS feed URL from show details if available
            # This is a limitation - Spotify doesn't expose RSS feeds directly
            # In a real implementation, you might need to use a service to convert
            # Spotify show URLs to RSS feeds or maintain a mapping
            rss_url = self._get_rss_url_from_spotify_show(show)
            
            # Validate required fields
            if not all([title, author, rss_url]):
                logger.warning(f"Missing required fields in show item: {show.get('id')}")
                return None
            
            # Extract optional fields
            images = show.get("images", [])
            artwork_url = images[0]["url"] if images else None
            
            # Get primary category from genres
            genres = show.get("genres", [])
            category = genres[0] if genres else "Unknown"
            
            return PodcastResult(
                title=title,
                author=author,
                description=description,
                rss_url=rss_url,
                artwork_url=artwork_url,
                category=category
            )
            
        except (KeyError, ValueError, ValidationError) as e:
            logger.warning(f"Failed to parse show item: {e}")
            return None
    
    def _get_rss_url_from_spotify_show(self, show: Dict[str, Any]) -> str:
        """
        Attempt to get RSS URL from Spotify show data.
        
        This is a placeholder implementation. In a real-world scenario,
        you would need to:
        1. Use a service that maps Spotify show IDs to RSS feeds
        2. Maintain your own mapping database
        3. Use web scraping to find RSS feeds from show pages
        4. Use third-party services that provide this mapping
        
        Args:
            show: Spotify show data
            
        Returns:
            RSS URL or empty string if not available
        """
        # For demonstration purposes, we'll return a placeholder
        # In a real implementation, this would need to be resolved
        show_id = show.get("id", "")
        external_urls = show.get("external_urls", {})
        
        # This is a placeholder - you would implement actual RSS URL resolution here
        # For now, we'll use the Spotify URL as a fallback (which won't work for RSS)
        # but allows the code to function for demonstration
        spotify_url = external_urls.get("spotify", "")
        
        # In a real implementation, you might:
        # 1. Query a database mapping Spotify IDs to RSS URLs
        # 2. Use a third-party service to resolve RSS feeds
        # 3. Return empty string if no RSS feed is available
        
        if spotify_url:
            # This is a placeholder - replace with actual RSS URL resolution
            logger.warning(f"Using Spotify URL as placeholder for RSS feed: {spotify_url}")
            return spotify_url
        
        return ""