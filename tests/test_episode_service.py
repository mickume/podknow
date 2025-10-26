"""
Unit tests for episode listing service functionality.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from podknow.services.episode import EpisodeListingService, EpisodeManagementError
from podknow.services.rss import RSSParsingError
from podknow.models.episode import Episode
from podknow.models.podcast import PodcastMetadata


class TestEpisodeListingService:
    """Test EpisodeListingService functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.service = EpisodeListingService()
        self.test_rss_url = "https://example.com/feed.xml"
        
        # Create sample episodes for testing
        self.sample_episodes = [
            Episode(
                id="ep1",
                title="Episode 1",
                description="First episode",
                audio_url="https://example.com/ep1.mp3",
                publication_date=datetime(2024, 1, 15, 10, 0, 0),
                duration="30:00"
            ),
            Episode(
                id="ep2", 
                title="Episode 2",
                description="Second episode",
                audio_url="https://example.com/ep2.mp3",
                publication_date=datetime(2024, 1, 16, 10, 0, 0),
                duration="25:00"
            ),
            Episode(
                id="ep3",
                title="Episode 3", 
                description="Third episode",
                audio_url="https://example.com/ep3.mp3",
                publication_date=datetime(2024, 1, 17, 10, 0, 0),
                duration="35:00"
            )
        ]
    
    def test_init(self):
        """Test EpisodeListingService initialization."""
        service = EpisodeListingService()
        assert service is not None
        assert hasattr(service, 'rss_parser')
    
    @patch('podknow.services.episode.RSSFeedParser.get_episodes')
    def test_list_episodes_success(self, mock_get_episodes):
        """Test successful episode listing."""
        mock_get_episodes.return_value = self.sample_episodes
        
        result = self.service.list_episodes(self.test_rss_url, count=10)
        
        assert len(result) == 3
        assert all(isinstance(ep, Episode) for ep in result)
        # Should be sorted by date (newest first)
        assert result[0].title == "Episode 3"
        assert result[1].title == "Episode 2"
        assert result[2].title == "Episode 1"
        
        mock_get_episodes.assert_called_once_with(self.test_rss_url, 10)
    
    @patch('podknow.services.episode.RSSFeedParser.get_episodes')
    def test_list_episodes_with_count_limit(self, mock_get_episodes):
        """Test episode listing with count limit."""
        mock_get_episodes.return_value = self.sample_episodes
        
        result = self.service.list_episodes(self.test_rss_url, count=2)
        
        assert len(result) == 3  # RSS parser handles the count limit
        mock_get_episodes.assert_called_once_with(self.test_rss_url, 2)
    
    def test_list_episodes_invalid_count(self):
        """Test episode listing with invalid count."""
        with pytest.raises(EpisodeManagementError, match="Episode count must be positive"):
            self.service.list_episodes(self.test_rss_url, count=0)
        
        with pytest.raises(EpisodeManagementError, match="Episode count must be positive"):
            self.service.list_episodes(self.test_rss_url, count=-1)
    
    @patch('podknow.services.episode.RSSFeedParser.get_episodes')
    def test_list_episodes_no_sorting(self, mock_get_episodes):
        """Test episode listing without sorting."""
        # Return episodes in original order
        mock_get_episodes.return_value = self.sample_episodes
        
        result = self.service.list_episodes(self.test_rss_url, sort_by_date=False)
        
        # Should maintain original order when sort_by_date=False
        assert result[0].title == "Episode 1"
        assert result[1].title == "Episode 2"
        assert result[2].title == "Episode 3"
    
    @patch('podknow.services.episode.RSSFeedParser.get_episodes')
    def test_list_episodes_rss_error(self, mock_get_episodes):
        """Test episode listing with RSS parsing error."""
        mock_get_episodes.side_effect = RSSParsingError("Feed parsing failed")
        
        with pytest.raises(EpisodeManagementError, match="Failed to list episodes"):
            self.service.list_episodes(self.test_rss_url)
    
    @patch('podknow.services.episode.RSSFeedParser.get_episodes')
    def test_list_episodes_unexpected_error(self, mock_get_episodes):
        """Test episode listing with unexpected error."""
        mock_get_episodes.side_effect = Exception("Unexpected error")
        
        with pytest.raises(EpisodeManagementError, match="Unexpected error listing episodes"):
            self.service.list_episodes(self.test_rss_url)
    
    @patch('podknow.services.episode.RSSFeedParser.parse_feed')
    def test_get_podcast_info_success(self, mock_parse_feed):
        """Test successful podcast info retrieval."""
        mock_metadata = PodcastMetadata(
            title="Test Podcast",
            author="Test Author",
            description="Test Description",
            rss_url=self.test_rss_url,
            episode_count=10,
            last_updated=datetime.now()
        )
        mock_parse_feed.return_value = mock_metadata
        
        result = self.service.get_podcast_info(self.test_rss_url)
        
        assert isinstance(result, PodcastMetadata)
        assert result.title == "Test Podcast"
        assert result.author == "Test Author"
        
        mock_parse_feed.assert_called_once_with(self.test_rss_url)
    
    @patch('podknow.services.episode.RSSFeedParser.parse_feed')
    def test_get_podcast_info_rss_error(self, mock_parse_feed):
        """Test podcast info retrieval with RSS parsing error."""
        mock_parse_feed.side_effect = RSSParsingError("Feed parsing failed")
        
        with pytest.raises(EpisodeManagementError, match="Failed to get podcast info"):
            self.service.get_podcast_info(self.test_rss_url)
    
    @patch('podknow.services.episode.RSSFeedParser.get_episodes')
    def test_find_episode_by_id_success(self, mock_get_episodes):
        """Test successful episode finding by ID."""
        mock_get_episodes.return_value = self.sample_episodes
        
        result = self.service.find_episode_by_id(self.test_rss_url, "ep2")
        
        assert result is not None
        assert result.id == "ep2"
        assert result.title == "Episode 2"
        
        mock_get_episodes.assert_called_once_with(self.test_rss_url, count=None)
    
    @patch('podknow.services.episode.RSSFeedParser.get_episodes')
    def test_find_episode_by_id_not_found(self, mock_get_episodes):
        """Test episode finding when ID not found."""
        mock_get_episodes.return_value = self.sample_episodes
        
        result = self.service.find_episode_by_id(self.test_rss_url, "nonexistent")
        
        assert result is None
    
    @patch('podknow.services.episode.RSSFeedParser.get_episodes')
    def test_find_episode_by_id_rss_error(self, mock_get_episodes):
        """Test episode finding with RSS parsing error."""
        mock_get_episodes.side_effect = RSSParsingError("Feed parsing failed")
        
        with pytest.raises(EpisodeManagementError, match="Failed to find episode"):
            self.service.find_episode_by_id(self.test_rss_url, "ep1")
    
    def test_format_episode_list_empty(self):
        """Test formatting empty episode list."""
        result = self.service.format_episode_list([])
        assert result == "No episodes found."
    
    def test_format_episode_list_basic(self):
        """Test basic episode list formatting."""
        episodes = self.sample_episodes[:2]  # First 2 episodes
        
        result = self.service.format_episode_list(episodes)
        
        assert "Found 2 episode(s):" in result
        assert "[ep1] Episode 1" in result
        assert "[ep2] Episode 2" in result
        assert "Date: 2024-01-15" in result
        assert "Date: 2024-01-16" in result
        assert "Duration: 30:00" in result
        assert "Duration: 25:00" in result
    
    def test_format_episode_list_with_descriptions(self):
        """Test episode list formatting with descriptions."""
        episodes = self.sample_episodes[:1]
        
        result = self.service.format_episode_list(episodes, show_descriptions=True)
        
        assert "Description: First episode" in result
    
    def test_format_episode_list_long_description(self):
        """Test episode list formatting with long description truncation."""
        long_desc = "A" * 250  # Long description
        episode = Episode(
            id="ep1",
            title="Episode 1",
            description=long_desc,
            audio_url="https://example.com/ep1.mp3",
            publication_date=datetime(2024, 1, 15, 10, 0, 0),
            duration="30:00"
        )
        
        result = self.service.format_episode_list([episode], show_descriptions=True)
        
        assert "..." in result  # Should be truncated
        assert len(result.split("Description: ")[1].split("\n")[0]) <= 203  # 200 + "..."
    
    def test_format_podcast_info(self):
        """Test podcast info formatting."""
        podcast = PodcastMetadata(
            title="Test Podcast",
            author="Test Author",
            description="Test Description",
            rss_url=self.test_rss_url,
            episode_count=10,
            last_updated=datetime(2024, 1, 15, 10, 30, 0)
        )
        
        result = self.service.format_podcast_info(podcast)
        
        assert "Podcast: Test Podcast" in result
        assert "Author: Test Author" in result
        assert "Episodes: 10" in result
        assert "Last Updated: 2024-01-15 10:30" in result
        assert "RSS URL: https://example.com/feed.xml" in result
        assert "Description: Test Description" in result
    
    def test_format_podcast_info_long_description(self):
        """Test podcast info formatting with long description truncation."""
        long_desc = "A" * 350  # Long description
        podcast = PodcastMetadata(
            title="Test Podcast",
            author="Test Author",
            description=long_desc,
            rss_url=self.test_rss_url,
            episode_count=10,
            last_updated=datetime(2024, 1, 15, 10, 30, 0)
        )
        
        result = self.service.format_podcast_info(podcast)
        
        assert "..." in result  # Should be truncated
        assert len(result.split("Description: ")[1]) <= 303  # 300 + "..."
    
    @patch('podknow.services.episode.RSSFeedParser.get_episodes')
    def test_get_recent_episodes_success(self, mock_get_episodes):
        """Test successful recent episodes retrieval."""
        # Create episodes with different dates
        now = datetime.now()
        recent_episodes = [
            Episode(
                id="recent1",
                title="Recent Episode 1",
                description="Recent episode",
                audio_url="https://example.com/recent1.mp3",
                publication_date=now - timedelta(days=5),
                duration="30:00"
            ),
            Episode(
                id="recent2",
                title="Recent Episode 2", 
                description="Recent episode",
                audio_url="https://example.com/recent2.mp3",
                publication_date=now - timedelta(days=10),
                duration="25:00"
            ),
            Episode(
                id="old1",
                title="Old Episode",
                description="Old episode",
                audio_url="https://example.com/old1.mp3",
                publication_date=now - timedelta(days=40),
                duration="35:00"
            )
        ]
        
        mock_get_episodes.return_value = recent_episodes
        
        result = self.service.get_recent_episodes(self.test_rss_url, days=30)
        
        # Should only return episodes from last 30 days
        assert len(result) == 2
        assert result[0].title == "Recent Episode 1"  # Newest first
        assert result[1].title == "Recent Episode 2"
    
    @patch('podknow.services.episode.RSSFeedParser.get_episodes')
    def test_get_recent_episodes_with_count(self, mock_get_episodes):
        """Test recent episodes retrieval with count limit."""
        now = datetime.now()
        recent_episodes = [
            Episode(
                id="recent1",
                title="Recent Episode 1",
                description="Recent episode",
                audio_url="https://example.com/recent1.mp3",
                publication_date=now - timedelta(days=5),
                duration="30:00"
            ),
            Episode(
                id="recent2",
                title="Recent Episode 2",
                description="Recent episode", 
                audio_url="https://example.com/recent2.mp3",
                publication_date=now - timedelta(days=10),
                duration="25:00"
            )
        ]
        
        mock_get_episodes.return_value = recent_episodes
        
        result = self.service.get_recent_episodes(self.test_rss_url, days=30, count=1)
        
        # Should only return 1 episode (the newest)
        assert len(result) == 1
        assert result[0].title == "Recent Episode 1"
    
    def test_get_recent_episodes_invalid_days(self):
        """Test recent episodes retrieval with invalid days parameter."""
        with pytest.raises(EpisodeManagementError, match="Days must be positive"):
            self.service.get_recent_episodes(self.test_rss_url, days=0)
        
        with pytest.raises(EpisodeManagementError, match="Days must be positive"):
            self.service.get_recent_episodes(self.test_rss_url, days=-1)
    
    @patch('podknow.services.episode.RSSFeedParser.get_episodes')
    def test_get_recent_episodes_rss_error(self, mock_get_episodes):
        """Test recent episodes retrieval with RSS parsing error."""
        mock_get_episodes.side_effect = RSSParsingError("Feed parsing failed")
        
        with pytest.raises(EpisodeManagementError, match="Failed to get recent episodes"):
            self.service.get_recent_episodes(self.test_rss_url, days=30)