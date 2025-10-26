"""
Integration tests for podcast discovery service.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests
from podknow.services.discovery import PodcastDiscoveryService, iTunesAPIClient, SpotifyAPIClient
from podknow.models.podcast import PodcastResult
from podknow.exceptions import NetworkError


class TestiTunesAPIClient:
    """Test iTunes API client."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.client = iTunesAPIClient()
    
    @patch('requests.get')
    def test_search_podcasts_success(self, mock_get):
        """Test successful iTunes API search."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.json.return_value = {
            'results': [
                {
                    'collectionName': 'Test Podcast',
                    'artistName': 'Test Author',
                    'feedUrl': 'https://example.com/feed.xml',
                    'description': 'Test description'
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        results = self.client.search_podcasts('test query')
        
        assert len(results) == 1
        assert results[0].title == 'Test Podcast'
        assert results[0].author == 'Test Author'
        assert results[0].rss_url == 'https://example.com/feed.xml'
        assert results[0].platform == 'iTunes'
        assert results[0].description == 'Test description'
        
        # Verify API call
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert 'term' in call_args[1]['params']
        assert call_args[1]['params']['term'] == 'test query'
    
    @patch('requests.get')
    def test_search_podcasts_empty_query(self, mock_get):
        """Test search with empty query returns empty list."""
        results = self.client.search_podcasts('')
        assert results == []
        mock_get.assert_not_called()
    
    @patch('requests.get')
    def test_search_podcasts_no_feed_url(self, mock_get):
        """Test that podcasts without feed URLs are filtered out."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'results': [
                {
                    'collectionName': 'Test Podcast',
                    'artistName': 'Test Author',
                    'description': 'Test description'
                    # No feedUrl field
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        results = self.client.search_podcasts('test query')
        assert len(results) == 0
    
    @patch('requests.get')
    def test_search_podcasts_timeout_retry(self, mock_get):
        """Test timeout handling with retries."""
        # First two calls timeout, third succeeds
        mock_get.side_effect = [
            requests.exceptions.Timeout(),
            requests.exceptions.Timeout(),
            Mock(json=lambda: {'results': []}, raise_for_status=lambda: None)
        ]
        
        results = self.client.search_podcasts('test query')
        assert results == []
        assert mock_get.call_count == 3
    
    @patch('requests.get')
    def test_search_podcasts_timeout_failure(self, mock_get):
        """Test timeout failure after max retries."""
        mock_get.side_effect = requests.exceptions.Timeout()
        
        with pytest.raises(NetworkError, match="iTunes API timeout"):
            self.client.search_podcasts('test query')
        
        assert mock_get.call_count == 3
    
    @patch('requests.get')
    def test_search_podcasts_request_error(self, mock_get):
        """Test request error handling."""
        mock_get.side_effect = requests.exceptions.RequestException("Connection error")
        
        with pytest.raises(NetworkError, match="iTunes API request failed"):
            self.client.search_podcasts('test query')
    
    @patch('requests.get')
    def test_search_podcasts_invalid_json(self, mock_get):
        """Test invalid JSON response handling."""
        mock_response = Mock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        with pytest.raises(NetworkError, match="Invalid iTunes API response"):
            self.client.search_podcasts('test query')


class TestSpotifyAPIClient:
    """Test Spotify API client."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.client = SpotifyAPIClient('test_client_id', 'test_client_secret')
    
    @patch('requests.post')
    @patch('requests.get')
    def test_search_podcasts_success(self, mock_get, mock_post):
        """Test successful Spotify API search."""
        # Mock authentication response
        mock_auth_response = Mock()
        mock_auth_response.json.return_value = {
            'access_token': 'test_token',
            'expires_in': 3600
        }
        mock_auth_response.raise_for_status.return_value = None
        mock_post.return_value = mock_auth_response
        
        # Mock search response
        mock_search_response = Mock()
        mock_search_response.json.return_value = {
            'shows': {
                'items': [
                    {
                        'name': 'Test Podcast',
                        'publisher': 'Test Publisher',
                        'external_urls': {'spotify': 'https://spotify.com/show/123'},
                        'description': 'Test description'
                    }
                ]
            }
        }
        mock_search_response.raise_for_status.return_value = None
        mock_get.return_value = mock_search_response
        
        results = self.client.search_podcasts('test query')
        
        assert len(results) == 1
        assert results[0].title == 'Test Podcast'
        assert results[0].author == 'Test Publisher'
        assert results[0].rss_url == 'https://spotify.com/show/123'
        assert results[0].platform == 'Spotify'
        assert results[0].description == 'Test description'
    
    def test_search_podcasts_no_credentials(self):
        """Test search without credentials raises error."""
        client = SpotifyAPIClient()  # No credentials
        
        with pytest.raises(NetworkError, match="Spotify API credentials not configured"):
            client.search_podcasts('test query')
    
    @patch('requests.post')
    def test_auth_failure(self, mock_post):
        """Test authentication failure."""
        mock_post.side_effect = requests.exceptions.RequestException("Auth failed")
        
        with pytest.raises(NetworkError, match="Spotify authentication failed"):
            self.client.search_podcasts('test query')
    
    @patch('requests.post')
    @patch('requests.get')
    def test_search_podcasts_empty_query(self, mock_get, mock_post):
        """Test search with empty query returns empty list."""
        results = self.client.search_podcasts('')
        assert results == []
        mock_post.assert_not_called()
        mock_get.assert_not_called()
    
    @patch('requests.post')
    @patch('requests.get')
    def test_search_podcasts_no_spotify_url(self, mock_get, mock_post):
        """Test that shows without Spotify URLs are filtered out."""
        # Mock authentication
        mock_auth_response = Mock()
        mock_auth_response.json.return_value = {
            'access_token': 'test_token',
            'expires_in': 3600
        }
        mock_auth_response.raise_for_status.return_value = None
        mock_post.return_value = mock_auth_response
        
        # Mock search response without external_urls
        mock_search_response = Mock()
        mock_search_response.json.return_value = {
            'shows': {
                'items': [
                    {
                        'name': 'Test Podcast',
                        'publisher': 'Test Publisher',
                        'description': 'Test description'
                        # No external_urls field
                    }
                ]
            }
        }
        mock_search_response.raise_for_status.return_value = None
        mock_get.return_value = mock_search_response
        
        results = self.client.search_podcasts('test query')
        assert len(results) == 0


class TestPodcastDiscoveryService:
    """Test combined podcast discovery service."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.service = PodcastDiscoveryService('test_client_id', 'test_client_secret')
    
    @patch.object(iTunesAPIClient, 'search_podcasts')
    def test_search_itunes_success(self, mock_itunes_search):
        """Test iTunes search through service."""
        mock_results = [
            PodcastResult('Test Podcast', 'Test Author', 'https://example.com/feed.xml', 'iTunes', 'Description')
        ]
        mock_itunes_search.return_value = mock_results
        
        results = self.service.search_itunes('test query')
        assert results == mock_results
        mock_itunes_search.assert_called_once_with('test query')
    
    @patch.object(iTunesAPIClient, 'search_podcasts')
    def test_search_itunes_error_handling(self, mock_itunes_search):
        """Test iTunes search error handling."""
        mock_itunes_search.side_effect = NetworkError("API error")
        
        results = self.service.search_itunes('test query')
        assert results == []
    
    @patch.object(SpotifyAPIClient, 'search_podcasts')
    def test_search_spotify_success(self, mock_spotify_search):
        """Test Spotify search through service."""
        mock_results = [
            PodcastResult('Test Podcast', 'Test Author', 'https://spotify.com/show/123', 'Spotify', 'Description')
        ]
        mock_spotify_search.return_value = mock_results
        
        results = self.service.search_spotify('test query')
        assert results == mock_results
        mock_spotify_search.assert_called_once_with('test query')
    
    @patch.object(SpotifyAPIClient, 'search_podcasts')
    def test_search_spotify_error_handling(self, mock_spotify_search):
        """Test Spotify search error handling."""
        mock_spotify_search.side_effect = NetworkError("API error")
        
        results = self.service.search_spotify('test query')
        assert results == []
    
    @patch.object(iTunesAPIClient, 'search_podcasts')
    @patch.object(SpotifyAPIClient, 'search_podcasts')
    def test_get_combined_results_success(self, mock_spotify_search, mock_itunes_search):
        """Test successful combined search."""
        itunes_results = [
            PodcastResult('Podcast A', 'Author A', 'https://example.com/feed1.xml', 'iTunes', 'Description A')
        ]
        spotify_results = [
            PodcastResult('Podcast B', 'Author B', 'https://spotify.com/show/123', 'Spotify', 'Description B')
        ]
        
        mock_itunes_search.return_value = itunes_results
        mock_spotify_search.return_value = spotify_results
        
        results = self.service.get_combined_results('test query')
        
        assert len(results) == 2
        # iTunes results should be ranked higher due to platform preference
        assert results[0].platform == 'iTunes'
        assert results[1].platform == 'Spotify'
    
    @patch.object(iTunesAPIClient, 'search_podcasts')
    @patch.object(SpotifyAPIClient, 'search_podcasts')
    def test_get_combined_results_deduplication(self, mock_spotify_search, mock_itunes_search):
        """Test deduplication of similar results."""
        # Same podcast from both platforms
        itunes_result = PodcastResult('Test Podcast', 'Test Author', 'https://example.com/feed.xml', 'iTunes', 'Description')
        spotify_result = PodcastResult('Test Podcast', 'Test Author', 'https://spotify.com/show/123', 'Spotify', 'Description')
        
        mock_itunes_search.return_value = [itunes_result]
        mock_spotify_search.return_value = [spotify_result]
        
        results = self.service.get_combined_results('test query')
        
        # Should only return one result after deduplication
        assert len(results) == 1
        # Should prefer iTunes result
        assert results[0].platform == 'iTunes'
    
    @patch.object(iTunesAPIClient, 'search_podcasts')
    @patch.object(SpotifyAPIClient, 'search_podcasts')
    def test_get_combined_results_all_fail(self, mock_spotify_search, mock_itunes_search):
        """Test behavior when all searches fail."""
        mock_itunes_search.side_effect = NetworkError("iTunes error")
        mock_spotify_search.side_effect = NetworkError("Spotify error")
        
        with pytest.raises(NetworkError, match="All podcast searches failed"):
            self.service.get_combined_results('test query')
    
    @patch.object(iTunesAPIClient, 'search_podcasts')
    @patch.object(SpotifyAPIClient, 'search_podcasts')
    def test_get_combined_results_partial_failure(self, mock_spotify_search, mock_itunes_search):
        """Test behavior when one search fails."""
        itunes_results = [
            PodcastResult('Podcast A', 'Author A', 'https://example.com/feed1.xml', 'iTunes', 'Description A')
        ]
        
        mock_itunes_search.return_value = itunes_results
        mock_spotify_search.side_effect = NetworkError("Spotify error")
        
        results = self.service.get_combined_results('test query')
        
        # Should return iTunes results even though Spotify failed
        assert len(results) == 1
        assert results[0].platform == 'iTunes'
    
    def test_get_combined_results_empty_query(self):
        """Test combined search with empty query."""
        results = self.service.get_combined_results('')
        assert results == []
    
    def test_normalize_string(self):
        """Test string normalization for comparison."""
        normalized = self.service._normalize_string('  Test   String  ')
        assert normalized == 'test string'
    
    def test_calculate_relevance_score(self):
        """Test relevance score calculation."""
        result = PodcastResult(
            'Machine Learning Podcast',
            'AI Expert',
            'https://example.com/feed.xml',
            'iTunes',
            'A podcast about artificial intelligence and machine learning'
        )
        query_words = {'machine', 'learning'}
        
        score = self.service._calculate_relevance_score(result, query_words)
        
        # Should have high score due to title matches
        assert score > 5.0  # 2 title matches * 3.0 + platform bonus
    
    def test_rank_results(self):
        """Test result ranking by relevance."""
        results = [
            PodcastResult('Random Podcast', 'Random Author', 'https://example.com/feed1.xml', 'iTunes', 'Random content'),
            PodcastResult('Machine Learning Podcast', 'AI Expert', 'https://example.com/feed2.xml', 'iTunes', 'ML content')
        ]
        
        ranked = self.service._rank_results(results, 'machine learning')
        
        # ML podcast should be ranked first
        assert ranked[0].title == 'Machine Learning Podcast'
        assert ranked[1].title == 'Random Podcast'