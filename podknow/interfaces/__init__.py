"""Abstract interfaces and base classes for PodKnow components."""

from .discovery import PodcastDiscoveryInterface
from .analyzer import ContentAnalyzerInterface
from .downloader import MediaDownloaderInterface

__all__ = [
    "PodcastDiscoveryInterface",
    "ContentAnalyzerInterface",
    "MediaDownloaderInterface",
]