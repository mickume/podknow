"""
Exception hierarchy for PodKnow application.

This module defines all custom exceptions used throughout the application
for proper error handling and user feedback.
"""


class PodKnowError(Exception):
    """Base exception for PodKnow application."""
    
    def __init__(self, message: str, details: str = None):
        self.message = message
        self.details = details
        super().__init__(self.message)


class NetworkError(PodKnowError):
    """Network-related errors including API timeouts and connection failures."""
    pass


class TranscriptionError(PodKnowError):
    """Audio processing and transcription errors."""
    pass


class AnalysisError(PodKnowError):
    """AI analysis and API errors."""
    pass


class ConfigurationError(PodKnowError):
    """Configuration and setup errors."""
    pass


class ValidationError(PodKnowError):
    """Data validation errors."""
    pass


class AudioProcessingError(TranscriptionError):
    """Specific audio processing errors."""
    pass


class LanguageDetectionError(TranscriptionError):
    """Language detection specific errors."""
    pass


class APIError(NetworkError):
    """Generic API error."""
    
    def __init__(self, message: str, status_code: int = None, details: str = None):
        self.status_code = status_code
        super().__init__(message, details)


class iTunesAPIError(APIError):
    """iTunes API specific errors."""
    pass


class SpotifyAPIError(APIError):
    """Spotify API specific errors."""
    pass


class ClaudeAPIError(APIError):
    """Claude AI API specific errors."""
    pass


class RSSParsingError(PodKnowError):
    """RSS feed parsing errors."""
    pass


class FileOperationError(PodKnowError):
    """File system operation errors."""
    pass


class EpisodeManagementError(PodKnowError):
    """Episode management and listing errors."""
    pass