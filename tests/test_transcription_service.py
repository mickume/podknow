"""
Integration tests for transcription service.
"""

import pytest
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import requests

from podknow.services.transcription import TranscriptionService
from podknow.models.transcription import TranscriptionResult, TranscriptionSegment
from podknow.models.episode import EpisodeMetadata
from podknow.exceptions import (
    NetworkError, 
    AudioProcessingError, 
    LanguageDetectionError,
    TranscriptionError,
    FileOperationError
)


class TestTranscriptionService:
    """Test TranscriptionService functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.service = TranscriptionService()
        self.temp_dir = tempfile.mkdtemp()
        
    def teardown_method(self):
        """Clean up test fixtures."""
        # Clean up any temporary files
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)


class TestAudioDownload:
    """Test audio download functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.service = TranscriptionService()
    
    @patch('requests.get')
    def test_successful_audio_download(self, mock_get):
        """Test successful audio file download."""
        # Mock successful response
        mock_response = Mock()
        mock_response.headers = {
            'content-type': 'audio/mpeg',
            'content-length': '1024'
        }
        mock_response.iter_content.return_value = [b'fake audio data']
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        with tempfile.TemporaryDirectory() as temp_dir:
            service = TranscriptionService(temp_dir=temp_dir)
            
            result_path = service.download_audio("https://example.com/audio.mp3")
            
            assert os.path.exists(result_path)
            assert result_path.endswith('.mp3')
            
            # Verify file content
            with open(result_path, 'rb') as f:
                content = f.read()
                assert content == b'fake audio data'
    
    @patch('requests.get')
    def test_download_network_error(self, mock_get):
        """Test network error during download."""
        mock_get.side_effect = requests.RequestException("Connection failed")
        
        with pytest.raises(NetworkError, match="Failed to download audio"):
            self.service.download_audio("https://example.com/audio.mp3")
    
    @patch('requests.get')
    def test_download_unsupported_format(self, mock_get):
        """Test download with unsupported audio format."""
        mock_response = Mock()
        mock_response.headers = {'content-type': 'text/html'}
        mock_response.iter_content.return_value = [b'<html>Not audio</html>']
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        with pytest.raises(AudioProcessingError, match="Unsupported audio format"):
            self.service.download_audio("https://example.com/notaudio.html")
    
    def test_audio_content_validation(self):
        """Test audio content type validation."""
        service = self.service
        
        # Valid audio content types
        assert service._is_audio_content('audio/mpeg', 'test.mp3')
        assert service._is_audio_content('audio/wav', 'test.wav')
        assert service._is_audio_content('', 'test.mp3')  # Valid extension
        
        # Invalid content types
        assert not service._is_audio_content('text/html', 'test.html')
        assert not service._is_audio_content('image/jpeg', 'test.jpg')
    
    def test_cleanup_audio_file(self):
        """Test audio file cleanup."""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = temp_file.name
            temp_file.write(b'test data')
        
        # File should exist
        assert os.path.exists(temp_path)
        
        # Clean up
        self.service.cleanup_audio_file(temp_path)
        
        # File should be deleted
        assert not os.path.exists(temp_path)
    
    def test_cleanup_nonexistent_file(self):
        """Test cleanup of non-existent file doesn't raise error."""
        # Should not raise an error
        self.service.cleanup_audio_file("/nonexistent/path/file.mp3")


class TestLanguageDetection:
    """Test language detection functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.service = TranscriptionService()
    
    @patch('mlx_whisper.transcribe')
    def test_english_language_detection(self, mock_transcribe):
        """Test successful English language detection."""
        mock_transcribe.return_value = {'language': 'en'}
        
        with tempfile.NamedTemporaryFile(suffix='.mp3') as temp_file:
            result = self.service.detect_language(temp_file.name)
            assert result == 'en'
    
    @patch('mlx_whisper.transcribe')
    def test_non_english_language_rejection(self, mock_transcribe):
        """Test rejection of non-English content."""
        mock_transcribe.return_value = {'language': 'es'}
        
        with tempfile.NamedTemporaryFile(suffix='.mp3') as temp_file:
            with pytest.raises(LanguageDetectionError, match="Non-English content detected"):
                self.service.detect_language(temp_file.name)
    
    def test_language_detection_missing_file(self):
        """Test language detection with missing file."""
        with pytest.raises(AudioProcessingError, match="Audio file not found"):
            self.service.detect_language("/nonexistent/file.mp3")
    
    @patch('mlx_whisper.transcribe')
    def test_language_detection_mlx_error(self, mock_transcribe):
        """Test language detection with MLX-Whisper error."""
        mock_transcribe.side_effect = Exception("MLX error")
        
        with tempfile.NamedTemporaryFile(suffix='.mp3') as temp_file:
            with pytest.raises(LanguageDetectionError, match="Language detection failed"):
                self.service.detect_language(temp_file.name)


class TestTranscription:
    """Test transcription functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.service = TranscriptionService()
    
    @patch('mlx_whisper.transcribe')
    def test_successful_transcription(self, mock_transcribe):
        """Test successful audio transcription."""
        mock_transcribe.return_value = {
            'text': 'Hello world. This is a test.',
            'language': 'en',
            'segments': [
                {
                    'start': 0.0,
                    'end': 5.0,
                    'text': 'Hello world.',
                    'avg_logprob': -0.2
                },
                {
                    'start': 5.0,
                    'end': 10.0,
                    'text': 'This is a test.',
                    'avg_logprob': -0.3
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(suffix='.mp3') as temp_file:
            result = self.service.transcribe_audio(temp_file.name)
            
            assert isinstance(result, TranscriptionResult)
            assert result.text == 'Hello world. This is a test.'
            assert result.language == 'en'
            assert len(result.segments) == 2
            assert 0.0 <= result.confidence <= 1.0
    
    def test_transcription_missing_file(self):
        """Test transcription with missing file."""
        with pytest.raises(AudioProcessingError, match="Audio file not found"):
            self.service.transcribe_audio("/nonexistent/file.mp3")
    
    @patch('mlx_whisper.transcribe')
    def test_transcription_mlx_error(self, mock_transcribe):
        """Test transcription with MLX-Whisper error."""
        mock_transcribe.side_effect = Exception("MLX transcription error")
        
        with tempfile.NamedTemporaryFile(suffix='.mp3') as temp_file:
            with pytest.raises(TranscriptionError, match="Transcription failed"):
                self.service.transcribe_audio(temp_file.name)
    
    def test_paragraph_boundary_detection(self):
        """Test paragraph boundary detection logic."""
        service = self.service
        
        # First segment should always be paragraph start
        assert service._detect_paragraph_boundary({}, None, True)
        
        # Long time gap should trigger paragraph break
        current = {'start': 10.0, 'text': 'New paragraph'}
        previous = {'end': 7.0, 'text': 'Previous sentence.'}
        assert service._detect_paragraph_boundary(current, previous, False)
        
        # Sentence ending with capitalized start should trigger break
        current = {'start': 5.0, 'text': 'So this is new'}
        previous = {'end': 4.5, 'text': 'Previous sentence.'}
        assert service._detect_paragraph_boundary(current, previous, False)
    
    def test_confidence_calculation(self):
        """Test confidence score calculation."""
        service = self.service
        
        # Test with confidence scores
        segments_with_confidence = [
            {'confidence': 0.9},
            {'confidence': 0.8},
            {'confidence': 0.7}
        ]
        confidence = service._calculate_confidence(segments_with_confidence)
        assert abs(confidence - 0.8) < 0.001  # Average (allow for floating point precision)
        
        # Test with log probabilities
        segments_with_logprob = [
            {'avg_logprob': -0.1},
            {'avg_logprob': -0.2}
        ]
        confidence = service._calculate_confidence(segments_with_logprob)
        assert 0.0 <= confidence <= 1.0
        
        # Test fallback calculation
        segments_basic = [
            {'text': 'Valid segment'},
            {'text': ''},  # Empty segment
            {'text': 'Another valid'}
        ]
        confidence = service._calculate_confidence(segments_basic)
        assert confidence == 2/3  # 2 valid out of 3


class TestOutputGeneration:
    """Test transcription output generation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.service = TranscriptionService()
        self.episode_metadata = EpisodeMetadata(
            podcast_title="Test Podcast",
            episode_title="Test Episode",
            episode_number=1,
            publication_date=datetime(2024, 1, 15),
            duration="30:00",
            description="Test episode description",
            audio_url="https://example.com/audio.mp3"
        )
        self.transcription_result = TranscriptionResult(
            text="Hello world. This is a test transcription.",
            segments=[
                TranscriptionSegment(0.0, 5.0, "Hello world.", True),
                TranscriptionSegment(5.0, 10.0, "This is a test transcription.", True)  # Make this a paragraph start
            ],
            language="en",
            confidence=0.95
        )
    
    def test_filename_generation(self):
        """Test markdown filename generation."""
        filename = self.service._generate_filename(self.episode_metadata)
        assert filename == "test_podcast_ep001.md"
        
        # Test without episode number
        metadata_no_number = EpisodeMetadata(
            podcast_title="Test Podcast",
            episode_title="Test Episode",
            episode_number=None,
            publication_date=datetime(2024, 1, 15),
            duration="30:00",
            description="Test description",
            audio_url="https://example.com/audio.mp3"
        )
        filename = self.service._generate_filename(metadata_no_number)
        assert filename == "test_podcast_episode_20240115.md"
    
    def test_filename_sanitization(self):
        """Test filename sanitization."""
        service = self.service
        
        # Test invalid characters
        result = service._sanitize_filename("Test<>Podcast:/\\|?*")
        assert result == "test_podcast"
        
        # Test spaces and length
        result = service._sanitize_filename("Very Long Podcast Name That Exceeds Fifty Characters Limit")
        assert len(result) <= 50
        assert ' ' not in result
    
    def test_markdown_content_formatting(self):
        """Test markdown content formatting."""
        content = self.service._format_markdown_content(
            self.transcription_result, 
            self.episode_metadata
        )
        
        # Check frontmatter
        assert '---' in content
        assert 'podcast_title: Test Podcast' in content
        assert 'episode_title: Test Episode' in content
        assert 'language: en' in content
        assert 'confidence: 0.95' in content
        
        # Check content structure
        assert '# Test Episode' in content
        assert '## Episode Description' in content
        assert '## Transcription' in content
        assert 'Test episode description' in content
    
    def test_transcription_text_formatting(self):
        """Test transcription text paragraph formatting."""
        formatted = self.service._format_transcription_text(self.transcription_result)
        
        # Should have paragraph breaks
        paragraphs = formatted.split('\n\n')
        assert len(paragraphs) == 2
        assert paragraphs[0] == "Hello world."
        assert paragraphs[1] == "This is a test transcription."
    
    def test_markdown_output_generation(self):
        """Test complete markdown file generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = self.service.generate_markdown_output(
                self.transcription_result,
                self.episode_metadata,
                output_dir=temp_dir
            )
            
            # Check file was created
            assert os.path.exists(output_path)
            assert output_path.endswith('.md')
            
            # Check file content
            with open(output_path, 'r', encoding='utf-8') as f:
                content = f.read()
                assert 'Test Podcast' in content
                assert 'Hello world' in content
                assert 'confidence: 0.95' in content
    
    def test_output_generation_file_error(self):
        """Test output generation with file operation error."""
        # Try to write to invalid directory
        with pytest.raises(FileOperationError, match="Failed to generate output file"):
            self.service.generate_markdown_output(
                self.transcription_result,
                self.episode_metadata,
                output_dir="/invalid/readonly/path"
            )


class TestMLXWhisperIntegration:
    """Test MLX-Whisper integration scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.service = TranscriptionService()
    
    def test_mlx_whisper_import_error(self):
        """Test handling of missing MLX-Whisper package."""
        with patch('builtins.__import__', side_effect=ImportError):
            with pytest.raises(LanguageDetectionError, match="MLX-Whisper not available"):
                self.service.detect_language("test.mp3")
            
            with pytest.raises(TranscriptionError, match="MLX-Whisper not available"):
                self.service.transcribe_audio("test.mp3")