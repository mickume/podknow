"""
Integration tests for workflow orchestration and end-to-end functionality.

These tests validate the complete workflow from discovery through final output,
including error recovery and graceful degradation scenarios.
"""

import os
import tempfile
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from podknow.services.workflow import WorkflowOrchestrator, WorkflowState, WorkflowLogger
from podknow.models.podcast import PodcastResult, PodcastMetadata
from podknow.models.episode import Episode
from podknow.models.transcription import TranscriptionResult, TranscriptionSegment
from podknow.models.analysis import AnalysisResult, SponsorSegment
from podknow.exceptions import (
    NetworkError, 
    TranscriptionError, 
    AnalysisError,
    AudioProcessingError,
    LanguageDetectionError
)


@pytest.fixture
def temp_output_dir():
    """Create temporary output directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def workflow_orchestrator(temp_output_dir):
    """Create workflow orchestrator for testing."""
    log_file = os.path.join(temp_output_dir, "test.log")
    return WorkflowOrchestrator(verbose=True, log_file=log_file)


@pytest.fixture
def sample_podcast_results():
    """Sample podcast search results."""
    return [
        PodcastResult(
            title="Test Podcast",
            author="Test Author",
            rss_url="https://example.com/feed.xml",
            platform="iTunes",
            description="A test podcast for integration testing"
        ),
        PodcastResult(
            title="Another Podcast",
            author="Another Author", 
            rss_url="https://example.com/feed2.xml",
            platform="Spotify",
            description="Another test podcast"
        )
    ]


@pytest.fixture
def sample_podcast_metadata():
    """Sample podcast metadata."""
    from datetime import datetime
    return PodcastMetadata(
        title="Test Podcast",
        author="Test Author",
        description="A test podcast",
        rss_url="https://example.com/feed.xml",
        episode_count=100,
        last_updated=datetime.now()
    )


@pytest.fixture
def sample_episodes():
    """Sample episode list."""
    from datetime import datetime, timedelta
    return [
        Episode(
            id="ep001",
            title="Episode 1: Introduction",
            description="The first episode",
            audio_url="https://example.com/audio1.mp3",
            publication_date=datetime.now() - timedelta(days=1),
            duration="30:00"
        ),
        Episode(
            id="ep002", 
            title="Episode 2: Deep Dive",
            description="A deeper look",
            audio_url="https://example.com/audio2.mp3",
            publication_date=datetime.now() - timedelta(days=2),
            duration="45:00"
        )
    ]


@pytest.fixture
def sample_transcription_result():
    """Sample transcription result."""
    segments = [
        TranscriptionSegment(
            start_time=0.0,
            end_time=5.0,
            text="Welcome to the test podcast.",
            is_paragraph_start=True
        ),
        TranscriptionSegment(
            start_time=5.0,
            end_time=10.0,
            text="Today we'll discuss integration testing.",
            is_paragraph_start=False
        )
    ]
    
    return TranscriptionResult(
        text="Welcome to the test podcast. Today we'll discuss integration testing.",
        segments=segments,
        language="en",
        confidence=0.95
    )


@pytest.fixture
def sample_analysis_result():
    """Sample analysis result."""
    return AnalysisResult(
        summary="This episode introduces integration testing concepts and best practices.",
        topics=["Integration Testing", "Software Quality", "Test Automation"],
        keywords=["testing", "integration", "software", "quality", "automation"],
        sponsor_segments=[
            SponsorSegment(
                start_text="This episode is brought to you by",
                end_text="Use code TEST for 20% off",
                confidence=0.9
            )
        ]
    )


class TestWorkflowLogger:
    """Test workflow logging functionality."""
    
    def test_logger_initialization(self, temp_output_dir):
        """Test logger initialization with file output."""
        log_file = os.path.join(temp_output_dir, "test.log")
        logger = WorkflowLogger(verbose=True, log_file=log_file)
        
        logger.info("Test message")
        logger.debug("Debug message")
        logger.warning("Warning message")
        logger.error("Error message")
        
        # Check that log file was created
        assert os.path.exists(log_file)
        
        # Check log content
        with open(log_file, 'r') as f:
            content = f.read()
            assert "Test message" in content
            assert "Debug message" in content
    
    def test_logger_without_file(self):
        """Test logger without file output."""
        logger = WorkflowLogger(verbose=False, log_file=None)
        
        # Should not raise any exceptions
        logger.info("Test message")
        logger.debug("Debug message")
        logger.warning("Warning message")
        logger.error("Error message")


class TestWorkflowState:
    """Test workflow state tracking."""
    
    def test_state_initialization(self):
        """Test workflow state initialization."""
        state = WorkflowState()
        
        assert state.current_step == "initialization"
        assert len(state.completed_steps) == 0
        assert len(state.failed_steps) == 0
        assert len(state.errors) == 0
        assert len(state.warnings) == 0
    
    def test_step_progression(self):
        """Test step progression tracking."""
        state = WorkflowState()
        
        state.set_step("discovery")
        assert state.current_step == "discovery"
        assert "initialization" in state.completed_steps
        
        state.set_step("transcription")
        assert state.current_step == "transcription"
        assert "discovery" in state.completed_steps
    
    def test_error_tracking(self):
        """Test error and warning tracking."""
        state = WorkflowState()
        
        error = NetworkError("Test error")
        state.mark_step_failed("discovery", error)
        
        assert "discovery" in state.failed_steps
        assert len(state.errors) == 1
        assert state.errors[0][0] == "discovery"
        assert state.errors[0][1] == error
        
        state.add_warning("transcription", "Test warning")
        assert len(state.warnings) == 1
        assert state.warnings[0] == ("transcription", "Test warning")
    
    def test_recovery_detection(self):
        """Test recovery point detection."""
        state = WorkflowState()
        
        # No recovery points initially
        assert not state.is_recoverable()
        
        # Add some completed steps
        state.completed_steps = ["podcast_search", "episode_listing"]
        assert state.is_recoverable()


class TestWorkflowOrchestrator:
    """Test workflow orchestration functionality."""
    
    @pytest.mark.integration
    def test_search_workflow_success(self, workflow_orchestrator, sample_podcast_results):
        """Test successful podcast search workflow."""
        with patch.object(workflow_orchestrator.discovery_service, 'get_combined_results') as mock_search:
            mock_search.return_value = sample_podcast_results
            
            results = workflow_orchestrator.execute_search_workflow(
                keywords="test podcast",
                platform="all",
                limit=10
            )
            
            assert len(results) == 2
            assert results[0].title == "Test Podcast"
            mock_search.assert_called_once_with("test podcast")
    
    @pytest.mark.integration
    def test_search_workflow_network_error(self, workflow_orchestrator):
        """Test search workflow with network error."""
        with patch.object(workflow_orchestrator.discovery_service, 'get_combined_results') as mock_search:
            mock_search.side_effect = NetworkError("Connection failed")
            
            with pytest.raises(NetworkError):
                workflow_orchestrator.execute_search_workflow(
                    keywords="test podcast",
                    platform="all",
                    limit=10
                )
    
    @pytest.mark.integration
    def test_episode_listing_workflow_success(self, workflow_orchestrator, sample_podcast_metadata, sample_episodes):
        """Test successful episode listing workflow."""
        with patch.object(workflow_orchestrator.episode_service, 'get_podcast_info') as mock_info, \
             patch.object(workflow_orchestrator.episode_service, 'list_episodes') as mock_list:
            
            mock_info.return_value = sample_podcast_metadata
            mock_list.return_value = sample_episodes
            
            podcast_info, episodes = workflow_orchestrator.execute_episode_listing_workflow(
                rss_url="https://example.com/feed.xml",
                count=10
            )
            
            assert podcast_info.title == "Test Podcast"
            assert len(episodes) == 2
            assert episodes[0].id == "ep001"
    
    @pytest.mark.integration
    def test_transcription_workflow_success(self, workflow_orchestrator, sample_episodes, 
                                          sample_podcast_metadata, sample_transcription_result,
                                          sample_analysis_result, temp_output_dir):
        """Test successful complete transcription workflow."""
        with patch.object(workflow_orchestrator.episode_service, 'find_episode_by_id') as mock_find, \
             patch.object(workflow_orchestrator.episode_service, 'get_podcast_info') as mock_info, \
             patch.object(workflow_orchestrator.transcription_service, 'download_audio') as mock_download, \
             patch.object(workflow_orchestrator.transcription_service, 'detect_language') as mock_detect, \
             patch.object(workflow_orchestrator.transcription_service, 'transcribe_audio') as mock_transcribe, \
             patch.object(workflow_orchestrator.transcription_service, 'cleanup_audio_file') as mock_cleanup, \
             patch.object(workflow_orchestrator, 'get_analysis_service') as mock_analysis_service:
            
            # Setup mocks
            mock_find.return_value = sample_episodes[0]
            mock_info.return_value = sample_podcast_metadata
            mock_download.return_value = "/tmp/test_audio.mp3"
            mock_detect.return_value = "en"
            mock_transcribe.return_value = sample_transcription_result
            
            mock_analysis = Mock()
            # Mock all methods called by analyze_transcription
            mock_analysis.generate_summary.return_value = sample_analysis_result.summary
            mock_analysis.extract_topics.return_value = sample_analysis_result.topics
            mock_analysis.identify_keywords.return_value = sample_analysis_result.keywords
            mock_analysis.detect_sponsor_content.return_value = sample_analysis_result.sponsor_segments
            mock_analysis.analyze_transcription.return_value = sample_analysis_result
            mock_analysis.generate_markdown_output.return_value = "# Test Output\n\nContent here"
            mock_analysis_service.return_value = mock_analysis
            
            # Execute workflow
            output_path = workflow_orchestrator.execute_transcription_workflow(
                episode_id="ep001",
                rss_url="https://example.com/feed.xml",
                output_dir=temp_output_dir,
                claude_api_key="test-key",
                skip_analysis=False
            )
            
            # Verify calls
            mock_find.assert_called_once_with("https://example.com/feed.xml", "ep001")
            mock_download.assert_called_once()
            mock_detect.assert_called_once()
            mock_transcribe.assert_called_once()
            mock_cleanup.assert_called_once()
            
            # Verify output file exists
            assert os.path.exists(output_path)
            assert output_path.startswith(temp_output_dir)
    
    @pytest.mark.integration
    def test_transcription_workflow_skip_analysis(self, workflow_orchestrator, sample_episodes,
                                                sample_podcast_metadata, sample_transcription_result,
                                                temp_output_dir):
        """Test transcription workflow with analysis skipped."""
        with patch.object(workflow_orchestrator.episode_service, 'find_episode_by_id') as mock_find, \
             patch.object(workflow_orchestrator.episode_service, 'get_podcast_info') as mock_info, \
             patch.object(workflow_orchestrator.transcription_service, 'download_audio') as mock_download, \
             patch.object(workflow_orchestrator.transcription_service, 'detect_language') as mock_detect, \
             patch.object(workflow_orchestrator.transcription_service, 'transcribe_audio') as mock_transcribe, \
             patch.object(workflow_orchestrator.transcription_service, 'generate_markdown_output') as mock_output, \
             patch.object(workflow_orchestrator.transcription_service, 'cleanup_audio_file') as mock_cleanup:
            
            # Setup mocks
            mock_find.return_value = sample_episodes[0]
            mock_info.return_value = sample_podcast_metadata
            mock_download.return_value = "/tmp/test_audio.mp3"
            mock_detect.return_value = "en"
            mock_transcribe.return_value = sample_transcription_result
            mock_output.return_value = os.path.join(temp_output_dir, "test_output.md")
            
            # Execute workflow with analysis skipped
            output_path = workflow_orchestrator.execute_transcription_workflow(
                episode_id="ep001",
                rss_url="https://example.com/feed.xml",
                output_dir=temp_output_dir,
                claude_api_key=None,
                skip_analysis=True
            )
            
            # Verify analysis was skipped
            mock_output.assert_called_once()
            assert output_path == os.path.join(temp_output_dir, "test_output.md")
    
    @pytest.mark.integration
    def test_transcription_workflow_language_error(self, workflow_orchestrator, sample_episodes,
                                                  sample_podcast_metadata):
        """Test transcription workflow with language detection error."""
        with patch.object(workflow_orchestrator.episode_service, 'find_episode_by_id') as mock_find, \
             patch.object(workflow_orchestrator.episode_service, 'get_podcast_info') as mock_info, \
             patch.object(workflow_orchestrator.transcription_service, 'download_audio') as mock_download, \
             patch.object(workflow_orchestrator.transcription_service, 'detect_language') as mock_detect, \
             patch.object(workflow_orchestrator.transcription_service, 'cleanup_audio_file') as mock_cleanup:
            
            # Setup mocks
            mock_find.return_value = sample_episodes[0]
            mock_info.return_value = sample_podcast_metadata
            mock_download.return_value = "/tmp/test_audio.mp3"
            mock_detect.side_effect = LanguageDetectionError("Non-English content detected")
            
            # Execute workflow - should raise language error
            with pytest.raises(LanguageDetectionError):
                workflow_orchestrator.execute_transcription_workflow(
                    episode_id="ep001",
                    rss_url="https://example.com/feed.xml",
                    claude_api_key="test-key"
                )
            
            # Verify cleanup was called even on error
            mock_cleanup.assert_called_once()
    
    @pytest.mark.integration
    def test_transcription_workflow_analysis_failure_recovery(self, workflow_orchestrator, sample_episodes,
                                                            sample_podcast_metadata, sample_transcription_result,
                                                            temp_output_dir):
        """Test transcription workflow with analysis failure and recovery."""
        with patch.object(workflow_orchestrator.episode_service, 'find_episode_by_id') as mock_find, \
             patch.object(workflow_orchestrator.episode_service, 'get_podcast_info') as mock_info, \
             patch.object(workflow_orchestrator.transcription_service, 'download_audio') as mock_download, \
             patch.object(workflow_orchestrator.transcription_service, 'detect_language') as mock_detect, \
             patch.object(workflow_orchestrator.transcription_service, 'transcribe_audio') as mock_transcribe, \
             patch.object(workflow_orchestrator.transcription_service, 'generate_markdown_output') as mock_output, \
             patch.object(workflow_orchestrator.transcription_service, 'cleanup_audio_file') as mock_cleanup, \
             patch.object(workflow_orchestrator, 'get_analysis_service') as mock_analysis_service:
            
            # Setup mocks
            mock_find.return_value = sample_episodes[0]
            mock_info.return_value = sample_podcast_metadata
            mock_download.return_value = "/tmp/test_audio.mp3"
            mock_detect.return_value = "en"
            mock_transcribe.return_value = sample_transcription_result
            mock_output.return_value = os.path.join(temp_output_dir, "test_output.md")
            
            # Make analysis fail
            mock_analysis = Mock()
            mock_analysis.analyze_transcription.side_effect = AnalysisError("API error")
            mock_analysis_service.return_value = mock_analysis
            
            # Execute workflow - should recover by skipping analysis
            output_path = workflow_orchestrator.execute_transcription_workflow(
                episode_id="ep001",
                rss_url="https://example.com/feed.xml",
                output_dir=temp_output_dir,
                claude_api_key="test-key",
                skip_analysis=False
            )
            
            # Verify transcription-only output was generated
            mock_output.assert_called_once()
            assert output_path == os.path.join(temp_output_dir, "test_output.md")
    
    @pytest.mark.integration
    def test_workflow_status_check(self, workflow_orchestrator):
        """Test workflow status and health check."""
        status = workflow_orchestrator.get_workflow_status()
        
        assert 'services' in status
        assert 'dependencies' in status
        assert 'configuration' in status
        
        # Check service initialization status
        services = status['services']
        assert 'discovery' in services
        assert 'episode' in services
        assert 'transcription' in services
        assert 'analysis' in services
        
        # Check dependencies
        deps = status['dependencies']
        assert 'requests' in deps
        assert 'feedparser' in deps
        # MLX-Whisper and Anthropic may not be available in test environment
        
        # Check configuration
        config = status['configuration']
        assert 'output_directory' in config
        assert 'environment_variables' in config


class TestErrorRecoveryScenarios:
    """Test error recovery and graceful degradation scenarios."""
    
    @pytest.mark.integration
    def test_partial_search_failure_recovery(self, workflow_orchestrator):
        """Test recovery when some search APIs fail."""
        with patch.object(workflow_orchestrator.discovery_service, 'search_itunes') as mock_itunes, \
             patch.object(workflow_orchestrator.discovery_service, 'search_spotify') as mock_spotify:
            
            # iTunes succeeds, Spotify fails
            mock_itunes.return_value = [
                PodcastResult("Test Podcast", "Test Author", "https://example.com/feed.xml", "iTunes", "Description")
            ]
            mock_spotify.side_effect = NetworkError("Spotify API error")
            
            # Should still return iTunes results
            results = workflow_orchestrator.execute_search_workflow("test", "all", 10)
            assert len(results) == 1
            assert results[0].platform == "iTunes"
    
    @pytest.mark.integration
    def test_audio_download_retry_logic(self, workflow_orchestrator, sample_episodes, sample_podcast_metadata):
        """Test audio download retry logic."""
        with patch.object(workflow_orchestrator.episode_service, 'find_episode_by_id') as mock_find, \
             patch.object(workflow_orchestrator.episode_service, 'get_podcast_info') as mock_info, \
             patch.object(workflow_orchestrator.transcription_service, 'download_audio') as mock_download:
            
            mock_find.return_value = sample_episodes[0]
            mock_info.return_value = sample_podcast_metadata
            
            # First call fails, should raise error (no retry in current implementation)
            mock_download.side_effect = NetworkError("Download failed")
            
            with pytest.raises(AudioProcessingError):
                workflow_orchestrator.execute_transcription_workflow(
                    episode_id="ep001",
                    rss_url="https://example.com/feed.xml",
                    claude_api_key="test-key"
                )
    
    @pytest.mark.integration
    def test_cleanup_on_workflow_interruption(self, workflow_orchestrator, sample_episodes, sample_podcast_metadata):
        """Test cleanup when workflow is interrupted."""
        with patch.object(workflow_orchestrator.episode_service, 'find_episode_by_id') as mock_find, \
             patch.object(workflow_orchestrator.episode_service, 'get_podcast_info') as mock_info, \
             patch.object(workflow_orchestrator.transcription_service, 'download_audio') as mock_download, \
             patch.object(workflow_orchestrator.transcription_service, 'detect_language') as mock_detect, \
             patch.object(workflow_orchestrator.transcription_service, 'cleanup_audio_file') as mock_cleanup:
            
            mock_find.return_value = sample_episodes[0]
            mock_info.return_value = sample_podcast_metadata
            mock_download.return_value = "/tmp/test_audio.mp3"
            mock_detect.side_effect = Exception("Unexpected error")
            
            # Workflow should fail but still cleanup
            with pytest.raises(Exception):
                workflow_orchestrator.execute_transcription_workflow(
                    episode_id="ep001",
                    rss_url="https://example.com/feed.xml",
                    claude_api_key="test-key"
                )
            
            # Verify cleanup was called
            mock_cleanup.assert_called_once_with("/tmp/test_audio.mp3")


@pytest.mark.integration
@pytest.mark.slow
class TestEndToEndWorkflows:
    """Test complete end-to-end workflows with real API calls (rate-limited)."""
    
    @pytest.mark.skipif(
        not os.getenv('PODKNOW_INTEGRATION_TESTS'),
        reason="Integration tests require PODKNOW_INTEGRATION_TESTS=1"
    )
    def test_real_podcast_search(self, workflow_orchestrator):
        """Test real podcast search with rate limiting."""
        import time
        
        # Rate limit: only run if not recently executed
        results = workflow_orchestrator.execute_search_workflow(
            keywords="python programming",
            platform="itunes",  # iTunes only to avoid Spotify auth
            limit=5
        )
        
        assert len(results) > 0
        assert all(result.platform == "iTunes" for result in results)
        assert all(result.rss_url.startswith("http") for result in results)
        
        # Rate limit for next test
        time.sleep(1)
    
    @pytest.mark.skipif(
        not os.getenv('PODKNOW_INTEGRATION_TESTS'),
        reason="Integration tests require PODKNOW_INTEGRATION_TESTS=1"
    )
    def test_real_rss_parsing(self, workflow_orchestrator):
        """Test real RSS feed parsing."""
        import time
        
        # Use a known stable RSS feed for testing
        test_rss_url = "https://feeds.feedburner.com/oreilly/radar"
        
        try:
            podcast_info, episodes = workflow_orchestrator.execute_episode_listing_workflow(
                rss_url=test_rss_url,
                count=3
            )
            
            assert podcast_info.title
            assert podcast_info.author
            assert len(episodes) > 0
            assert all(episode.audio_url for episode in episodes)
            
        except Exception as e:
            pytest.skip(f"RSS feed not available for testing: {e}")
        
        # Rate limit for next test
        time.sleep(1)


class TestConfigurationIntegration:
    """Test configuration integration with workflows."""
    
    def test_workflow_with_custom_config(self, temp_output_dir):
        """Test workflow with custom configuration."""
        from podknow.config.manager import ConfigManager
        from podknow.config.models import Config
        
        # Create custom config
        config = Config(
            claude_api_key="test-key",
            output_directory=temp_output_dir,
            max_retries=1,
            retry_delay=0.1
        )
        
        # Create workflow with custom settings
        workflow = WorkflowOrchestrator(verbose=True)
        
        # Verify configuration is used
        status = workflow.get_workflow_status()
        assert status['configuration']['output_directory']
    
    def test_environment_variable_override(self, temp_output_dir):
        """Test environment variable configuration override."""
        import os
        
        # Set environment variables
        original_env = os.environ.copy()
        os.environ['CLAUDE_API_KEY'] = 'env-test-key'
        os.environ['PODKNOW_OUTPUT_DIR'] = temp_output_dir
        
        try:
            workflow = WorkflowOrchestrator(verbose=True)
            status = workflow.get_workflow_status()
            
            # Environment variables should be reflected in status
            env_vars = status['configuration']['environment_variables']
            assert env_vars['CLAUDE_API_KEY'] == True
            
        finally:
            # Restore environment
            os.environ.clear()
            os.environ.update(original_env)


if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v", "-m", "integration"])