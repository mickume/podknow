"""
Podcast discovery service implementation.
"""

import requests
import time
from typing import List, Dict, Any, Optional
from urllib.parse import quote_plus
from ..models.podcast import PodcastResult
from ..exceptions import NetworkError


class iTunesAPIClient:
    """Client for iTunes Search API."""
    
    BASE_URL = "https://itunes.apple.com/search"
    TIMEOUT = 10
    MAX_RETRIES = 3
    RETRY_DELAY = 1
    
    def search_podcasts(self, query: str, limit: int = 50) -> List[PodcastResult]:
        """
        Search for podcasts using iTunes API.
        
        Args:
            query: Search keywords
            limit: Maximum number of results (default 50)
            
        Returns:
            List of PodcastResult objects
            
        Raises:
            NetworkError: If API request fails after retries
        """
        if not query.strip():
            return []
            
        params = {
            'term': query,
            'media': 'podcast',
            'entity': 'podcast',
            'limit': min(limit, 200),  # iTunes API max is 200
            'explicit': 'Yes'
        }
        
        for attempt in range(self.MAX_RETRIES):
            try:
                response = requests.get(
                    self.BASE_URL,
                    params=params,
                    timeout=self.TIMEOUT,
                    headers={'User-Agent': 'PodKnow/1.0'}
                )
                response.raise_for_status()
                
                data = response.json()
                return self._parse_itunes_response(data)
                
            except requests.exceptions.Timeout:
                if attempt == self.MAX_RETRIES - 1:
                    raise NetworkError(f"iTunes API timeout after {self.MAX_RETRIES} attempts")
                time.sleep(self.RETRY_DELAY * (attempt + 1))
                
            except requests.exceptions.RequestException as e:
                if attempt == self.MAX_RETRIES - 1:
                    raise NetworkError(f"iTunes API request failed: {str(e)}")
                time.sleep(self.RETRY_DELAY * (attempt + 1))
                
            except (ValueError, KeyError) as e:
                raise NetworkError(f"Invalid iTunes API response: {str(e)}")
    
    def _parse_itunes_response(self, data: Dict[str, Any]) -> List[PodcastResult]:
        """Parse iTunes API response into PodcastResult objects."""
        results = []
        
        for item in data.get('results', []):
            try:
                # Extract RSS feed URL from feedUrl field
                rss_url = item.get('feedUrl', '')
                if not rss_url:
                    continue  # Skip podcasts without RSS feeds
                
                result = PodcastResult(
                    title=item.get('collectionName', '').strip(),
                    author=item.get('artistName', '').strip(),
                    rss_url=rss_url,
                    platform='iTunes',
                    description=item.get('description', '').strip()
                )
                
                # Only add if we have required fields
                if result.title and result.author:
                    results.append(result)
                    
            except (ValueError, KeyError):
                # Skip malformed entries
                continue
                
        return results


class SpotifyAPIClient:
    """Client for Spotify Web API."""
    
    BASE_URL = "https://api.spotify.com/v1"
    AUTH_URL = "https://accounts.spotify.com/api/token"
    TIMEOUT = 10
    MAX_RETRIES = 3
    RETRY_DELAY = 1
    
    def __init__(self, client_id: Optional[str] = None, client_secret: Optional[str] = None):
        """
        Initialize Spotify API client.
        
        Args:
            client_id: Spotify app client ID (optional, can be set via environment)
            client_secret: Spotify app client secret (optional, can be set via environment)
        """
        import os
        self.client_id = client_id or os.getenv('SPOTIFY_CLIENT_ID')
        self.client_secret = client_secret or os.getenv('SPOTIFY_CLIENT_SECRET')
        self.access_token = None
        self.token_expires_at = 0
    
    def _get_access_token(self) -> str:
        """Get or refresh Spotify access token using client credentials flow."""
        import base64
        
        if not self.client_id or not self.client_secret:
            raise NetworkError("Spotify API credentials not configured. Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET environment variables.")
        
        # Check if current token is still valid
        if self.access_token and time.time() < self.token_expires_at:
            return self.access_token
        
        # Request new token
        auth_string = f"{self.client_id}:{self.client_secret}"
        auth_bytes = auth_string.encode('ascii')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
        
        headers = {
            'Authorization': f'Basic {auth_b64}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {'grant_type': 'client_credentials'}
        
        try:
            response = requests.post(
                self.AUTH_URL,
                headers=headers,
                data=data,
                timeout=self.TIMEOUT
            )
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data['access_token']
            # Set expiration with 5 minute buffer
            expires_in = token_data.get('expires_in', 3600)
            self.token_expires_at = time.time() + expires_in - 300
            
            return self.access_token
            
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"Spotify authentication failed: {str(e)}")
        except (ValueError, KeyError) as e:
            raise NetworkError(f"Invalid Spotify auth response: {str(e)}")
    
    def search_podcasts(self, query: str, limit: int = 50) -> List[PodcastResult]:
        """
        Search for podcasts using Spotify API.
        
        Args:
            query: Search keywords
            limit: Maximum number of results (default 50)
            
        Returns:
            List of PodcastResult objects
            
        Raises:
            NetworkError: If API request fails after retries
        """
        if not query.strip():
            return []
        
        access_token = self._get_access_token()
        
        params = {
            'q': query,
            'type': 'show',
            'limit': min(limit, 50),  # Spotify API max is 50
            'market': 'US'
        }
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'User-Agent': 'PodKnow/1.0'
        }
        
        for attempt in range(self.MAX_RETRIES):
            try:
                response = requests.get(
                    f"{self.BASE_URL}/search",
                    params=params,
                    headers=headers,
                    timeout=self.TIMEOUT
                )
                response.raise_for_status()
                
                data = response.json()
                return self._parse_spotify_response(data)
                
            except requests.exceptions.Timeout:
                if attempt == self.MAX_RETRIES - 1:
                    raise NetworkError(f"Spotify API timeout after {self.MAX_RETRIES} attempts")
                time.sleep(self.RETRY_DELAY * (attempt + 1))
                
            except requests.exceptions.RequestException as e:
                if attempt == self.MAX_RETRIES - 1:
                    raise NetworkError(f"Spotify API request failed: {str(e)}")
                time.sleep(self.RETRY_DELAY * (attempt + 1))
                
            except (ValueError, KeyError) as e:
                raise NetworkError(f"Invalid Spotify API response: {str(e)}")
    
    def _parse_spotify_response(self, data: Dict[str, Any]) -> List[PodcastResult]:
        """Parse Spotify API response into PodcastResult objects."""
        results = []
        
        shows = data.get('shows', {}).get('items', [])
        for show in shows:
            try:
                # Spotify doesn't provide RSS URLs directly, so we'll use the Spotify URL
                # In a real implementation, you might need to find RSS feeds through other means
                spotify_url = show.get('external_urls', {}).get('spotify', '')
                if not spotify_url:
                    continue
                
                # Extract publisher name
                publisher = show.get('publisher', '').strip()
                if not publisher:
                    continue
                
                result = PodcastResult(
                    title=show.get('name', '').strip(),
                    author=publisher,
                    rss_url=spotify_url,  # Note: This is Spotify URL, not RSS
                    platform='Spotify',
                    description=show.get('description', '').strip()
                )
                
                # Only add if we have required fields
                if result.title and result.author:
                    results.append(result)
                    
            except (ValueError, KeyError):
                # Skip malformed entries
                continue
                
        return results


class PodcastDiscoveryService:
    """Service for discovering podcasts across multiple platforms."""
    
    def __init__(self, spotify_client_id: Optional[str] = None, spotify_client_secret: Optional[str] = None):
        """Initialize discovery service with API clients."""
        self.itunes_client = iTunesAPIClient()
        self.spotify_client = SpotifyAPIClient(spotify_client_id, spotify_client_secret)
    
    def search_itunes(self, query: str) -> List[PodcastResult]:
        """Search for podcasts using iTunes API."""
        try:
            return self.itunes_client.search_podcasts(query)
        except NetworkError as e:
            # Log error but don't fail completely
            print(f"iTunes search failed: {e}")
            return []
    
    def search_spotify(self, query: str) -> List[PodcastResult]:
        """Search for podcasts using Spotify API."""
        try:
            return self.spotify_client.search_podcasts(query)
        except NetworkError as e:
            # Log error but don't fail completely
            print(f"Spotify search failed: {e}")
            return []
    
    def get_combined_results(self, query: str) -> List[PodcastResult]:
        """
        Get combined search results from all platforms.
        
        Args:
            query: Search keywords
            
        Returns:
            List of deduplicated and ranked PodcastResult objects
            
        Raises:
            NetworkError: If all API searches fail
        """
        if not query.strip():
            return []
        
        all_results = []
        errors = []
        
        # Search iTunes
        try:
            itunes_results = self.itunes_client.search_podcasts(query)
            all_results.extend(itunes_results)
        except NetworkError as e:
            errors.append(f"iTunes: {e}")
        
        # Search Spotify (only if credentials are available)
        try:
            spotify_results = self.spotify_client.search_podcasts(query)
            all_results.extend(spotify_results)
        except NetworkError as e:
            errors.append(f"Spotify: {e}")
        
        # If all searches failed, raise error
        if not all_results and errors:
            raise NetworkError(f"All podcast searches failed: {'; '.join(errors)}")
        
        # Deduplicate and rank results
        deduplicated = self._deduplicate_results(all_results)
        ranked = self._rank_results(deduplicated, query)
        
        return ranked
    
    def _deduplicate_results(self, results: List[PodcastResult]) -> List[PodcastResult]:
        """
        Remove duplicate podcasts based on title and author similarity.
        
        Args:
            results: List of podcast results to deduplicate
            
        Returns:
            List of unique podcast results
        """
        if not results:
            return []
        
        unique_results = []
        seen_combinations = set()
        
        for result in results:
            # Create a normalized key for comparison
            title_key = self._normalize_string(result.title)
            author_key = self._normalize_string(result.author)
            combination_key = f"{title_key}|{author_key}"
            
            if combination_key not in seen_combinations:
                seen_combinations.add(combination_key)
                unique_results.append(result)
        
        return unique_results
    
    def _normalize_string(self, text: str) -> str:
        """Normalize string for comparison by removing extra whitespace and converting to lowercase."""
        return ' '.join(text.lower().split())
    
    def _rank_results(self, results: List[PodcastResult], query: str) -> List[PodcastResult]:
        """
        Rank results by relevance to the search query.
        
        Args:
            results: List of podcast results to rank
            query: Original search query
            
        Returns:
            List of results sorted by relevance score (highest first)
        """
        if not results:
            return []
        
        query_words = set(self._normalize_string(query).split())
        
        # Calculate relevance scores
        scored_results = []
        for result in results:
            score = self._calculate_relevance_score(result, query_words)
            scored_results.append((score, result))
        
        # Sort by score (descending) and return results
        scored_results.sort(key=lambda x: x[0], reverse=True)
        return [result for score, result in scored_results]
    
    def _calculate_relevance_score(self, result: PodcastResult, query_words: set) -> float:
        """
        Calculate relevance score for a podcast result.
        
        Args:
            result: Podcast result to score
            query_words: Set of normalized query words
            
        Returns:
            Relevance score (higher is better)
        """
        score = 0.0
        
        # Title matches (highest weight)
        title_words = set(self._normalize_string(result.title).split())
        title_matches = len(query_words.intersection(title_words))
        score += title_matches * 3.0
        
        # Author matches (medium weight)
        author_words = set(self._normalize_string(result.author).split())
        author_matches = len(query_words.intersection(author_words))
        score += author_matches * 2.0
        
        # Description matches (lower weight)
        description_words = set(self._normalize_string(result.description).split())
        description_matches = len(query_words.intersection(description_words))
        score += description_matches * 1.0
        
        # Prefer iTunes results (they have RSS feeds)
        if result.platform == 'iTunes':
            score += 0.5
        
        return score