"""
Unit tests for RSS feed parsing functionality.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from podknow.services.rss import RSSFeedParser, RSSParsingError
from podknow.models.podcast import PodcastMetadata
from podknow.models.episode import Episode


class TestRSSFeedParser:
    """Test RSSFeedParser functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = RSSFeedParser()
        self.test_rss_url = "https://example.com/feed.xml"
    
    def test_init(self):
        """Test RSSFeedParser initialization."""
        parser = RSSFeedParser()
        assert parser is not None
    
    def test_parse_feed_invalid_url(self):
        """Test parse_feed with invalid URL."""
        with pytest.raises(RSSParsingError, match="RSS URL must be a non-empty string"):
            self.parser.parse_feed("")
        
        with pytest.raises(RSSParsingError, match="RSS URL must be a non-empty string"):
            self.parser.parse_feed(None)
        
        with pytest.raises(RSSParsingError, match="Invalid RSS URL format"):
            self.parser.parse_feed("not-a-url")
    
    @patch('podknow.services.rss.feedparser.parse')
    def test_parse_feed_success(self, mock_parse):
        """Test successful RSS feed parsing."""
        # Mock feedparser response
        mock_feed = Mock()
        mock_feed.bozo = False
        mock_feed.feed = Mock()
        mock_feed.feed.title = "Test Podcast"
        mock_feed.feed.author = "Test Author"
        mock_feed.feed.description = "Test Description"
        mock_feed.feed.updated_parsed = (2024, 1, 15, 10, 30, 0, 0, 0, 0)
        mock_feed.entries = [Mock(), Mock()]  # 2 episodes
        
        mock_parse.return_value = mock_feed
        
        result = self.parser.parse_feed(self.test_rss_url)
        
        assert isinstance(result, PodcastMetadata)
        assert result.title == "Test Podcast"
        assert result.author == "Test Author"
        assert result.description == "Test Description"
        assert result.rss_url == self.test_rss_url
        assert result.episode_count == 2
        assert result.last_updated == datetime(2024, 1, 15, 10, 30, 0)
    
    @patch('podknow.services.rss.feedparser.parse')
    def test_parse_feed_bozo_error(self, mock_parse):
        """Test RSS feed parsing with bozo error."""
        mock_feed = Mock()
        mock_feed.bozo = True
        mock_feed.bozo_exception = Exception("Feed parsing error")
        
        mock_parse.return_value = mock_feed
        
        with pytest.raises(RSSParsingError, match="Feed parsing error"):
            self.parser.parse_feed(self.test_rss_url)
    
    @patch('podknow.services.rss.feedparser.parse')
    def test_parse_feed_missing_feed_element(self, mock_parse):
        """Test RSS feed parsing with missing feed element."""
        mock_feed = Mock()
        mock_feed.bozo = False
        mock_feed.feed = None
        
        mock_parse.return_value = mock_feed
        
        with pytest.raises(RSSParsingError, match="Invalid RSS feed: missing feed element"):
            self.parser.parse_feed(self.test_rss_url)
    
    @patch('podknow.services.rss.feedparser.parse')
    def test_parse_feed_missing_title(self, mock_parse):
        """Test RSS feed parsing with missing title."""
        mock_feed = Mock()
        mock_feed.bozo = False
        mock_feed.feed = Mock()
        mock_feed.feed.title = ""
        mock_feed.entries = []
        
        mock_parse.return_value = mock_feed
        
        with pytest.raises(RSSParsingError, match="RSS feed missing required title"):
            self.parser.parse_feed(self.test_rss_url)
    
    @patch('podknow.services.rss.feedparser.parse')
    def test_parse_feed_fallback_author(self, mock_parse):
        """Test RSS feed parsing with fallback author fields."""
        mock_feed = Mock()
        mock_feed.bozo = False
        mock_feed.feed = Mock()
        mock_feed.feed.title = "Test Podcast"
        mock_feed.feed.author = ""
        mock_feed.feed.itunes_author = "iTunes Author"
        mock_feed.feed.description = "Test Description"
        mock_feed.entries = []
        
        mock_parse.return_value = mock_feed
        
        result = self.parser.parse_feed(self.test_rss_url)
        assert result.author == "iTunes Author"
    
    @patch('podknow.services.rss.feedparser.parse')
    def test_parse_feed_unknown_author(self, mock_parse):
        """Test RSS feed parsing with no author information."""
        mock_feed = Mock()
        mock_feed.bozo = False
        mock_feed.feed = Mock()
        mock_feed.feed.title = "Test Podcast"
        mock_feed.feed.description = "Test Description"
        mock_feed.entries = []
        
        # Remove all author-related attributes
        for attr in ['author', 'itunes_author', 'managingEditor']:
            if hasattr(mock_feed.feed, attr):
                delattr(mock_feed.feed, attr)
        
        mock_parse.return_value = mock_feed
        
        result = self.parser.parse_feed(self.test_rss_url)
        assert result.author == "Unknown Author"
    
    def test_get_episodes_invalid_url(self):
        """Test get_episodes with invalid URL."""
        with pytest.raises(RSSParsingError, match="RSS URL must be a non-empty string"):
            self.parser.get_episodes("")
    
    @patch('podknow.services.rss.feedparser.parse')
    def test_get_episodes_empty_feed(self, mock_parse):
        """Test get_episodes with empty feed."""
        mock_feed = Mock()
        mock_feed.bozo = False
        mock_feed.entries = []
        
        mock_parse.return_value = mock_feed
        
        result = self.parser.get_episodes(self.test_rss_url)
        assert result == []
    
    @patch('podknow.services.rss.feedparser.parse')
    def test_get_episodes_success(self, mock_parse):
        """Test successful episode extraction."""
        # Create mock entries
        entry1 = Mock()
        entry1.title = "Episode 1"
        entry1.description = "First episode"
        entry1.published_parsed = (2024, 1, 15, 10, 0, 0, 0, 0, 0)
        entry1.itunes_duration = "30:00"
        entry1.enclosures = [Mock()]
        entry1.enclosures[0].type = "audio/mpeg"
        entry1.enclosures[0].href = "https://example.com/episode1.mp3"
        
        entry2 = Mock()
        entry2.title = "Episode 2"
        entry2.description = "Second episode"
        entry2.published_parsed = (2024, 1, 16, 10, 0, 0, 0, 0, 0)
        entry2.itunes_duration = "25:00"
        entry2.enclosures = [Mock()]
        entry2.enclosures[0].type = "audio/mpeg"
        entry2.enclosures[0].href = "https://example.com/episode2.mp3"
        
        mock_feed = Mock()
        mock_feed.bozo = False
        mock_feed.entries = [entry1, entry2]
        
        mock_parse.return_value = mock_feed
        
        result = self.parser.get_episodes(self.test_rss_url)
        
        assert len(result) == 2
        assert all(isinstance(ep, Episode) for ep in result)
        
        # Check sorting (newest first)
        assert result[0].title == "Episode 2"
        assert result[1].title == "Episode 1"
        
        # Check episode details
        assert result[0].duration == "25:00"
        assert result[0].audio_url == "https://example.com/episode2.mp3"
    
    @patch('podknow.services.rss.feedparser.parse')
    def test_get_episodes_with_count_limit(self, mock_parse):
        """Test episode extraction with count limit."""
        # Create 3 mock entries
        entries = []
        for i in range(3):
            entry = Mock()
            entry.title = f"Episode {i+1}"
            entry.description = f"Episode {i+1} description"
            entry.published_parsed = (2024, 1, 15+i, 10, 0, 0, 0, 0, 0)
            entry.itunes_duration = "30:00"
            entry.enclosures = [Mock()]
            entry.enclosures[0].type = "audio/mpeg"
            entry.enclosures[0].href = f"https://example.com/episode{i+1}.mp3"
            entries.append(entry)
        
        mock_feed = Mock()
        mock_feed.bozo = False
        mock_feed.entries = entries
        
        mock_parse.return_value = mock_feed
        
        result = self.parser.get_episodes(self.test_rss_url, count=2)
        
        assert len(result) == 2
        # Should get the 2 newest episodes
        assert result[0].title == "Episode 3"
        assert result[1].title == "Episode 2"
    
    def test_extract_audio_url_from_enclosures(self):
        """Test audio URL extraction from enclosures."""
        entry = Mock()
        entry.enclosures = [Mock()]
        entry.enclosures[0].type = "audio/mpeg"
        entry.enclosures[0].href = "https://example.com/audio.mp3"
        
        result = self.parser._extract_audio_url(entry)
        assert result == "https://example.com/audio.mp3"
    
    def test_extract_audio_url_from_links(self):
        """Test audio URL extraction from links."""
        entry = Mock()
        entry.enclosures = []
        entry.links = [Mock()]
        entry.links[0].type = "audio/mpeg"
        entry.links[0].href = "https://example.com/audio.mp3"
        
        result = self.parser._extract_audio_url(entry)
        assert result == "https://example.com/audio.mp3"
    
    def test_extract_audio_url_from_direct_link(self):
        """Test audio URL extraction from direct link."""
        entry = Mock()
        entry.enclosures = []
        entry.links = []
        entry.link = "https://example.com/audio.mp3"
        
        result = self.parser._extract_audio_url(entry)
        assert result == "https://example.com/audio.mp3"
    
    def test_extract_audio_url_no_audio(self):
        """Test audio URL extraction when no audio found."""
        entry = Mock()
        entry.enclosures = []
        entry.links = []
        entry.link = "https://example.com/webpage.html"
        
        result = self.parser._extract_audio_url(entry)
        assert result is None
    
    def test_extract_publication_date_from_published(self):
        """Test publication date extraction from published_parsed."""
        entry = Mock()
        entry.published_parsed = (2024, 1, 15, 10, 30, 0, 0, 0, 0)
        
        result = self.parser._extract_publication_date(entry)
        assert result == datetime(2024, 1, 15, 10, 30, 0)
    
    def test_extract_publication_date_from_updated(self):
        """Test publication date extraction from updated_parsed."""
        entry = Mock()
        entry.published_parsed = None
        entry.updated_parsed = (2024, 1, 15, 10, 30, 0, 0, 0, 0)
        
        result = self.parser._extract_publication_date(entry)
        assert result == datetime(2024, 1, 15, 10, 30, 0)
    
    def test_extract_publication_date_fallback(self):
        """Test publication date extraction fallback to current time."""
        entry = Mock()
        entry.published_parsed = None
        entry.updated_parsed = None
        
        result = self.parser._extract_publication_date(entry)
        # Should be close to current time
        assert isinstance(result, datetime)
        assert (datetime.now() - result).total_seconds() < 1
    
    def test_extract_duration_itunes(self):
        """Test duration extraction from iTunes field."""
        entry = Mock()
        entry.itunes_duration = "30:45"
        
        result = self.parser._extract_duration(entry)
        assert result == "30:45"
    
    def test_extract_duration_fallback(self):
        """Test duration extraction fallback."""
        entry = Mock()
        entry.duration = "25:30"
        
        # Remove itunes_duration
        if hasattr(entry, 'itunes_duration'):
            delattr(entry, 'itunes_duration')
        
        result = self.parser._extract_duration(entry)
        assert result == "25:30"
    
    def test_extract_duration_unknown(self):
        """Test duration extraction when no duration found."""
        entry = Mock()
        
        # Remove all duration fields
        for attr in ['itunes_duration', 'duration', 'length']:
            if hasattr(entry, attr):
                delattr(entry, attr)
        
        result = self.parser._extract_duration(entry)
        assert result == "Unknown"
    
    def test_generate_episode_id(self):
        """Test episode ID generation."""
        title = "Test Episode"
        audio_url = "https://example.com/audio.mp3"
        rss_url = "https://example.com/feed.xml"
        
        result = self.parser._generate_episode_id(title, audio_url, rss_url)
        
        assert isinstance(result, str)
        assert len(result) == 12  # First 12 characters of MD5 hash
        
        # Same inputs should generate same ID
        result2 = self.parser._generate_episode_id(title, audio_url, rss_url)
        assert result == result2
        
        # Different inputs should generate different ID
        result3 = self.parser._generate_episode_id("Different Title", audio_url, rss_url)
        assert result != result3
    
    @patch('podknow.services.rss.feedparser.parse')
    def test_parse_episode_entry_missing_title(self, mock_parse):
        """Test parsing episode entry with missing title."""
        entry = Mock()
        entry.title = ""
        
        result = self.parser._parse_episode_entry(entry, self.test_rss_url)
        assert result is None
    
    @patch('podknow.services.rss.feedparser.parse')
    def test_parse_episode_entry_missing_audio(self, mock_parse):
        """Test parsing episode entry with missing audio URL."""
        entry = Mock()
        entry.title = "Test Episode"
        entry.description = "Test description"
        entry.enclosures = []
        entry.links = []
        entry.link = "https://example.com/webpage.html"
        
        result = self.parser._parse_episode_entry(entry, self.test_rss_url)
        assert result is None
    
    @patch('podknow.services.rss.feedparser.parse')
    def test_get_episodes_skip_invalid_entries(self, mock_parse):
        """Test that invalid episode entries are skipped."""
        # Create mix of valid and invalid entries
        valid_entry = Mock()
        valid_entry.title = "Valid Episode"
        valid_entry.description = "Valid description"
        valid_entry.published_parsed = (2024, 1, 15, 10, 0, 0, 0, 0, 0)
        valid_entry.itunes_duration = "30:00"
        valid_entry.enclosures = [Mock()]
        valid_entry.enclosures[0].type = "audio/mpeg"
        valid_entry.enclosures[0].href = "https://example.com/valid.mp3"
        
        invalid_entry = Mock()
        invalid_entry.title = ""  # Missing title
        
        mock_feed = Mock()
        mock_feed.bozo = False
        mock_feed.entries = [valid_entry, invalid_entry]
        
        mock_parse.return_value = mock_feed
        
        result = self.parser.get_episodes(self.test_rss_url)
        
        # Should only return the valid episode
        assert len(result) == 1
        assert result[0].title == "Valid Episode"


class TestRSSParsingEdgeCases:
    """Test edge cases and error conditions for RSS parsing."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = RSSFeedParser()
    
    @patch('podknow.services.rss.feedparser.parse')
    def test_character_encoding_override(self, mock_parse):
        """Test handling of character encoding override."""
        from feedparser import CharacterEncodingOverride
        
        # Mock successful second parse
        mock_feed = Mock()
        mock_feed.bozo = False
        mock_feed.feed = Mock()
        mock_feed.feed.title = "Test Podcast"
        mock_feed.feed.author = "Test Author"
        mock_feed.feed.description = "Test Description"
        mock_feed.entries = []
        
        # First call raises CharacterEncodingOverride, second call succeeds
        mock_parse.side_effect = [
            CharacterEncodingOverride("Encoding override"),
            mock_feed
        ]
        
        result = self.parser.parse_feed("https://example.com/feed.xml")
        
        assert isinstance(result, PodcastMetadata)
        assert result.title == "Test Podcast"
        assert mock_parse.call_count == 2
    
    @patch('podknow.services.rss.feedparser.parse')
    def test_malformed_date_handling(self, mock_parse):
        """Test handling of malformed publication dates."""
        entry = Mock()
        entry.title = "Test Episode"
        entry.description = "Test description"
        entry.published_parsed = (2024, 13, 32)  # Invalid date
        entry.itunes_duration = "30:00"
        entry.enclosures = [Mock()]
        entry.enclosures[0].type = "audio/mpeg"
        entry.enclosures[0].href = "https://example.com/audio.mp3"
        
        mock_feed = Mock()
        mock_feed.bozo = False
        mock_feed.entries = [entry]
        
        mock_parse.return_value = mock_feed
        
        result = self.parser.get_episodes("https://example.com/feed.xml")
        
        # Should handle malformed date gracefully
        assert len(result) == 1
        assert isinstance(result[0].publication_date, datetime)
    
    @patch('podknow.services.rss.feedparser.parse')
    def test_multiple_audio_enclosures(self, mock_parse):
        """Test handling of multiple audio enclosures."""
        entry = Mock()
        entry.title = "Test Episode"
        entry.description = "Test description"
        entry.published_parsed = (2024, 1, 15, 10, 0, 0, 0, 0, 0)
        entry.itunes_duration = "30:00"
        
        # Multiple enclosures with different types
        enclosure1 = Mock()
        enclosure1.type = "text/html"
        enclosure1.href = "https://example.com/webpage.html"
        
        enclosure2 = Mock()
        enclosure2.type = "audio/mpeg"
        enclosure2.href = "https://example.com/audio.mp3"
        
        entry.enclosures = [enclosure1, enclosure2]
        
        mock_feed = Mock()
        mock_feed.bozo = False
        mock_feed.entries = [entry]
        
        mock_parse.return_value = mock_feed
        
        result = self.parser.get_episodes("https://example.com/feed.xml")
        
        assert len(result) == 1
        assert result[0].audio_url == "https://example.com/audio.mp3"