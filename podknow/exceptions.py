"""Custom exceptions for PodKnow."""


class PodKnowError(Exception):
    """Base exception for all PodKnow errors."""
    pass


class ConfigurationError(PodKnowError):
    """Raised when there are configuration-related errors."""
    pass


class DiscoveryError(PodKnowError):
    """Raised when podcast discovery operations fail."""
    pass


class SubscriptionError(PodKnowError):
    """Raised when subscription management operations fail."""
    pass


class DownloadError(PodKnowError):
    """Raised when media download operations fail."""
    pass


class TranscriptionError(PodKnowError):
    """Raised when transcription operations fail."""
    pass


class AnalysisError(PodKnowError):
    """Raised when content analysis operations fail."""
    pass


class TemplateError(PodKnowError):
    """Raised when template processing fails."""
    pass


class ValidationError(PodKnowError):
    """Raised when data validation fails."""
    pass