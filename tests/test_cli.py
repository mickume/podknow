"""
Tests for CLI interface and command handling.
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from click.testing import CliRunner

from podknow.cli.main import cli
from podknow.models.podcast import PodcastResult, PodcastMetadata
from podknow.models.episode import Episode, EpisodeMetadata
from podknow.models.analysis import AnalysisResult, SponsorSegment
from podknow.models.transcription import TranscriptionResult, TranscriptionSegment
from podknow.exceptions import NetworkError, EpisodeManagementError, TranscriptionError, AnalysisError
from datetime import datetime


class TestCLIFramework:
    """Test base CLI framework functionality."""
    
    def test_cli_help(self):
        """Test CLI help output."""
        runner = CliRunner()
        result = runner.invoke(cli, ['--help'])
        
        assert result.exit_code == 0
        assert 'PodKnow - Command-line podcast transcription and analysis tool' in result.output
        assert 'search' in result.output
        assert 'list' in result.output
        assert 'transcribe' in result.output
        assert 'analyze' in result.output
    
    def test_cli_version(self):
        """Test CLI version output."""
        runner = CliRunner()
        result = runner.invoke(cli, ['--version'])
        
        assert result.exit_code == 0
        assert '0.1.0' in result.output
    
    def test_cli_verbose_flag(self):
        """Test verbose flag functionality."""
        runner = CliRunner()
        result = runner.invoke(cli, ['--verbose', '--help'])
        
        assert result.exit_code == 0
        # Verbose flag should not affect help output
        assert 'PodKnow - Command-line podcast transcription and analysis tool' in result.output


class TestSearchCommand:
    """Test search command functionality."""
    
    @patch('podknow.services.discovery.PodcastDiscoveryService')
    def test_search_success(self, mock_discovery_service):
        """Test successful podcast search."""
        # Mock search results
        mock_results = [
            PodcastResult(
                title="Test Podcast 1",
                author="Test Author 1",
                rss_url="https://example.com/feed1.xml",
                platform="iTunes",
                description="Test description 1"
            ),
            PodcastResult(
                title="Test Podcast 2",
                author="Test Author 2",
                rss_url="https://example.com/feed2.xml",
                platform="Spotify",
                description="Test description 2"
            )
        ]
        
        mock_service = Mock()
        mock_service.get_combined_results.return_value = mock_results
        mock_discovery_service.return_value = mock_service
        
        runner = CliRunner()
        result = runner.invoke(cli, ['search', 'test keywords'])
        
        assert result.exit_code == 0
        assert 'Found 2 podcast(s)' in result.output
        assert 'Test Podcast 1' in result.output
        assert 'Test Author 1' in result.output
        assert 'iTunes' in result.output
        assert 'RSS Feed: https://example.com/feed1.xml' in result.output
        
        # Verify service was called correctly
        mock_service.get_combined_results.assert_called_once_with('test keywords')
    
    @patch('podknow.services.discovery.PodcastDiscoveryService')
    def test_search_platform_filter(self, mock_discovery_service):
        """Test search with platform filter."""
        mock_results = [
            PodcastResult(
                title="iTunes Podcast",
                author="iTunes Author",
                rss_url="https://example.com/itunes.xml",
                platform="iTunes",
                description="iTunes description"
            )
        ]
        
        mock_service = Mock()
        mock_service.search_itunes.return_value = mock_results
        mock_discovery_service.return_value = mock_service
        
        runner = CliRunner()
        result = runner.invoke(cli, ['search', 'test', '--platform', 'itunes'])
        
        assert result.exit_code == 0
        assert 'iTunes Podcast' in result.output
        mock_service.search_itunes.assert_called_once_with('test')
    
    @patch('podknow.services.discovery.PodcastDiscoveryService')
    def test_search_no_results(self, mock_discovery_service):
        """Test search with no results."""
        mock_service = Mock()
        mock_service.get_combined_results.return_value = []
        mock_discovery_service.return_value = mock_service
        
        runner = CliRunner()
        result = runner.invoke(cli, ['search', 'nonexistent'])
        
        assert result.exit_code == 0
        assert 'No podcasts found' in result.output
        assert 'Tips:' in result.output
    
    @patch('podknow.services.discovery.PodcastDiscoveryService')
    def test_search_network_error(self, mock_discovery_service):
        """Test search with network error."""
        mock_service = Mock()
        mock_service.get_combined_results.side_effect = NetworkError("Connection failed")
        mock_discovery_service.return_value = mock_service
        
        runner = CliRunner()
        result = runner.invoke(cli, ['search', 'test'])
        
        assert result.exit_code == 1
        assert 'Search failed' in result.output
        assert 'Connection failed' in result.output
    
    def test_search_empty_keywords(self):
        """Test search with empty keywords."""
        runner = CliRunner()
        result = runner.invoke(cli, ['search', ''])
        
        assert result.exit_code == 2  # Click parameter error
        assert 'Keywords cannot be empty' in result.output


class TestListCommand:
    """Test list command functionality."""
    
    @patch('podknow.services.episode.EpisodeListingService')
    def test_list_success(self, mock_episode_service):
        """Test successful episode listing."""
        # Mock podcast info
        mock_podcast = PodcastMetadata(
            title="Test Podcast",
            author="Test Author",
            description="Test description",
            rss_url="https://example.com/feed.xml",
            episode_count=100,
            last_updated=datetime(2024, 1, 15, 10, 30)
        )
        
        # Mock episodes
        mock_episodes = [
            Episode(
                id="ep001",
                title="Episode 1",
                description="First episode",
                audio_url="https://example.com/ep1.mp3",
                publication_date=datetime(2024, 1, 10),
                duration="30:00"
            ),
            Episode(
                id="ep002",
                title="Episode 2",
                description="Second episode",
                audio_url="https://example.com/ep2.mp3",
                publication_date=datetime(2024, 1, 5),
                duration="25:30"
            )
        ]
        
        mock_service = Mock()
        mock_service.get_podcast_info.return_value = mock_podcast
        mock_service.list_episodes.return_value = mock_episodes
        mock_episode_service.return_value = mock_service
        
        runner = CliRunner()
        result = runner.invoke(cli, ['list', 'https://example.com/feed.xml'])
        
        assert result.exit_code == 0
        assert 'Test Podcast' in result.output
        assert 'Test Author' in result.output
        assert 'Episode 1' in result.output
        assert '[ep001]' in result.output
        assert '2024-01-10' in result.output
        assert '30:00' in result.output
        
        # Verify service calls
        mock_service.get_podcast_info.assert_called_once_with('https://example.com/feed.xml')
        mock_service.list_episodes.assert_called_once_with('https://example.com/feed.xml', count=10)
    
    @patch('podknow.services.episode.EpisodeListingService')
    def test_list_with_descriptions(self, mock_episode_service):
        """Test episode listing with descriptions."""
        mock_podcast = PodcastMetadata(
            title="Test Podcast",
            author="Test Author",
            description="Test description",
            rss_url="https://example.com/feed.xml",
            episode_count=10,
            last_updated=datetime.now()
        )
        
        mock_episodes = [
            Episode(
                id="ep001",
                title="Episode 1",
                description="This is a detailed description of the first episode",
                audio_url="https://example.com/ep1.mp3",
                publication_date=datetime(2024, 1, 10),
                duration="30:00"
            )
        ]
        
        mock_service = Mock()
        mock_service.get_podcast_info.return_value = mock_podcast
        mock_service.list_episodes.return_value = mock_episodes
        mock_episode_service.return_value = mock_service
        
        runner = CliRunner()
        result = runner.invoke(cli, ['list', 'https://example.com/feed.xml', '--show-descriptions'])
        
        assert result.exit_code == 0
        assert 'This is a detailed description' in result.output
    
    def test_list_episode_management_error(self):
        """Test list command with episode management error."""
        with patch('podknow.services.episode.EpisodeListingService') as mock_episode_service:
            mock_service = Mock()
            mock_service.get_podcast_info.side_effect = EpisodeManagementError("RSS parsing failed")
            mock_episode_service.return_value = mock_service
            
            runner = CliRunner()
            result = runner.invoke(cli, ['list', 'https://invalid.com/feed.xml'])
            
            assert result.exit_code == 1
            # The error should be caught and handled appropriately
            assert 'An unexpected error occurred while listing episodes' in result.output or 'Failed to fetch podcast info' in result.output
    
    def test_list_invalid_url(self):
        """Test list command with invalid URL."""
        runner = CliRunner()
        result = runner.invoke(cli, ['list', 'not-a-url'])
        
        assert result.exit_code == 2
        assert 'RSS URL must start with http://' in result.output


class TestTranscribeCommand:
    """Test transcribe command functionality."""
    
    @patch('podknow.services.episode.EpisodeListingService')
    @patch('podknow.services.transcription.TranscriptionService')
    @patch('podknow.services.analysis.AnalysisService')
    def test_transcribe_success_with_analysis(self, mock_analysis_service, mock_transcription_service, mock_episode_service):
        """Test successful transcription with analysis."""
        # Mock episode finding
        mock_episode = Episode(
            id="ep001",
            title="Test Episode",
            description="Test description",
            audio_url="https://example.com/audio.mp3",
            publication_date=datetime(2024, 1, 10),
            duration="30:00"
        )
        
        mock_podcast = PodcastMetadata(
            title="Test Podcast",
            author="Test Author",
            description="Test podcast",
            rss_url="https://example.com/feed.xml",
            episode_count=10,
            last_updated=datetime.now()
        )
        
        mock_ep_service = Mock()
        mock_ep_service.find_episode_by_id.return_value = mock_episode
        mock_ep_service.get_podcast_info.return_value = mock_podcast
        mock_episode_service.return_value = mock_ep_service
        
        # Mock transcription
        mock_transcription_result = TranscriptionResult(
            text="This is the transcribed text.",
            segments=[
                TranscriptionSegment(
                    start_time=0.0,
                    end_time=5.0,
                    text="This is the transcribed text.",
                    is_paragraph_start=True
                )
            ],
            language="en",
            confidence=0.95
        )
        
        mock_trans_service = Mock()
        mock_trans_service.download_audio.return_value = "/tmp/audio.mp3"
        mock_trans_service.detect_language.return_value = "en"
        mock_trans_service.transcribe_audio.return_value = mock_transcription_result
        mock_trans_service._generate_filename.return_value = "test_episode.md"
        mock_transcription_service.return_value = mock_trans_service
        
        # Mock analysis
        mock_analysis_result = AnalysisResult(
            summary="This is a test episode summary.",
            topics=["Topic 1", "Topic 2"],
            keywords=["keyword1", "keyword2"],
            sponsor_segments=[]
        )
        
        mock_anal_service = Mock()
        mock_anal_service.analyze_transcription.return_value = mock_analysis_result
        mock_anal_service.generate_markdown_output.return_value = "# Test Output"
        mock_analysis_service.return_value = mock_anal_service
        
        # Mock file operations
        with patch('builtins.open', create=True) as mock_open:
            with patch('os.makedirs'):
                with patch('os.path.expanduser', return_value="/home/user/Documents/PodKnow"):
                    runner = CliRunner()
                    result = runner.invoke(cli, [
                        'transcribe', 'ep001',
                        '--rss-url', 'https://example.com/feed.xml',
                        '--claude-api-key', 'test-key'
                    ])
        
        assert result.exit_code == 0
        assert 'Transcription completed successfully' in result.output
        assert 'Confidence: 95.0%' in result.output
        
        # Verify service calls
        mock_ep_service.find_episode_by_id.assert_called_once_with('https://example.com/feed.xml', 'ep001')
        mock_trans_service.download_audio.assert_called_once()
        mock_trans_service.detect_language.assert_called_once()
        mock_trans_service.transcribe_audio.assert_called_once()
        mock_anal_service.analyze_transcription.assert_called_once()
    
    @patch('podknow.services.episode.EpisodeListingService')
    def test_transcribe_episode_not_found(self, mock_episode_service):
        """Test transcribe command when episode is not found."""
        mock_service = Mock()
        mock_service.find_episode_by_id.return_value = None
        mock_episode_service.return_value = mock_service
        
        runner = CliRunner()
        result = runner.invoke(cli, [
            'transcribe', 'nonexistent',
            '--rss-url', 'https://example.com/feed.xml',
            '--claude-api-key', 'test-key'
        ])
        
        assert result.exit_code == 1
        assert 'Episode with ID \'nonexistent\' not found' in result.output
    
    def test_transcribe_missing_claude_key(self):
        """Test transcribe command without Claude API key."""
        runner = CliRunner()
        result = runner.invoke(cli, [
            'transcribe', 'ep001',
            '--rss-url', 'https://example.com/feed.xml'
        ])
        
        assert result.exit_code == 2
        assert 'Claude API key is required' in result.output
    
    @patch('podknow.services.episode.EpisodeListingService')
    @patch('podknow.services.transcription.TranscriptionService')
    def test_transcribe_skip_analysis(self, mock_transcription_service, mock_episode_service):
        """Test transcribe command with skip analysis flag."""
        # Mock episode finding
        mock_episode = Episode(
            id="ep001",
            title="Test Episode",
            description="Test description",
            audio_url="https://example.com/audio.mp3",
            publication_date=datetime(2024, 1, 10),
            duration="30:00"
        )
        
        mock_podcast = PodcastMetadata(
            title="Test Podcast",
            author="Test Author",
            description="Test podcast",
            rss_url="https://example.com/feed.xml",
            episode_count=10,
            last_updated=datetime.now()
        )
        
        mock_ep_service = Mock()
        mock_ep_service.find_episode_by_id.return_value = mock_episode
        mock_ep_service.get_podcast_info.return_value = mock_podcast
        mock_episode_service.return_value = mock_ep_service
        
        # Mock transcription
        mock_transcription_result = TranscriptionResult(
            text="This is the transcribed text.",
            segments=[],
            language="en",
            confidence=0.95
        )
        
        mock_trans_service = Mock()
        mock_trans_service.download_audio.return_value = "/tmp/audio.mp3"
        mock_trans_service.detect_language.return_value = "en"
        mock_trans_service.transcribe_audio.return_value = mock_transcription_result
        mock_trans_service.generate_markdown_output.return_value = "/output/file.md"
        mock_transcription_service.return_value = mock_trans_service
        
        runner = CliRunner()
        result = runner.invoke(cli, [
            'transcribe', 'ep001',
            '--rss-url', 'https://example.com/feed.xml',
            '--skip-analysis'
        ])
        
        assert result.exit_code == 0
        assert 'Transcription completed successfully' in result.output
        
        # Verify analysis was skipped
        mock_trans_service.generate_markdown_output.assert_called_once()


class TestAnalyzeCommand:
    """Test analyze command functionality."""
    
    @patch('podknow.services.analysis.AnalysisService')
    def test_analyze_success(self, mock_analysis_service):
        """Test successful analysis of transcription file."""
        # Mock analysis result
        mock_analysis_result = AnalysisResult(
            summary="This is a test summary.",
            topics=["Topic 1", "Topic 2"],
            keywords=["keyword1", "keyword2"],
            sponsor_segments=[
                SponsorSegment(
                    start_text="This episode is sponsored",
                    end_text="back to the show",
                    confidence=0.9
                )
            ]
        )
        
        mock_service = Mock()
        mock_service.analyze_transcription.return_value = mock_analysis_result
        mock_service._generate_transcription_section.return_value = "Transcription with sponsor marks"
        mock_analysis_service.return_value = mock_service
        
        # Create temporary test file
        test_content = """---
podcast_title: "Test Podcast"
episode_title: "Test Episode"
publication_date: "2024-01-10"
---

# Test Episode

This is the transcription text.
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(test_content)
            temp_file = f.name
        
        try:
            with patch('builtins.open', create=True) as mock_open:
                # Mock file reading
                mock_open.return_value.__enter__.return_value.read.return_value = test_content
                
                runner = CliRunner()
                result = runner.invoke(cli, [
                    'analyze', temp_file,
                    '--claude-api-key', 'test-key'
                ])
            
            assert result.exit_code == 0
            assert 'Analysis completed successfully' in result.output
            assert '2 topics, 2 keywords' in result.output
            assert '1 detected' in result.output
            
            # Verify service was called
            mock_service.analyze_transcription.assert_called_once()
            
        finally:
            os.unlink(temp_file)
    
    def test_analyze_file_not_found(self):
        """Test analyze command with non-existent file."""
        runner = CliRunner()
        result = runner.invoke(cli, [
            'analyze', '/nonexistent/file.md',
            '--claude-api-key', 'test-key'
        ])
        
        assert result.exit_code == 2
        assert 'does not exist' in result.output


class TestCLIErrorHandling:
    """Test CLI error handling and edge cases."""
    
    def test_keyboard_interrupt_handling(self):
        """Test handling of keyboard interrupt."""
        with patch('podknow.services.discovery.PodcastDiscoveryService') as mock_service:
            mock_service.side_effect = KeyboardInterrupt()
            
            runner = CliRunner()
            result = runner.invoke(cli, ['search', 'test'])
            
            assert result.exit_code == 130
            assert 'cancelled by user' in result.output
    
    def test_verbose_error_output(self):
        """Test verbose error output."""
        with patch('podknow.services.discovery.PodcastDiscoveryService') as mock_service:
            mock_service.side_effect = Exception("Unexpected error")
            
            runner = CliRunner()
            result = runner.invoke(cli, ['--verbose', 'search', 'test'])
            
            # In verbose mode, the full exception should be raised
            assert result.exit_code == 1
    
    def test_parameter_validation(self):
        """Test parameter validation."""
        runner = CliRunner()
        
        # Test invalid count parameter
        result = runner.invoke(cli, ['list', 'https://example.com/feed.xml', '--count', '0'])
        assert result.exit_code == 2
        
        # Test invalid limit parameter
        result = runner.invoke(cli, ['search', 'test', '--limit', '101'])
        assert result.exit_code == 2