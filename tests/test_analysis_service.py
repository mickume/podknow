"""
Unit tests for analysis service.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from podknow.services.analysis import AnalysisService, ClaudeAPIClient
from podknow.models.analysis import AnalysisResult, SponsorSegment
from podknow.models.episode import EpisodeMetadata
from podknow.models.output import OutputDocument
from podknow.exceptions import AnalysisError, ClaudeAPIError, ConfigurationError


class TestClaudeAPIClient:
    """Test ClaudeAPIClient functionality."""
    
    def test_init_with_valid_api_key(self):
        """Test initializing client with valid API key."""
        client = ClaudeAPIClient("test-api-key")
        assert client.max_retries == 3
        assert client.retry_delay == 1.0
    
    def test_init_with_empty_api_key_raises_error(self):
        """Test that empty API key raises ConfigurationError."""
        with pytest.raises(ConfigurationError, match="Claude API key is required"):
            ClaudeAPIClient("")
    
    def test_init_with_none_api_key_raises_error(self):
        """Test that None API key raises ConfigurationError."""
        with pytest.raises(ConfigurationError, match="Claude API key is required"):
            ClaudeAPIClient(None)
    
    @patch('podknow.services.analysis.Anthropic')
    def test_send_message_success(self, mock_anthropic):
        """Test successful message sending."""
        # Mock the response
        mock_response = Mock()
        mock_response.content = [Mock(text="Test response")]
        
        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client
        
        client = ClaudeAPIClient("test-api-key")
        response = client.send_message("Test prompt")
        
        assert response == "Test response"
        mock_client.messages.create.assert_called_once()
    
    @patch('podknow.services.analysis.Anthropic')
    def test_send_message_with_system_prompt(self, mock_anthropic):
        """Test sending message with system prompt."""
        mock_response = Mock()
        mock_response.content = [Mock(text="Test response")]
        
        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client
        
        client = ClaudeAPIClient("test-api-key")
        response = client.send_message("Test prompt", system_prompt="System prompt")
        
        assert response == "Test response"
        call_args = mock_client.messages.create.call_args
        assert call_args[1]["system"] == "System prompt"
    
    @patch('podknow.services.analysis.Anthropic')
    def test_send_message_empty_response_raises_error(self, mock_anthropic):
        """Test that empty response raises ClaudeAPIError."""
        mock_response = Mock()
        mock_response.content = []
        
        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client
        
        client = ClaudeAPIClient("test-api-key")
        
        with pytest.raises(ClaudeAPIError, match="Empty response from Claude API"):
            client.send_message("Test prompt")
    
    @patch('podknow.services.analysis.Anthropic')
    @patch('time.sleep')
    def test_send_message_rate_limit_retry(self, mock_sleep, mock_anthropic):
        """Test retry logic for rate limit errors."""
        from anthropic import RateLimitError
        
        mock_client = Mock()
        # First call raises rate limit error, second succeeds
        mock_response = Mock()
        mock_response.content = [Mock(text="Success after retry")]
        
        mock_client.messages.create.side_effect = [
            RateLimitError("Rate limited", response=Mock(), body={}),
            mock_response
        ]
        mock_anthropic.return_value = mock_client
        
        client = ClaudeAPIClient("test-api-key", max_retries=1)
        response = client.send_message("Test prompt")
        
        assert response == "Success after retry"
        assert mock_client.messages.create.call_count == 2
        mock_sleep.assert_called_once()


class TestAnalysisService:
    """Test AnalysisService functionality."""
    
    @patch('podknow.services.analysis.ClaudeAPIClient')
    def test_init_with_api_key(self, mock_client_class):
        """Test initializing service with API key."""
        service = AnalysisService("test-api-key")
        mock_client_class.assert_called_once_with("test-api-key", model='claude-sonnet-4-20250514')
        assert service.prompts is not None
    
    @patch('podknow.services.analysis.ClaudeAPIClient')
    def test_init_with_custom_prompts(self, mock_client_class):
        """Test initializing service with custom prompts."""
        custom_prompts = {"summary": "Custom summary prompt"}
        service = AnalysisService("test-api-key", prompts=custom_prompts)
        assert service.prompts == custom_prompts
    
    def test_get_default_prompts(self):
        """Test that default prompts are properly structured."""
        with patch('podknow.services.analysis.ClaudeAPIClient'):
            service = AnalysisService("test-api-key")
            prompts = service._get_default_prompts()

            required_keys = ["summary", "topics", "keywords", "sponsor_detection"]
            for key in required_keys:
                assert key in prompts
                assert isinstance(prompts[key], str)
                assert len(prompts[key]) > 0
    
    @patch('podknow.services.analysis.ClaudeAPIClient')
    def test_generate_summary_success(self, mock_client_class):
        """Test successful summary generation."""
        mock_client = Mock()
        mock_client.send_message.return_value = "This is a test summary."
        mock_client_class.return_value = mock_client
        
        service = AnalysisService("test-api-key")
        summary = service.generate_summary("Test transcription")
        
        assert summary == "This is a test summary."
        mock_client.send_message.assert_called_once()
    
    @patch('podknow.services.analysis.ClaudeAPIClient')
    def test_generate_summary_empty_transcription_raises_error(self, mock_client_class):
        """Test that empty transcription raises AnalysisError."""
        service = AnalysisService("test-api-key")
        
        with pytest.raises(AnalysisError, match="Transcription text is required"):
            service.generate_summary("")
    
    @patch('podknow.services.analysis.ClaudeAPIClient')
    def test_extract_topics_success(self, mock_client_class):
        """Test successful topic extraction."""
        mock_client = Mock()
        mock_client.send_message.return_value = "Topic 1\nTopic 2\nTopic 3"
        mock_client_class.return_value = mock_client
        
        service = AnalysisService("test-api-key")
        topics = service.extract_topics("Test transcription")
        
        assert topics == ["Topic 1", "Topic 2", "Topic 3"]
    
    @patch('podknow.services.analysis.ClaudeAPIClient')
    def test_identify_keywords_success(self, mock_client_class):
        """Test successful keyword identification."""
        mock_client = Mock()
        mock_client.send_message.return_value = "keyword1, keyword2, keyword3"
        mock_client_class.return_value = mock_client
        
        service = AnalysisService("test-api-key")
        keywords = service.identify_keywords("Test transcription")
        
        assert keywords == ["keyword1", "keyword2", "keyword3"]
    
    @patch('podknow.services.analysis.ClaudeAPIClient')
    def test_detect_sponsor_content_success(self, mock_client_class):
        """Test successful sponsor content detection."""
        sponsor_response = json.dumps([
            {
                "start_text": "This episode is sponsored by",
                "end_text": "Back to the show",
                "confidence": 0.9
            }
        ])
        
        mock_client = Mock()
        mock_client.send_message.return_value = sponsor_response
        mock_client_class.return_value = mock_client
        
        service = AnalysisService("test-api-key")
        segments = service.detect_sponsor_content("Test transcription")
        
        assert len(segments) == 1
        assert segments[0].start_text == "This episode is sponsored by"
        assert segments[0].end_text == "Back to the show"
        assert segments[0].confidence == 0.9
    
    @patch('podknow.services.analysis.ClaudeAPIClient')
    def test_detect_sponsor_content_no_sponsors(self, mock_client_class):
        """Test sponsor detection when no sponsors found."""
        mock_client = Mock()
        mock_client.send_message.return_value = "[]"
        mock_client_class.return_value = mock_client
        
        service = AnalysisService("test-api-key")
        segments = service.detect_sponsor_content("Test transcription")
        
        assert segments == []
    
    @patch('podknow.services.analysis.ClaudeAPIClient')
    def test_detect_sponsor_content_invalid_json(self, mock_client_class):
        """Test sponsor detection with invalid JSON response."""
        mock_client = Mock()
        mock_client.send_message.return_value = "Invalid JSON response"
        mock_client_class.return_value = mock_client
        
        service = AnalysisService("test-api-key")
        segments = service.detect_sponsor_content("Test transcription")
        
        # Should return empty list for invalid JSON
        assert segments == []
    
    @patch('podknow.services.analysis.ClaudeAPIClient')
    def test_analyze_transcription_success(self, mock_client_class):
        """Test complete transcription analysis."""
        mock_client = Mock()
        mock_client.send_message.side_effect = [
            "Test summary",  # Summary
            "Topic 1\nTopic 2",  # Topics
            "keyword1, keyword2",  # Keywords
            "[]"  # No sponsors
        ]
        mock_client_class.return_value = mock_client
        
        service = AnalysisService("test-api-key")
        result = service.analyze_transcription("Test transcription")
        
        assert isinstance(result, AnalysisResult)
        assert result.summary == "Test summary"
        assert result.topics == ["Topic 1", "Topic 2"]
        assert result.keywords == ["keyword1", "keyword2"]
        assert result.sponsor_segments == []
    
    @patch('podknow.services.analysis.ClaudeAPIClient')
    def test_analyze_transcription_empty_input_raises_error(self, mock_client_class):
        """Test that empty transcription raises AnalysisError."""
        service = AnalysisService("test-api-key")
        
        with pytest.raises(AnalysisError, match="Transcription text is required"):
            service.analyze_transcription("")
    
    @patch('podknow.services.analysis.ClaudeAPIClient')
    def test_generate_markdown_output_success(self, mock_client_class):
        """Test successful markdown output generation."""
        service = AnalysisService("test-api-key")
        
        # Create test data
        metadata = EpisodeMetadata(
            podcast_title="Test Podcast",
            episode_title="Test Episode",
            episode_number=1,
            publication_date=datetime(2024, 1, 15),
            duration="30:00",
            description="Test description",
            audio_url="https://example.com/audio.mp3"
        )
        
        analysis = AnalysisResult(
            summary="This is a test summary.",
            topics=["Topic 1", "Topic 2"],
            keywords=["keyword1", "keyword2"],
            sponsor_segments=[]
        )
        
        output_doc = OutputDocument(
            metadata=metadata,
            transcription="This is the transcription text.",
            analysis=analysis,
            processing_timestamp=datetime(2024, 1, 16, 10, 30, 0)
        )
        
        markdown = service.generate_markdown_output(output_doc)
        
        # Check that markdown contains expected sections
        assert "---" in markdown  # Frontmatter
        assert "podcast_title: \"Test Podcast\"" in markdown
        assert "# Episode Summary" in markdown
        assert "## Topics Covered" in markdown
        assert "## Transcription" in markdown
        assert "This is a test summary." in markdown
        assert "- Topic 1" in markdown
        assert "This is the transcription text." in markdown
    
    @patch('podknow.services.analysis.ClaudeAPIClient')
    def test_generate_markdown_output_with_sponsors(self, mock_client_class):
        """Test markdown output generation with sponsor content."""
        service = AnalysisService("test-api-key")
        
        # Create test data with sponsor segments
        metadata = EpisodeMetadata(
            podcast_title="Test Podcast",
            episode_title="Test Episode",
            episode_number=1,
            publication_date=datetime(2024, 1, 15),
            duration="30:00",
            description="Test description",
            audio_url="https://example.com/audio.mp3"
        )
        
        sponsor_segment = SponsorSegment(
            start_text="This episode is sponsored",
            end_text="back to the show",
            confidence=0.9
        )
        
        analysis = AnalysisResult(
            summary="This is a test summary.",
            topics=["Topic 1"],
            keywords=["keyword1"],
            sponsor_segments=[sponsor_segment]
        )
        
        transcription = "Welcome to the show. This episode is sponsored by our friends back to the show. Thanks for listening."
        
        output_doc = OutputDocument(
            metadata=metadata,
            transcription=transcription,
            analysis=analysis,
            processing_timestamp=datetime(2024, 1, 16, 10, 30, 0)
        )
        
        markdown = service.generate_markdown_output(output_doc)

        # Check that sponsor markers are present
        assert "**[SPONSOR START - 90%]**" in markdown
        assert "**[SPONSOR END]**" in markdown
    
    @patch('podknow.services.analysis.ClaudeAPIClient')
    def test_generate_frontmatter(self, mock_client_class):
        """Test frontmatter generation."""
        service = AnalysisService("test-api-key")
        
        metadata = EpisodeMetadata(
            podcast_title="Test Podcast",
            episode_title="Test Episode",
            episode_number=1,
            publication_date=datetime(2024, 1, 15),
            duration="30:00",
            description="Test description",
            audio_url="https://example.com/audio.mp3"
        )
        
        analysis = AnalysisResult(
            summary="Test summary",
            topics=["Topic 1"],
            keywords=["keyword1", "keyword2"],
            sponsor_segments=[]
        )
        
        output_doc = OutputDocument(
            metadata=metadata,
            transcription="Test transcription",
            analysis=analysis,
            processing_timestamp=datetime(2024, 1, 16, 10, 30, 0)
        )
        
        frontmatter = service._generate_frontmatter(output_doc)
        
        assert "podcast_title: \"Test Podcast\"" in frontmatter
        assert "episode_title: \"Test Episode\"" in frontmatter
        assert "episode_number: 1" in frontmatter
        assert "publication_date: \"2024-01-15\"" in frontmatter
        assert "duration: \"30:00\"" in frontmatter
        assert "transcribed_at: \"2024-01-16T10:30:00Z\"" in frontmatter
        assert "keywords: [\"keyword1\", \"keyword2\"]" in frontmatter
        assert "sponsor_segments_detected: 0" in frontmatter