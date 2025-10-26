"""Media downloader with progress tracking and resume capability."""

import os
import time
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any, Callable
from urllib.parse import urlparse
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from podknow.exceptions import DownloadError, ValidationError


class MediaInfo:
    """Container for media file information."""
    
    def __init__(
        self,
        file_path: str,
        file_size: int,
        content_type: str,
        duration: Optional[float] = None,
    ):
        self.file_path = file_path
        self.file_size = file_size
        self.content_type = content_type
        self.duration = duration


class DownloadProgress:
    """Progress tracking for downloads."""
    
    def __init__(self, total_size: int):
        self.total_size = total_size
        self.downloaded = 0
        self.start_time = time.time()
        self.last_update = time.time()
    
    @property
    def percentage(self) -> float:
        """Calculate download percentage."""
        if self.total_size == 0:
            return 0.0
        return (self.downloaded / self.total_size) * 100
    
    @property
    def speed(self) -> float:
        """Calculate download speed in bytes per second."""
        elapsed = time.time() - self.start_time
        if elapsed == 0:
            return 0.0
        return self.downloaded / elapsed
    
    @property
    def eta(self) -> Optional[float]:
        """Estimate time remaining in seconds."""
        if self.speed == 0 or self.downloaded == 0:
            return None
        remaining_bytes = self.total_size - self.downloaded
        return remaining_bytes / self.speed


class MediaDownloader:
    """Robust media downloader with progress tracking and resume capability."""
    
    SUPPORTED_FORMATS = {
        'audio/mpeg': '.mp3',
        'audio/mp4': '.m4a',
        'audio/x-m4a': '.m4a',
        'audio/aac': '.aac',
        'audio/wav': '.wav',
        'audio/ogg': '.ogg',
        'video/mp4': '.mp4',
        'video/quicktime': '.mov',
        'video/x-msvideo': '.avi',
    }
    
    def __init__(
        self,
        chunk_size: int = 8192,
        max_retries: int = 3,
        backoff_factor: float = 0.3,
        timeout: int = 30,
    ):
        """Initialize the media downloader.
        
        Args:
            chunk_size: Size of chunks to download at a time
            max_retries: Maximum number of retry attempts
            backoff_factor: Factor for exponential backoff
            timeout: Request timeout in seconds
        """
        self.chunk_size = chunk_size
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.timeout = timeout
        
        # Configure session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set user agent
        self.session.headers.update({
            'User-Agent': 'PodKnow/0.1.0 (Podcast Transcription Tool)'
        })
    
    def download_with_progress(
        self,
        url: str,
        destination: str,
        progress_callback: Optional[Callable[[DownloadProgress], None]] = None,
        resume: bool = True,
    ) -> bool:
        """Download media file with progress tracking and resume capability.
        
        Args:
            url: URL to download from
            destination: Local file path to save to
            progress_callback: Optional callback for progress updates
            resume: Whether to resume partial downloads
            
        Returns:
            True if download successful, False otherwise
            
        Raises:
            DownloadError: If download fails after all retries
        """
        try:
            destination_path = Path(destination)
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Check if file already exists and get size for resume
            existing_size = 0
            if resume and destination_path.exists():
                existing_size = destination_path.stat().st_size
            
            # Get file info from server
            head_response = self._make_request('HEAD', url)
            total_size = int(head_response.headers.get('content-length', 0))
            content_type = head_response.headers.get('content-type', '')
            
            # Validate content type
            if not self._is_supported_format(content_type):
                raise ValidationError(f"Unsupported media format: {content_type}")
            
            # Check if file is already complete
            if existing_size == total_size and total_size > 0:
                if self.validate_media_file(destination):
                    return True
            
            # Set up headers for resume
            headers = {}
            if resume and existing_size > 0 and existing_size < total_size:
                headers['Range'] = f'bytes={existing_size}-'
            else:
                existing_size = 0  # Start from beginning
            
            # Start download
            response = self._make_request('GET', url, headers=headers, stream=True)
            
            # Initialize progress tracking
            if total_size == 0:
                total_size = existing_size + int(response.headers.get('content-length', 0))
            
            progress = DownloadProgress(total_size)
            progress.downloaded = existing_size
            
            # Open file for writing (append if resuming)
            mode = 'ab' if resume and existing_size > 0 else 'wb'
            
            with open(destination, mode) as file:
                for chunk in response.iter_content(chunk_size=self.chunk_size):
                    if chunk:  # Filter out keep-alive chunks
                        file.write(chunk)
                        progress.downloaded += len(chunk)
                        
                        # Call progress callback
                        if progress_callback and time.time() - progress.last_update > 0.1:
                            progress_callback(progress)
                            progress.last_update = time.time()
            
            # Final progress update
            if progress_callback:
                progress_callback(progress)
            
            # Validate downloaded file
            if not self.validate_media_file(destination):
                raise ValidationError(f"Downloaded file failed validation: {destination}")
            
            return True
            
        except requests.RequestException as e:
            raise DownloadError(f"Failed to download {url}: {str(e)}")
        except OSError as e:
            raise DownloadError(f"File system error: {str(e)}")
    
    def validate_media_file(self, file_path: str) -> bool:
        """Validate that a media file is not corrupted.
        
        Args:
            file_path: Path to the media file
            
        Returns:
            True if file appears valid, False otherwise
        """
        try:
            path = Path(file_path)
            if not path.exists():
                return False
            
            # Check file size
            if path.stat().st_size == 0:
                return False
            
            # Basic format validation by reading first few bytes
            with open(file_path, 'rb') as file:
                header = file.read(12)
                
                # Check for common audio/video file signatures
                if len(header) < 4:
                    return False
                
                # MP3 files start with ID3 tag or MPEG frame sync
                if header.startswith(b'ID3') or header[:2] in [b'\xff\xfb', b'\xff\xf3', b'\xff\xf2']:
                    return True
                
                # MP4/M4A files have 'ftyp' box
                if b'ftyp' in header[:12]:
                    return True
                
                # WAV files start with RIFF
                if header.startswith(b'RIFF') and b'WAVE' in header:
                    return True
                
                # OGG files start with 'OggS'
                if header.startswith(b'OggS'):
                    return True
                
                # For other formats, assume valid if we got this far
                return True
                
        except (OSError, IOError):
            return False
    
    def get_media_info(self, file_path: str) -> MediaInfo:
        """Get information about a media file.
        
        Args:
            file_path: Path to the media file
            
        Returns:
            MediaInfo object with file details
            
        Raises:
            ValidationError: If file doesn't exist or is invalid
        """
        path = Path(file_path)
        if not path.exists():
            raise ValidationError(f"File does not exist: {file_path}")
        
        file_size = path.stat().st_size
        
        # Determine content type from file extension
        suffix = path.suffix.lower()
        content_type = 'application/octet-stream'  # Default
        
        for mime_type, ext in self.SUPPORTED_FORMATS.items():
            if suffix == ext:
                content_type = mime_type
                break
        
        return MediaInfo(
            file_path=str(path),
            file_size=file_size,
            content_type=content_type,
        )
    
    def _make_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Make HTTP request with error handling.
        
        Args:
            method: HTTP method
            url: URL to request
            **kwargs: Additional arguments for requests
            
        Returns:
            Response object
            
        Raises:
            DownloadError: If request fails
        """
        try:
            kwargs.setdefault('timeout', self.timeout)
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            raise DownloadError(f"HTTP request failed: {str(e)}")
    
    def _is_supported_format(self, content_type: str) -> bool:
        """Check if content type is supported.
        
        Args:
            content_type: MIME type to check
            
        Returns:
            True if supported, False otherwise
        """
        # Handle content types with parameters (e.g., "audio/mpeg; charset=utf-8")
        base_type = content_type.split(';')[0].strip().lower()
        return base_type in self.SUPPORTED_FORMATS
    
    def get_file_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Hexadecimal hash string
        """
        hash_sha256 = hashlib.sha256()
        with open(file_path, 'rb') as file:
            for chunk in iter(lambda: file.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def cleanup_partial_download(self, file_path: str) -> None:
        """Remove a partial download file.
        
        Args:
            file_path: Path to the partial file
        """
        try:
            Path(file_path).unlink(missing_ok=True)
        except OSError:
            pass  # Ignore cleanup errors