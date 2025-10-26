"""
Unit tests for data models.
"""

import pytest
from datetime import datetime
from podknow.models.podcast import PodcastResult, PodcastMetadata
from podknow.models.episode import Episode, EpisodeMetadata
from podknow.models.transcription import TranscriptionSegment, TranscriptionResult
from podknow.models.analysis import SponsorSegment, AnalysisResult
from podknow.models.output import OutputDocument


class TestPodcastResult:
    """Test PodcastResult data model."""
    
    def test_valid_podcast_result(self):
        """Test creating a valid PodcastResult."""
        result = PodcastResult(
            title="Test Podcast",
            author="Test Author",
            rss_url="https://example.com/feed.xml",
            platform="iTunes",
            description="Test description"
        )
        assert result.title == "Test Podcast"
        assert result.author == "Test Author"
        assert result.rss_url == "https://example.com/feed.xml"
        assert result.platform == "iTunes"
        assert result.description == "Test description"
    
    def test_empty_title_raises_error(self):
        """Test that empty title raises ValueError."""
        with pytest.raises(ValueError, match="Podcast title is required"):
            PodcastResult(
                title="",
                author="Test Author",
                rss_url="https://example.com/feed.xml",
                platform="iTunes",
                description="Test description"
            )
    
    def test_empty_author_raises_error(self):
        """Test that empty author raises ValueError."""
        with pytest.raises(ValueError, match="Podcast author is required"):
            PodcastResult(
                title="Test Podcast",
                author="",
                rss_url="https://example.com/feed.xml",
                platform="iTunes",
                description="Test description"
            )
    
    def test_empty_rss_url_raises_error(self):
        """Test that empty RSS URL raises ValueError."""
        with pytest.raises(ValueError, match="RSS URL is required"):
            PodcastResult(
                title="Test Podcast",
                author="Test Author",
                rss_url="",
                platform="iTunes",
                description="Test description"
            )


class TestPodcastMetadata:
    """Test PodcastMetadata data model."""
    
    def test_valid_podcast_metadata(self):
        """Test creating valid PodcastMetadata."""
        metadata = PodcastMetadata(
            title="Test Podcast",
            author="Test Author",
            description="Test description",
            rss_url="https://example.com/feed.xml",
            episode_count=10,
            last_updated=datetime.now()
        )
        assert metadata.title == "Test Podcast"
        assert metadata.episode_count == 10
    
    def test_negative_episode_count_raises_error(self):
        """Test that negative episode count raises ValueError."""
        with pytest.raises(ValueError, match="Episode count must be non-negative"):
            PodcastMetadata(
                title="Test Podcast",
                author="Test Author",
                description="Test description",
                rss_url="https://example.com/feed.xml",
                episode_count=-1,
                last_updated=datetime.now()
            )


class TestEpisode:
    """Test Episode data model."""
    
    def test_valid_episode(self):
        """Test creating a valid Episode."""
        episode = Episode(
            id="ep123",
            title="Test Episode",
            description="Test description",
            audio_url="https://example.com/audio.mp3",
            publication_date=datetime.now(),
            duration="30:00"
        )
        assert episode.id == "ep123"
        assert episode.title == "Test Episode"
        assert episode.duration == "30:00"
    
    def test_empty_id_raises_error(self):
        """Test that empty ID raises ValueError."""
        with pytest.raises(ValueError, match="Episode ID is required"):
            Episode(
                id="",
                title="Test Episode",
                description="Test description",
                audio_url="https://example.com/audio.mp3",
                publication_date=datetime.now(),
                duration="30:00"
            )


class TestEpisodeMetadata:
    """Test EpisodeMetadata data model."""
    
    def test_valid_episode_metadata(self):
        """Test creating valid EpisodeMetadata."""
        metadata = EpisodeMetadata(
            podcast_title="Test Podcast",
            episode_title="Test Episode",
            episode_number=1,
            publication_date=datetime.now(),
            duration="30:00",
            description="Test description",
            audio_url="https://example.com/audio.mp3",
            file_size=1024
        )
        assert metadata.podcast_title == "Test Podcast"
        assert metadata.episode_number == 1
        assert metadata.file_size == 1024


class TestTranscriptionSegment:
    """Test TranscriptionSegment data model."""
    
    def test_valid_transcription_segment(self):
        """Test creating a valid TranscriptionSegment."""
        segment = TranscriptionSegment(
            start_time=0.0,
            end_time=5.0,
            text="Hello world",
            is_paragraph_start=True
        )
        assert segment.start_time == 0.0
        assert segment.end_time == 5.0
        assert segment.text == "Hello world"
        assert segment.is_paragraph_start is True
    
    def test_negative_start_time_raises_error(self):
        """Test that negative start time raises ValueError."""
        with pytest.raises(ValueError, match="Start time must be non-negative"):
            TranscriptionSegment(
                start_time=-1.0,
                end_time=5.0,
                text="Hello world"
            )
    
    def test_end_time_before_start_raises_error(self):
        """Test that end time before start time raises ValueError."""
        with pytest.raises(ValueError, match="End time must be greater than start time"):
            TranscriptionSegment(
                start_time=5.0,
                end_time=3.0,
                text="Hello world"
            )
    
    def test_empty_text_raises_error(self):
        """Test that empty text raises ValueError."""
        with pytest.raises(ValueError, match="Segment text cannot be empty"):
            TranscriptionSegment(
                start_time=0.0,
                end_time=5.0,
                text="   "
            )


class TestTranscriptionResult:
    """Test TranscriptionResult data model."""
    
    def test_valid_transcription_result(self):
        """Test creating a valid TranscriptionResult."""
        segments = [
            TranscriptionSegment(0.0, 5.0, "Hello world"),
            TranscriptionSegment(5.0, 10.0, "This is a test")
        ]
        result = TranscriptionResult(
            text="Hello world. This is a test.",
            segments=segments,
            language="en",
            confidence=0.95
        )
        assert result.text == "Hello world. This is a test."
        assert len(result.segments) == 2
        assert result.language == "en"
        assert result.confidence == 0.95
    
    def test_invalid_confidence_raises_error(self):
        """Test that invalid confidence raises ValueError."""
        with pytest.raises(ValueError, match="Confidence must be between 0.0 and 1.0"):
            TranscriptionResult(
                text="Hello world",
                segments=[],
                language="en",
                confidence=1.5
            )


class TestSponsorSegment:
    """Test SponsorSegment data model."""
    
    def test_valid_sponsor_segment(self):
        """Test creating a valid SponsorSegment."""
        segment = SponsorSegment(
            start_text="This episode is sponsored by",
            end_text="Back to the show",
            confidence=0.8
        )
        assert segment.start_text == "This episode is sponsored by"
        assert segment.end_text == "Back to the show"
        assert segment.confidence == 0.8
    
    def test_empty_start_text_raises_error(self):
        """Test that empty start text raises ValueError."""
        with pytest.raises(ValueError, match="Start text cannot be empty"):
            SponsorSegment(
                start_text="",
                end_text="Back to the show",
                confidence=0.8
            )


class TestAnalysisResult:
    """Test AnalysisResult data model."""
    
    def test_valid_analysis_result(self):
        """Test creating a valid AnalysisResult."""
        result = AnalysisResult(
            summary="This episode discusses technology trends.",
            topics=["AI", "Machine Learning", "Technology"],
            keywords=["artificial intelligence", "ML", "tech"],
            sponsor_segments=[]
        )
        assert result.summary == "This episode discusses technology trends."
        assert len(result.topics) == 3
        assert len(result.keywords) == 3
    
    def test_empty_topics_raises_error(self):
        """Test that empty topics list raises ValueError."""
        with pytest.raises(ValueError, match="At least one topic is required"):
            AnalysisResult(
                summary="Test summary",
                topics=[],
                keywords=["test"],
                sponsor_segments=[]
            )
    
    def test_empty_keywords_raises_error(self):
        """Test that empty keywords list raises ValueError."""
        with pytest.raises(ValueError, match="At least one keyword is required"):
            AnalysisResult(
                summary="Test summary",
                topics=["test"],
                keywords=[],
                sponsor_segments=[]
            )


class TestOutputDocument:
    """Test OutputDocument data model."""
    
    def test_valid_output_document(self):
        """Test creating a valid OutputDocument."""
        metadata = EpisodeMetadata(
            podcast_title="Test Podcast",
            episode_title="Test Episode",
            episode_number=1,
            publication_date=datetime.now(),
            duration="30:00",
            description="Test description",
            audio_url="https://example.com/audio.mp3"
        )
        analysis = AnalysisResult(
            summary="Test summary",
            topics=["test"],
            keywords=["test"],
            sponsor_segments=[]
        )
        document = OutputDocument(
            metadata=metadata,
            transcription="This is the transcription text.",
            analysis=analysis,
            processing_timestamp=datetime.now()
        )
        assert document.transcription == "This is the transcription text."
        assert isinstance(document.metadata, EpisodeMetadata)
        assert isinstance(document.analysis, AnalysisResult)
    
    def test_empty_transcription_raises_error(self):
        """Test that empty transcription raises ValueError."""
        metadata = EpisodeMetadata(
            podcast_title="Test Podcast",
            episode_title="Test Episode",
            episode_number=1,
            publication_date=datetime.now(),
            duration="30:00",
            description="Test description",
            audio_url="https://example.com/audio.mp3"
        )
        analysis = AnalysisResult(
            summary="Test summary",
            topics=["test"],
            keywords=["test"],
            sponsor_segments=[]
        )
        with pytest.raises(ValueError, match="Transcription cannot be empty"):
            OutputDocument(
                metadata=metadata,
                transcription="   ",
                analysis=analysis,
                processing_timestamp=datetime.now()
            )