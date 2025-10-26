"""Abstract interface for media download services."""

from abc import ABC, abstractmethod
from typing import Optional, Callable, Dict, Any
from pathlib import Path


class MediaDownloaderInterface(ABC):
    """Abstract interface for media download services."""
    
    @abstractmethod
    async def download_media(
        self,
        url: str,
        destination: Path,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> bool:
        """
        Download media file from URL to destination.
        
        Args:
            url: Media file URL
            destination: Local file path for download
            progress_callback: Optional callback for download progress (bytes_downloaded, total_bytes)
            
        Returns:
            True if download successful, False otherwise
            
        Raises:
            DownloadError: When download fails
        """
        pass
    
    @abstractmethod
    async def get_media_info(self, url: str) -> Dict[str, Any]:
        """
        Get information about media file without downloading.
        
        Args:
            url: Media file URL
            
        Returns:
            Dictionary containing media information (size, type, duration, etc.)
            
        Raises:
            DownloadError: When media info cannot be retrieved
        """
        pass
    
    @abstractmethod
    async def validate_media_url(self, url: str) -> bool:
        """
        Validate that the URL points to a valid media file.
        
        Args:
            url: Media file URL to validate
            
        Returns:
            True if URL is valid and accessible, False otherwise
        """
        pass
    
    @abstractmethod
    async def resume_download(
        self,
        url: str,
        destination: Path,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> bool:
        """
        Resume a partially downloaded media file.
        
        Args:
            url: Media file URL
            destination: Local file path for download
            progress_callback: Optional callback for download progress
            
        Returns:
            True if resume successful, False otherwise
            
        Raises:
            DownloadError: When resume fails
        """
        pass
    
    @property
    @abstractmethod
    def supported_formats(self) -> List[str]:
        """Return list of supported media formats."""
        pass
    
    @property
    @abstractmethod
    def max_file_size(self) -> Optional[int]:
        """Return maximum supported file size in bytes, or None for no limit."""
        pass