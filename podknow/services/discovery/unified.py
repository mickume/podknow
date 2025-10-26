"""Unified podcast discovery interface that aggregates multiple sources."""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
from urllib.parse import urlparse

from ...exceptions import DiscoveryError, ConfigurationError
from ...models.podcast import PodcastResult
from .apple_podcasts import ApplePodcastsClient
from .spotify import SpotifyClient


logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Container for search results with metadata."""
    results: List[PodcastResult]
    source: str
    query: str
    total_found: int
    search_time: float


class PodcastDiscovery:
    """Unified podcast discovery service that aggregates results from multiple sources."""
    
    def __init__(
        self,
        apple_podcasts_enabled: bool = True,
        spotify_enabled: bool = False,
        spotify_client_id: Optional[str] = None,
        spotify_client_secret: Optional[str] = None,
        timeout: int = 30,
        max_concurrent_searches: int = 3
    ):
        """
        Initialize unified podcast discovery service.
        
        Args:
            apple_podcasts_enabled: Enable Apple Podcasts search
            spotify_enabled: Enable Spotify search
            spotify_client_id: Spotify client ID (required if Spotify enabled)
            spotify_client_secret: Spotify client secret (required if Spotify enabled)
            timeout: Request timeout in seconds
            max_concurrent_searches: Maximum concurrent API calls
            
        Raises:
            ConfigurationError: When required credentials are missing
        """
        self.apple_podcasts_enabled = apple_podcasts_enabled
        self.spotify_enabled = spotify_enabled
        self.timeout = timeout
        self.max_concurrent_searches = max_concurrent_searches
        
        # Initialize clients
        self._apple_client: Optional[ApplePodcastsClient] = None
        self._spotify_client: Optional[SpotifyClient] = None
        
        if self.apple_podcasts_enabled:
            self._apple_client = ApplePodcastsClient(timeout=timeout)
        
        if self.spotify_enabled:
            if not spotify_client_id or not spotify_client_secret:
                raise ConfigurationError(
                    "Spotify client ID and secret are required when Spotify is enabled"
                )
            self._spotify_client = SpotifyClient(
                client_id=spotify_client_id,
                client_secret=spotify_client_secret,
                timeout=timeout
            )
    
    async def search_podcasts(
        self,
        query: str,
        limit: int = 10,
        sources: Optional[List[str]] = None,
        deduplicate: bool = True,
        rank_results: bool = True
    ) -> List[PodcastResult]:
        """
        Search for podcasts across multiple sources.
        
        Args:
            query: Search terms for podcast discovery
            limit: Maximum number of results to return per source
            sources: Specific sources to search (None for all enabled)
            deduplicate: Remove duplicate results based on RSS URL
            rank_results: Rank and sort results by relevance
            
        Returns:
            Aggregated and optionally deduplicated/ranked podcast results
            
        Raises:
            DiscoveryError: When all searches fail
        """
        if not query.strip():
            raise DiscoveryError("Search query cannot be empty")
        
        # Determine which sources to search
        search_sources = self._get_enabled_sources(sources)
        if not search_sources:
            raise DiscoveryError("No podcast discovery sources are enabled or available")
        
        logger.info(f"Searching for '{query}' across {len(search_sources)} sources")
        
        # Execute searches concurrently
        search_tasks = []
        semaphore = asyncio.Semaphore(self.max_concurrent_searches)
        
        for source in search_sources:
            task = self._search_single_source(semaphore, source, query, limit)
            search_tasks.append(task)
        
        # Wait for all searches to complete
        search_results = await asyncio.gather(*search_tasks, return_exceptions=True)
        
        # Process results
        all_results = []
        successful_searches = 0
        
        for i, result in enumerate(search_results):
            source = search_sources[i]
            
            if isinstance(result, Exception):
                logger.warning(f"Search failed for {source}: {result}")
                continue
            
            if isinstance(result, SearchResult):
                all_results.extend(result.results)
                successful_searches += 1
                logger.info(
                    f"{source} found {len(result.results)} results "
                    f"in {result.search_time:.2f}s"
                )
        
        if successful_searches == 0:
            raise DiscoveryError("All podcast discovery sources failed")
        
        # Post-process results
        if deduplicate:
            all_results = self._deduplicate_results(all_results)
        
        if rank_results:
            all_results = self._rank_results(all_results, query)
        
        # Apply final limit
        final_results = all_results[:limit * len(search_sources)]
        
        logger.info(
            f"Returning {len(final_results)} results from {successful_searches} sources"
        )
        return final_results
    
    async def get_podcast_details(
        self,
        podcast_id: str,
        source: str
    ) -> PodcastResult:
        """
        Get detailed information about a specific podcast from a specific source.
        
        Args:
            podcast_id: Podcast identifier for the specified source
            source: Source name ('apple_podcasts' or 'spotify')
            
        Returns:
            Detailed podcast information
            
        Raises:
            DiscoveryError: When podcast details cannot be retrieved
        """
        if source == "apple_podcasts" and self._apple_client:
            async with self._apple_client as client:
                return await client.get_podcast_details(podcast_id)
        elif source == "spotify" and self._spotify_client:
            async with self._spotify_client as client:
                return await client.get_podcast_details(podcast_id)
        else:
            raise DiscoveryError(f"Source '{source}' is not available or enabled")
    
    def get_available_sources(self) -> List[str]:
        """
        Get list of available discovery sources.
        
        Returns:
            List of available source names
        """
        sources = []
        
        if self.apple_podcasts_enabled and self._apple_client:
            sources.append("apple_podcasts")
        
        if self.spotify_enabled and self._spotify_client:
            sources.append("spotify")
        
        return sources
    
    async def _search_single_source(
        self,
        semaphore: asyncio.Semaphore,
        source: str,
        query: str,
        limit: int
    ) -> SearchResult:
        """
        Search a single podcast source with concurrency control.
        
        Args:
            semaphore: Concurrency control semaphore
            source: Source name to search
            query: Search query
            limit: Maximum results to return
            
        Returns:
            Search results from the source
            
        Raises:
            DiscoveryError: When search fails
        """
        async with semaphore:
            start_time = asyncio.get_event_loop().time()
            
            try:
                if source == "apple_podcasts" and self._apple_client:
                    async with self._apple_client as client:
                        results = await client.search_podcasts(query, limit)
                elif source == "spotify" and self._spotify_client:
                    async with self._spotify_client as client:
                        results = await client.search_podcasts(query, limit)
                else:
                    raise DiscoveryError(f"Unknown or unavailable source: {source}")
                
                search_time = asyncio.get_event_loop().time() - start_time
                
                return SearchResult(
                    results=results,
                    source=source,
                    query=query,
                    total_found=len(results),
                    search_time=search_time
                )
                
            except Exception as e:
                logger.error(f"Search failed for {source}: {e}")
                raise DiscoveryError(f"{source} search failed: {str(e)}") from e
    
    def _get_enabled_sources(self, requested_sources: Optional[List[str]]) -> List[str]:
        """
        Get list of enabled sources to search.
        
        Args:
            requested_sources: Specific sources requested by user
            
        Returns:
            List of enabled source names to search
        """
        available_sources = self.get_available_sources()
        
        if requested_sources is None:
            return available_sources
        
        # Filter requested sources to only include available ones
        enabled_sources = [
            source for source in requested_sources
            if source in available_sources
        ]
        
        return enabled_sources
    
    def _deduplicate_results(self, results: List[PodcastResult]) -> List[PodcastResult]:
        """
        Remove duplicate podcast results based on RSS URL.
        
        Args:
            results: List of podcast results to deduplicate
            
        Returns:
            Deduplicated list of podcast results
        """
        seen_urls: Set[str] = set()
        deduplicated = []
        
        for result in results:
            # Normalize RSS URL for comparison
            normalized_url = self._normalize_url(str(result.rss_url))
            
            if normalized_url not in seen_urls:
                seen_urls.add(normalized_url)
                deduplicated.append(result)
            else:
                logger.debug(f"Removing duplicate podcast: {result.title}")
        
        logger.info(f"Deduplicated {len(results)} results to {len(deduplicated)}")
        return deduplicated
    
    def _rank_results(self, results: List[PodcastResult], query: str) -> List[PodcastResult]:
        """
        Rank and sort podcast results by relevance to the search query.
        
        Args:
            results: List of podcast results to rank
            query: Original search query
            
        Returns:
            Ranked and sorted list of podcast results
        """
        query_terms = set(query.lower().split())
        
        def calculate_relevance_score(podcast: PodcastResult) -> float:
            """Calculate relevance score for a podcast result."""
            score = 0.0
            
            # Title matches (highest weight)
            title_words = set(podcast.title.lower().split())
            title_matches = len(query_terms.intersection(title_words))
            score += title_matches * 3.0
            
            # Author matches (medium weight)
            author_words = set(podcast.author.lower().split())
            author_matches = len(query_terms.intersection(author_words))
            score += author_matches * 2.0
            
            # Description matches (lower weight)
            description_words = set(podcast.description.lower().split())
            description_matches = len(query_terms.intersection(description_words))
            score += description_matches * 1.0
            
            # Exact phrase matches in title (bonus)
            if query.lower() in podcast.title.lower():
                score += 5.0
            
            # Exact phrase matches in description (smaller bonus)
            if query.lower() in podcast.description.lower():
                score += 2.0
            
            return score
        
        # Sort by relevance score (descending)
        ranked_results = sorted(
            results,
            key=calculate_relevance_score,
            reverse=True
        )
        
        logger.debug(f"Ranked {len(results)} results by relevance to '{query}'")
        return ranked_results
    
    def _normalize_url(self, url: str) -> str:
        """
        Normalize URL for comparison purposes.
        
        Args:
            url: URL to normalize
            
        Returns:
            Normalized URL string
        """
        try:
            parsed = urlparse(url.lower().strip())
            # Remove common variations
            normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            # Remove trailing slash
            if normalized.endswith('/'):
                normalized = normalized[:-1]
            return normalized
        except Exception:
            return url.lower().strip()