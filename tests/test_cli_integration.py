"""
Integration tests for CLI functionality and command workflows.

These tests validate the complete CLI interface including command parsing,
workflow execution, error handling, and output generation.
"""

import os
import tempfile
import pytest
from click.testing import CliRunner
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from podknow.cli.main import cli
from podknow.models.podcast import PodcastResult, PodcastMetadata
from podknow.models.episode import Episode
from podknow.models.transcription import TranscriptionResult, TranscriptionSegment
from podknow.models.analysis import AnalysisResult, SponsorSegment
from podknow.exceptions import NetworkError, TranscriptionError, AnalysisError


@pytest.fixture
def cli_runner():
    """Create CLI test runner."""
    return CliRunner()


@pytest.fixture
def temp_config_dir():
    """Create temporary config directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir) / ".podknow"
        config_dir.mkdir(parents=True, exist_ok=True)
        yield config_dir


@pytest.fixture
def mock_config_file(temp_config_dir):
    """Create mock configuration file."""
    config_file = temp_config_dir / "config.md"
    config_content = """# PodKnow Configuration

## API Keys

```yaml
claude_api_key: "test-api-key"
```

## Analysis Prompts

### Summary Prompt
```
Test summary prompt
```

### Topic Extraction Prompt
```
Test topic prompt
```

### Keyword Identification Prompt
```
Test keyword prompt
```

### Sponsor Detection Prompt
```
Test sponsor prompt
```
"""
    config_file.write_text(config_content)
    return config_file


@pytest.fixture
def sample_search_results():
    """Sample search results for testing."""
    return [
        PodcastResult(
            title="Test Podcast One",
            author="Test Author One",
            rss_url="https://example.com/feed1.xml",
            platform="iTunes",
            description="First test podcast"
        ),
        PodcastResult(
            title="Test Podcast Two", 
            author="Test Author Two",
            rss_url="https://example.com/feed2.xml",
            platform="iTunes",
            description="Second test podcast"
        )
    ]


@pytest.fixture
def sample_episode_data():
    """Sample episode data for testing."""
    from datetime import datetime, timedelta
    
    podcast_metadata = PodcastMetadata(
        title="Test Podcast",
        author="Test Author",
        description="A test podcast",
        rss_url="https://example.com/feed.xml",
        episode_count=50,
        last_updated=datetime.now()
    )
    
    episodes = [
        Episode(
            id="ep001",
            title="Episode 1: Getting Started",
            description="The first episode of our test podcast",
            audio_url="https://example.com/audio1.mp3",
            publication_date=datetime.now() - timedelta(days=1),
            duration="25:30"
        ),
        Episode(
            id="ep002",
            title="Episode 2: Advanced Topics", 
            description="Diving deeper into the subject",
            audio_url="https://example.com/audio2.mp3",
            publication_date=datetime.now() - timedelta(days=2),
            duration="32:15"
        )
    ]
    
    return podcast_metadata, episodes


class TestCLISearchCommand:
    """Test CLI search command functionality."""
    
    @pytest.mark.integration
    def test_search_command_success(self, cli_runner, sample_search_results):
        """Test successful search command execution."""
        with patch('podknow.services.workflow.WorkflowOrchestrator') as mock_orchestrator_class:
            mock_orchestrator = Mock()
            mock_orchestrator.execute_search_workflow.return_value = sample_search_results
            mock_orchestrator_class.return_value = mock_orchestrator
            
            result = cli_runner.invoke(cli, ['search', 'test podcast'])
            
            assert result.exit_code == 0
            assert "Test Podcast One" in result.output
            assert "Test Podcast Two" in result.output
            assert "https://example.com/feed1.xml" in result.output
            mock_orchestrator.execute_search_workflow.assert_called_once()
    
    @pytest.mark.integration
    def test_search_command_with_options(self, cli_runner, sample_search_results):
        """Test search command with platform and limit options."""
        with patch('podknow.services.workflow.WorkflowOrchestrator') as mock_orchestrator_class:
            mock_orchestrator = Mock()
            mock_orchestrator.execute_search_workflow.return_value = sample_search_results[:1]
            mock_orchestrator_class.return_value = mock_orchestrator
            
            result = cli_runner.invoke(cli, [
                'search', 'test podcast', 
                '--platform', 'itunes',
                '--limit', '5'
            ])
            
            assert result.exit_code == 0
            assert "Test Podcast One" in result.output
            mock_orchestrator.execute_search_workflow.assert_called_once_with(
                keywords='test podcast',
                platform='itunes',
                limit=5
            )
    
    @pytest.mark.integration
    def test_search_command_network_error(self, cli_runner):
        """Test search command with network error."""
        with patch('podknow.services.workflow.WorkflowOrchestrator') as mock_orchestrator_class:
            mock_orchestrator = Mock()
            mock_orchestrator.execute_search_workflow.side_effect = NetworkError("Connection failed")
            mock_orchestrator_class.return_value = mock_orchestrator
            
            result = cli_runner.invoke(cli, ['search', 'test podcast'])
            
            assert result.exit_code == 1
            assert "Connection failed" in result.output
    
    @pytest.mark.integration
    def test_search_command_no_results(self, cli_runner):
        """Test search command with no results."""
        with patch('podknow.services.workflow.WorkflowOrchestrator') as mock_orchestrator_class:
            mock_orchestrator = Mock()
            mock_orchestrator.execute_search_workflow.return_value = []
            mock_orchestrator_class.return_value = mock_orchestrator
            
            result = cli_runner.invoke(cli, ['search', 'nonexistent podcast'])
            
            assert result.exit_code == 0
            assert "No podcasts found" in result.output
    
    @pytest.mark.integration
    def test_search_command_verbose(self, cli_runner, sample_search_results):
        """Test search command with verbose output."""
        with patch('podknow.services.workflow.WorkflowOrchestrator') as mock_orchestrator_class:
            mock_orchestrator = Mock()
            mock_orchestrator.execute_search_workflow.return_value = sample_search_results
            mock_orchestrator_class.return_value = mock_orchestrator
            
            result = cli_runner.invoke(cli, ['--verbose', 'search', 'test podcast'])
            
            assert result.exit_code == 0
            # Verbose output should include debug information
            assert "[DEBUG]" in result.output or "Test Podcast One" in result.output


class TestCLIListCommand:
    """Test CLI list command functionality."""
    
    @pytest.mark.integration
    def test_list_command_success(self, cli_runner, sample_episode_data):
        """Test successful list command execution."""
        podcast_metadata, episodes = sample_episode_data
        
        with patch('podknow.services.workflow.WorkflowOrchestrator') as mock_orchestrator_class:
            mock_orchestrator = Mock()
            mock_orchestrator.execute_episode_listing_workflow.return_value = (podcast_metadata, episodes)
            mock_orchestrator_class.return_value = mock_orchestrator
            
            result = cli_runner.invoke(cli, ['list', 'https://example.com/feed.xml'])
            
            assert result.exit_code == 0
            assert "Test Podcast" in result.output
            assert "Episode 1: Getting Started" in result.output
            assert "ep001" in result.output
            assert "25:30" in result.output
    
    @pytest.mark.integration
    def test_list_command_with_count(self, cli_runner, sample_episode_data):
        """Test list command with episode count limit."""
        podcast_metadata, episodes = sample_episode_data
        
        with patch('podknow.services.workflow.WorkflowOrchestrator') as mock_orchestrator_class:
            mock_orchestrator = Mock()
            mock_orchestrator.execute_episode_listing_workflow.return_value = (podcast_metadata, episodes[:1])
            mock_orchestrator_class.return_value = mock_orchestrator
            
            result = cli_runner.invoke(cli, ['list', 'https://example.com/feed.xml', '--count', '1'])
            
            assert result.exit_code == 0
            mock_orchestrator.execute_episode_listing_workflow.assert_called_once_with(
                rss_url='https://example.com/feed.xml',
                count=1
            )
    
    @pytest.mark.integration
    def test_list_command_with_descriptions(self, cli_runner, sample_episode_data):
        """Test list command with episode descriptions."""
        podcast_metadata, episodes = sample_episode_data
        
        with patch('podknow.services.workflow.WorkflowOrchestrator') as mock_orchestrator_class:
            mock_orchestrator = Mock()
            mock_orchestrator.execute_episode_listing_workflow.return_value = (podcast_metadata, episodes)
            mock_orchestrator_class.return_value = mock_orchestrator
            
            result = cli_runner.invoke(cli, ['list', 'https://example.com/feed.xml', '--show-descriptions'])
            
            assert result.exit_code == 0
            assert "The first episode of our test podcast" in result.output
    
    @pytest.mark.integration
    def test_list_command_invalid_url(self, cli_runner):
        """Test list command with invalid RSS URL."""
        result = cli_runner.invoke(cli, ['list', 'invalid-url'])
        
        assert result.exit_code == 2  # Click parameter validation error
        assert "RSS URL must start with http" in result.output


class TestCLITranscribeCommand:
    """Test CLI transcribe command functionality."""
    
    @pytest.mark.integration
    def test_transcribe_command_success(self, cli_runner):
        """Test successful transcribe command execution."""
        with patch('podknow.services.workflow.WorkflowOrchestrator') as mock_orchestrator_class:
            mock_orchestrator = Mock()
            mock_orchestrator.execute_transcription_workflow.return_value = "/tmp/output.md"
            mock_orchestrator_class.return_value = mock_orchestrator
            
            result = cli_runner.invoke(cli, [
                'transcribe', 'ep001',
                '--rss-url', 'https://example.com/feed.xml',
                '--claude-api-key', 'test-key'
            ])
            
            assert result.exit_code == 0
            assert "Transcription completed successfully" in result.output
            assert "/tmp/output.md" in result.output
    
    @pytest.mark.integration
    def test_transcribe_command_skip_analysis(self, cli_runner):
        """Test transcribe command with analysis skipped."""
        with patch('podknow.services.workflow.WorkflowOrchestrator') as mock_orchestrator_class:
            mock_orchestrator = Mock()
            mock_orchestrator.execute_transcription_workflow.return_value = "/tmp/output.md"
            mock_orchestrator_class.return_value = mock_orchestrator
            
            result = cli_runner.invoke(cli, [
                'transcribe', 'ep001',
                '--rss-url', 'https://example.com/feed.xml',
                '--skip-analysis'
            ])
            
            assert result.exit_code == 0
            mock_orchestrator.execute_transcription_workflow.assert_called_once()
            call_args = mock_orchestrator.execute_transcription_workflow.call_args
            assert call_args.kwargs['skip_analysis'] == True
    
    @pytest.mark.integration
    def test_transcribe_command_custom_output_dir(self, cli_runner):
        """Test transcribe command with custom output directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('podknow.services.workflow.WorkflowOrchestrator') as mock_orchestrator_class:
                mock_orchestrator = Mock()
                mock_orchestrator.execute_transcription_workflow.return_value = f"{temp_dir}/output.md"
                mock_orchestrator_class.return_value = mock_orchestrator
                
                result = cli_runner.invoke(cli, [
                    'transcribe', 'ep001',
                    '--rss-url', 'https://example.com/feed.xml',
                    '--claude-api-key', 'test-key',
                    '--output-dir', temp_dir
                ])
                
                assert result.exit_code == 0
                call_args = mock_orchestrator.execute_transcription_workflow.call_args
                assert call_args.kwargs['output_dir'] == temp_dir
    
    @pytest.mark.integration
    def test_transcribe_command_missing_api_key(self, cli_runner):
        """Test transcribe command without API key."""
        result = cli_runner.invoke(cli, [
            'transcribe', 'ep001',
            '--rss-url', 'https://example.com/feed.xml'
        ])
        
        assert result.exit_code == 2  # Click parameter validation error
        assert "Claude API key is required" in result.output
    
    @pytest.mark.integration
    def test_transcribe_command_transcription_error(self, cli_runner):
        """Test transcribe command with transcription error."""
        with patch('podknow.services.workflow.WorkflowOrchestrator') as mock_orchestrator_class:
            mock_orchestrator = Mock()
            mock_orchestrator.execute_transcription_workflow.side_effect = TranscriptionError("Transcription failed")
            mock_orchestrator_class.return_value = mock_orchestrator
            
            result = cli_runner.invoke(cli, [
                'transcribe', 'ep001',
                '--rss-url', 'https://example.com/feed.xml',
                '--claude-api-key', 'test-key'
            ])
            
            assert result.exit_code == 1
            assert "Transcription failed" in result.output


class TestCLIAnalyzeCommand:
    """Test CLI analyze command functionality."""
    
    @pytest.mark.integration
    def test_analyze_command_success(self, cli_runner):
        """Test successful analyze command execution."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as temp_file:
            temp_file.write("""---
title: "Test Episode"
---

# Test Episode

This is a test transcription for analysis.
""")
            temp_file.flush()
            
            try:
                with patch('podknow.services.workflow.WorkflowOrchestrator') as mock_orchestrator_class:
                    mock_orchestrator = Mock()
                    mock_orchestrator.execute_analysis_workflow.return_value = temp_file.name
                    mock_orchestrator_class.return_value = mock_orchestrator
                    
                    result = cli_runner.invoke(cli, [
                        'analyze', temp_file.name,
                        '--claude-api-key', 'test-key'
                    ])
                    
                    assert result.exit_code == 0
                    assert "Analysis completed successfully" in result.output
            finally:
                os.unlink(temp_file.name)
    
    @pytest.mark.integration
    def test_analyze_command_custom_output(self, cli_runner):
        """Test analyze command with custom output file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as input_file, \
             tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as output_file:
            
            input_file.write("""---
title: "Test Episode"
---

# Test Episode

This is a test transcription.
""")
            input_file.flush()
            
            try:
                with patch('podknow.services.workflow.WorkflowOrchestrator') as mock_orchestrator_class:
                    mock_orchestrator = Mock()
                    mock_orchestrator.execute_analysis_workflow.return_value = output_file.name
                    mock_orchestrator_class.return_value = mock_orchestrator
                    
                    result = cli_runner.invoke(cli, [
                        'analyze', input_file.name,
                        '--claude-api-key', 'test-key',
                        '--output-file', output_file.name
                    ])
                    
                    assert result.exit_code == 0
                    call_args = mock_orchestrator.execute_analysis_workflow.call_args
                    assert call_args.kwargs['output_file'] == output_file.name
            finally:
                os.unlink(input_file.name)
                os.unlink(output_file.name)
    
    @pytest.mark.integration
    def test_analyze_command_file_not_found(self, cli_runner):
        """Test analyze command with non-existent file."""
        result = cli_runner.invoke(cli, [
            'analyze', '/nonexistent/file.md',
            '--claude-api-key', 'test-key'
        ])
        
        assert result.exit_code == 2  # Click parameter validation error
        assert "not found" in result.output.lower()
    
    @pytest.mark.integration
    def test_analyze_command_analysis_error(self, cli_runner):
        """Test analyze command with analysis error."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as temp_file:
            temp_file.write("# Test content")
            temp_file.flush()
            
            try:
                with patch('podknow.services.workflow.WorkflowOrchestrator') as mock_orchestrator_class:
                    mock_orchestrator = Mock()
                    mock_orchestrator.execute_analysis_workflow.side_effect = AnalysisError("Analysis failed")
                    mock_orchestrator_class.return_value = mock_orchestrator
                    
                    result = cli_runner.invoke(cli, [
                        'analyze', temp_file.name,
                        '--claude-api-key', 'test-key'
                    ])
                    
                    assert result.exit_code == 1
                    assert "Analysis failed" in result.output
            finally:
                os.unlink(temp_file.name)


class TestCLISetupCommands:
    """Test CLI setup and configuration commands."""
    
    @pytest.mark.integration
    def test_setup_command_success(self, cli_runner):
        """Test successful setup command execution."""
        with patch('podknow.config.manager.ConfigManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager.config_exists.return_value = False
            mock_manager.generate_config_for_first_time_setup.return_value = "/tmp/config.md"
            mock_manager_class.return_value = mock_manager
            
            result = cli_runner.invoke(cli, ['setup'])
            
            assert result.exit_code == 0
            assert "Configuration file created successfully" in result.output
            assert "/tmp/config.md" in result.output
            assert "Claude API key" in result.output
    
    @pytest.mark.integration
    def test_setup_command_existing_config(self, cli_runner):
        """Test setup command with existing configuration."""
        with patch('podknow.config.manager.ConfigManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager.config_exists.return_value = True
            mock_manager.config_path = Path("/tmp/config.md")
            mock_manager_class.return_value = mock_manager
            
            result = cli_runner.invoke(cli, ['setup'])
            
            assert result.exit_code == 0
            assert "Configuration file already exists" in result.output
            assert "--force" in result.output
    
    @pytest.mark.integration
    def test_setup_command_force_overwrite(self, cli_runner):
        """Test setup command with force overwrite."""
        with patch('podknow.config.manager.ConfigManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager.config_exists.return_value = True
            mock_manager.generate_config_for_first_time_setup.return_value = "/tmp/config.md"
            mock_manager_class.return_value = mock_manager
            
            result = cli_runner.invoke(cli, ['setup', '--force'])
            
            assert result.exit_code == 0
            assert "Configuration file created successfully" in result.output
    
    @pytest.mark.integration
    def test_config_status_command_valid_config(self, cli_runner):
        """Test config-status command with valid configuration."""
        with patch('podknow.config.manager.ConfigManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager.get_config_status.return_value = {
                'config_exists': True,
                'config_path': '/tmp/config.md',
                'config_directory': '/tmp',
                'is_valid': True,
                'missing_keys': [],
                'validation_errors': []
            }
            mock_manager_class.return_value = mock_manager
            
            result = cli_runner.invoke(cli, ['config-status'])
            
            assert result.exit_code == 0
            assert "Configuration file exists" in result.output
            assert "Configuration is valid" in result.output
            assert "ready to use" in result.output
    
    @pytest.mark.integration
    def test_config_status_command_missing_config(self, cli_runner):
        """Test config-status command with missing configuration."""
        with patch('podknow.config.manager.ConfigManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager.get_config_status.return_value = {
                'config_exists': False,
                'config_path': '/tmp/config.md',
                'config_directory': '/tmp',
                'is_valid': False,
                'missing_keys': [],
                'validation_errors': []
            }
            mock_manager_class.return_value = mock_manager
            
            result = cli_runner.invoke(cli, ['config-status'])
            
            assert result.exit_code == 0
            assert "Configuration file not found" in result.output
            assert "podknow setup" in result.output
    
    @pytest.mark.integration
    def test_config_status_command_invalid_config(self, cli_runner):
        """Test config-status command with invalid configuration."""
        with patch('podknow.config.manager.ConfigManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager.get_config_status.return_value = {
                'config_exists': True,
                'config_path': '/tmp/config.md',
                'config_directory': '/tmp',
                'is_valid': False,
                'missing_keys': ['claude_api_key'],
                'validation_errors': ['Invalid YAML syntax']
            }
            mock_manager_class.return_value = mock_manager
            
            result = cli_runner.invoke(cli, ['config-status'])
            
            assert result.exit_code == 0
            assert "Configuration has issues" in result.output
            assert "claude_api_key" in result.output
            assert "Invalid YAML syntax" in result.output


class TestCLIErrorHandling:
    """Test CLI error handling and edge cases."""
    
    @pytest.mark.integration
    def test_cli_keyboard_interrupt(self, cli_runner):
        """Test CLI handling of keyboard interrupt."""
        with patch('podknow.services.workflow.WorkflowOrchestrator') as mock_orchestrator_class:
            mock_orchestrator = Mock()
            mock_orchestrator.execute_search_workflow.side_effect = KeyboardInterrupt()
            mock_orchestrator_class.return_value = mock_orchestrator
            
            result = cli_runner.invoke(cli, ['search', 'test'])
            
            assert result.exit_code == 130  # Standard exit code for SIGINT
    
    @pytest.mark.integration
    def test_cli_unexpected_error_verbose(self, cli_runner):
        """Test CLI handling of unexpected errors in verbose mode."""
        with patch('podknow.services.workflow.WorkflowOrchestrator') as mock_orchestrator_class:
            mock_orchestrator = Mock()
            mock_orchestrator.execute_search_workflow.side_effect = Exception("Unexpected error")
            mock_orchestrator_class.return_value = mock_orchestrator
            
            result = cli_runner.invoke(cli, ['--verbose', 'search', 'test'])
            
            assert result.exit_code == 1
            # In verbose mode, should show the actual exception
    
    @pytest.mark.integration
    def test_cli_unexpected_error_normal(self, cli_runner):
        """Test CLI handling of unexpected errors in normal mode."""
        with patch('podknow.services.workflow.WorkflowOrchestrator') as mock_orchestrator_class:
            mock_orchestrator = Mock()
            mock_orchestrator.execute_search_workflow.side_effect = Exception("Unexpected error")
            mock_orchestrator_class.return_value = mock_orchestrator
            
            result = cli_runner.invoke(cli, ['search', 'test'])
            
            assert result.exit_code == 1
            assert "An unexpected error occurred" in result.output
    
    @pytest.mark.integration
    def test_cli_invalid_command(self, cli_runner):
        """Test CLI with invalid command."""
        result = cli_runner.invoke(cli, ['invalid-command'])
        
        assert result.exit_code == 2  # Click command not found
        assert "No such command" in result.output
    
    @pytest.mark.integration
    def test_cli_help_output(self, cli_runner):
        """Test CLI help output."""
        result = cli_runner.invoke(cli, ['--help'])
        
        assert result.exit_code == 0
        assert "PodKnow" in result.output
        assert "search" in result.output
        assert "list" in result.output
        assert "transcribe" in result.output
        assert "analyze" in result.output
    
    @pytest.mark.integration
    def test_cli_version_output(self, cli_runner):
        """Test CLI version output."""
        result = cli_runner.invoke(cli, ['--version'])
        
        assert result.exit_code == 0
        assert "0.1.0" in result.output


class TestCLILogFileIntegration:
    """Test CLI integration with log files."""
    
    @pytest.mark.integration
    def test_cli_with_log_file(self, cli_runner):
        """Test CLI with log file option."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as log_file:
            try:
                with patch('podknow.services.workflow.WorkflowOrchestrator') as mock_orchestrator_class:
                    mock_orchestrator = Mock()
                    mock_orchestrator.execute_search_workflow.return_value = []
                    mock_orchestrator_class.return_value = mock_orchestrator
                    
                    result = cli_runner.invoke(cli, [
                        '--log-file', log_file.name,
                        'search', 'test'
                    ])
                    
                    assert result.exit_code == 0
                    
                    # Check that WorkflowOrchestrator was initialized with log file
                    mock_orchestrator_class.assert_called_once()
                    call_args = mock_orchestrator_class.call_args
                    assert call_args.kwargs['log_file'] == log_file.name
            finally:
                os.unlink(log_file.name)


if __name__ == "__main__":
    # Run CLI integration tests
    pytest.main([__file__, "-v", "-m", "integration"])