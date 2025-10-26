"""Episode processing orchestrator for download and transcription."""

import os
import json
import time
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

from podknow.models.podcast import Episode
from podknow.models.transcription import Transcription
from podknow.services.media.downloader import MediaDownloader, DownloadProgress
from podknow.services.media.transcription import TranscriptionEngine, TranscriptionProgress
from podknow.exceptions import TranscriptionError, DownloadError, ValidationError


class ProcessingStatus:
    """Status tracking for episode processing."""
    
    def __init__(self, episode: Episode):
        self.episode = episode
        self.status = "pending"  # pending, downloading, transcribing, complete, failed
        self.progress = 0.0
        self.message = ""
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.error: Optional[str] = None
        self.download_path: Optional[str] = None
        self.transcription: Optional[Transcription] = None
    
    @property
    def duration(self) -> Optional[float]:
        """Get processing duration in seconds."""
        if not self.start_time:
            return None
        end_time = self.end_time or datetime.now()
        return (end_time - self.start_time).total_seconds()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert status to dictionary for serialization."""
        return {
            "episode_title": self.episode.title,
            "episode_id": self.episode.episode_id,
            "podcast_id": self.episode.podcast_id,
            "status": self.status,
            "progress": self.progress,
            "message": self.message,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.duration,
            "error": self.error,
            "download_path": self.download_path,
            "has_transcription": self.transcription is not None,
        }


class BatchProcessingStatus:
    """Status tracking for batch processing operations."""
    
    def __init__(self, episodes: List[Episode]):
        self.episodes = episodes
        self.statuses = {ep.episode_id or str(hash(ep.media_url)): ProcessingStatus(ep) for ep in episodes}
        self.start_time = datetime.now()
        self.end_time: Optional[datetime] = None
    
    @property
    def total_episodes(self) -> int:
        """Get total number of episodes."""
        return len(self.episodes)
    
    @property
    def completed_episodes(self) -> int:
        """Get number of completed episodes."""
        return sum(1 for status in self.statuses.values() if status.status == "complete")
    
    @property
    def failed_episodes(self) -> int:
        """Get number of failed episodes."""
        return sum(1 for status in self.statuses.values() if status.status == "failed")
    
    @property
    def overall_progress(self) -> float:
        """Get overall batch progress percentage."""
        if not self.statuses:
            return 0.0
        total_progress = sum(status.progress for status in self.statuses.values())
        return total_progress / len(self.statuses)
    
    @property
    def is_complete(self) -> bool:
        """Check if batch processing is complete."""
        return all(status.status in ["complete", "failed"] for status in self.statuses.values())
    
    def get_status(self, episode_id: str) -> Optional[ProcessingStatus]:
        """Get status for a specific episode."""
        return self.statuses.get(episode_id)


class EpisodeProcessor:
    """Orchestrates episode download and transcription with batch processing."""
    
    def __init__(
        self,
        output_directory: str = "~/Documents/PodKnow",
        downloader: Optional[MediaDownloader] = None,
        transcription_engine: Optional[TranscriptionEngine] = None,
        max_concurrent_downloads: int = 3,
        max_concurrent_transcriptions: int = 1,  # MLX-Whisper works best with single threading
        resume_processing: bool = True,
    ):
        """Initialize the episode processor.
        
        Args:
            output_directory: Base directory for storing files
            downloader: Media downloader instance
            transcription_engine: Transcription engine instance
            max_concurrent_downloads: Maximum concurrent downloads
            max_concurrent_transcriptions: Maximum concurrent transcriptions
            resume_processing: Whether to resume interrupted processing
        """
        self.output_directory = Path(output_directory).expanduser()
        self.output_directory.mkdir(parents=True, exist_ok=True)
        
        self.downloader = downloader or MediaDownloader()
        self.transcription_engine = transcription_engine or TranscriptionEngine()
        
        self.max_concurrent_downloads = max_concurrent_downloads
        self.max_concurrent_transcriptions = max_concurrent_transcriptions
        self.resume_processing = resume_processing
        
        # Status tracking
        self.status_file = self.output_directory / "processing_status.json"
        self._load_status_cache()
        
        self.logger = logging.getLogger(__name__)
    
    def process_episode(
        self,
        episode: Episode,
        progress_callback: Optional[Callable[[ProcessingStatus], None]] = None,
        skip_existing: bool = True,
    ) -> ProcessingStatus:
        """Process a single episode (download and transcribe).
        
        Args:
            episode: Episode to process
            progress_callback: Optional callback for progress updates
            skip_existing: Whether to skip already processed episodes
            
        Returns:
            ProcessingStatus with results
        """
        episode_id = episode.episode_id or str(hash(episode.media_url))
        status = ProcessingStatus(episode)
        status.start_time = datetime.now()
        
        try:
            # Check if already processed
            if skip_existing and self._is_episode_processed(episode):
                status.status = "complete"
                status.progress = 100.0
                status.message = "Already processed"
                if progress_callback:
                    progress_callback(status)
                return status
            
            # Create episode directory
            episode_dir = self._get_episode_directory(episode)
            episode_dir.mkdir(parents=True, exist_ok=True)
            
            # Download media file
            status.status = "downloading"
            status.message = "Downloading media file..."
            if progress_callback:
                progress_callback(status)
            
            download_path = self._download_episode(episode, episode_dir, status, progress_callback)
            status.download_path = download_path
            
            # Transcribe audio
            status.status = "transcribing"
            status.progress = 50.0  # Download complete, transcription starting
            status.message = "Transcribing audio..."
            if progress_callback:
                progress_callback(status)
            
            transcription = self._transcribe_episode(download_path, status, progress_callback)
            status.transcription = transcription
            
            # Save transcription
            self._save_transcription(episode, transcription, episode_dir)
            
            # Mark as complete
            status.status = "complete"
            status.progress = 100.0
            status.message = "Processing complete"
            status.end_time = datetime.now()
            
            if progress_callback:
                progress_callback(status)
            
            self.logger.info(f"Successfully processed episode: {episode.title}")
            
        except Exception as e:
            status.status = "failed"
            status.error = str(e)
            status.end_time = datetime.now()
            status.message = f"Failed: {str(e)}"
            
            if progress_callback:
                progress_callback(status)
            
            self.logger.error(f"Failed to process episode {episode.title}: {str(e)}")
        
        # Update status cache
        self._update_status_cache(episode_id, status)
        
        return status
    
    def process_episodes_batch(
        self,
        episodes: List[Episode],
        progress_callback: Optional[Callable[[BatchProcessingStatus], None]] = None,
        skip_existing: bool = True,
    ) -> BatchProcessingStatus:
        """Process multiple episodes with concurrent downloads and sequential transcription.
        
        Args:
            episodes: List of episodes to process
            progress_callback: Optional callback for batch progress updates
            skip_existing: Whether to skip already processed episodes
            
        Returns:
            BatchProcessingStatus with results
        """
        batch_status = BatchProcessingStatus(episodes)
        
        def episode_progress_callback(episode_status: ProcessingStatus) -> None:
            """Update batch status when individual episode progresses."""
            episode_id = episode_status.episode.episode_id or str(hash(episode_status.episode.media_url))
            batch_status.statuses[episode_id] = episode_status
            
            if progress_callback:
                progress_callback(batch_status)
        
        # Process episodes with controlled concurrency
        with ThreadPoolExecutor(max_workers=self.max_concurrent_downloads) as executor:
            # Submit all episodes for processing
            future_to_episode = {
                executor.submit(
                    self.process_episode,
                    episode,
                    episode_progress_callback,
                    skip_existing
                ): episode
                for episode in episodes
            }
            
            # Wait for completion
            for future in as_completed(future_to_episode):
                episode = future_to_episode[future]
                try:
                    status = future.result()
                    episode_id = episode.episode_id or str(hash(episode.media_url))
                    batch_status.statuses[episode_id] = status
                except Exception as e:
                    self.logger.error(f"Unexpected error processing {episode.title}: {str(e)}")
        
        batch_status.end_time = datetime.now()
        
        if progress_callback:
            progress_callback(batch_status)
        
        self.logger.info(
            f"Batch processing complete: {batch_status.completed_episodes}/{batch_status.total_episodes} "
            f"successful, {batch_status.failed_episodes} failed"
        )
        
        return batch_status
    
    def _download_episode(
        self,
        episode: Episode,
        episode_dir: Path,
        status: ProcessingStatus,
        progress_callback: Optional[Callable[[ProcessingStatus], None]] = None,
    ) -> str:
        """Download episode media file.
        
        Args:
            episode: Episode to download
            episode_dir: Directory to save file in
            status: Processing status to update
            progress_callback: Progress callback
            
        Returns:
            Path to downloaded file
            
        Raises:
            DownloadError: If download fails
        """
        # Determine file extension from URL or content type
        file_extension = self._get_file_extension(str(episode.media_url))
        filename = f"{self._sanitize_filename(episode.title)}{file_extension}"
        download_path = episode_dir / filename
        
        def download_progress_callback(download_progress: DownloadProgress) -> None:
            """Update status with download progress."""
            # Map download progress to first 50% of overall progress
            status.progress = (download_progress.percentage / 100) * 50
            status.message = f"Downloading... {download_progress.percentage:.1f}%"
            
            if progress_callback:
                progress_callback(status)
        
        success = self.downloader.download_with_progress(
            str(episode.media_url),
            str(download_path),
            download_progress_callback,
            resume=self.resume_processing,
        )
        
        if not success:
            raise DownloadError(f"Failed to download episode: {episode.title}")
        
        return str(download_path)
    
    def _transcribe_episode(
        self,
        file_path: str,
        status: ProcessingStatus,
        progress_callback: Optional[Callable[[ProcessingStatus], None]] = None,
    ) -> Transcription:
        """Transcribe episode audio file.
        
        Args:
            file_path: Path to audio file
            status: Processing status to update
            progress_callback: Progress callback
            
        Returns:
            Transcription object
            
        Raises:
            TranscriptionError: If transcription fails
        """
        def transcription_progress_callback(transcription_progress: TranscriptionProgress) -> None:
            """Update status with transcription progress."""
            # Map transcription progress to second 50% of overall progress
            base_progress = 50.0
            transcription_contribution = (transcription_progress.percentage / 100) * 50
            status.progress = base_progress + transcription_contribution
            status.message = f"Transcribing... {transcription_progress.stage}"
            
            if progress_callback:
                progress_callback(status)
        
        return self.transcription_engine.transcribe_audio(
            file_path,
            transcription_progress_callback,
        )
    
    def _save_transcription(
        self,
        episode: Episode,
        transcription: Transcription,
        episode_dir: Path,
    ) -> None:
        """Save transcription to file.
        
        Args:
            episode: Episode metadata
            transcription: Transcription to save
            episode_dir: Directory to save in
        """
        # Save as JSON for programmatic access
        transcription_file = episode_dir / "transcription.json"
        with open(transcription_file, 'w', encoding='utf-8') as f:
            json.dump(transcription.model_dump(), f, indent=2, ensure_ascii=False)
        
        # Save as markdown for human reading
        markdown_file = episode_dir / "transcript.md"
        with open(markdown_file, 'w', encoding='utf-8') as f:
            f.write(f"# {episode.title}\n\n")
            f.write(f"**Podcast:** {episode.podcast_id}\n")
            f.write(f"**Published:** {episode.publication_date.strftime('%Y-%m-%d')}\n")
            f.write(f"**Duration:** {episode.duration // 60}:{episode.duration % 60:02d}\n")
            f.write(f"**Language:** {transcription.language}\n")
            f.write(f"**Model:** {transcription.model_used}\n")
            f.write(f"**Confidence:** {transcription.confidence:.2f}\n\n")
            f.write("## Transcript\n\n")
            f.write(transcription.text)
    
    def _get_episode_directory(self, episode: Episode) -> Path:
        """Get directory path for episode files.
        
        Args:
            episode: Episode to get directory for
            
        Returns:
            Path to episode directory
        """
        podcast_dir = self.output_directory / self._sanitize_filename(episode.podcast_id)
        episode_name = f"{episode.publication_date.strftime('%Y-%m-%d')}_{self._sanitize_filename(episode.title)}"
        return podcast_dir / episode_name
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for filesystem compatibility.
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename
        """
        # Remove or replace problematic characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # Limit length and strip whitespace
        return filename.strip()[:100]
    
    def _get_file_extension(self, url: str) -> str:
        """Get file extension from URL.
        
        Args:
            url: Media URL
            
        Returns:
            File extension with dot
        """
        from urllib.parse import urlparse
        
        parsed = urlparse(url)
        path = parsed.path.lower()
        
        # Common podcast media extensions
        if path.endswith('.mp3'):
            return '.mp3'
        elif path.endswith('.m4a'):
            return '.m4a'
        elif path.endswith('.mp4'):
            return '.mp4'
        elif path.endswith('.wav'):
            return '.wav'
        elif path.endswith('.ogg'):
            return '.ogg'
        else:
            return '.mp3'  # Default fallback
    
    def _is_episode_processed(self, episode: Episode) -> bool:
        """Check if episode has already been processed.
        
        Args:
            episode: Episode to check
            
        Returns:
            True if already processed, False otherwise
        """
        episode_dir = self._get_episode_directory(episode)
        transcription_file = episode_dir / "transcription.json"
        return transcription_file.exists()
    
    def _load_status_cache(self) -> None:
        """Load processing status cache from disk."""
        self.status_cache = {}
        if self.status_file.exists():
            try:
                with open(self.status_file, 'r') as f:
                    self.status_cache = json.load(f)
            except (json.JSONDecodeError, OSError):
                self.logger.warning("Failed to load status cache, starting fresh")
    
    def _update_status_cache(self, episode_id: str, status: ProcessingStatus) -> None:
        """Update status cache and save to disk.
        
        Args:
            episode_id: Episode identifier
            status: Processing status
        """
        self.status_cache[episode_id] = status.to_dict()
        
        try:
            with open(self.status_file, 'w') as f:
                json.dump(self.status_cache, f, indent=2)
        except OSError:
            self.logger.warning("Failed to save status cache")
    
    def get_processing_history(self) -> Dict[str, Any]:
        """Get processing history from cache.
        
        Returns:
            Dictionary with processing history
        """
        return self.status_cache.copy()
    
    def cleanup_failed_downloads(self) -> int:
        """Clean up partial downloads from failed processing.
        
        Returns:
            Number of files cleaned up
        """
        cleaned_count = 0
        
        for podcast_dir in self.output_directory.iterdir():
            if not podcast_dir.is_dir():
                continue
                
            for episode_dir in podcast_dir.iterdir():
                if not episode_dir.is_dir():
                    continue
                
                # Look for media files without corresponding transcription
                media_files = list(episode_dir.glob("*.[mp3|m4a|mp4|wav|ogg]*"))
                transcription_file = episode_dir / "transcription.json"
                
                if media_files and not transcription_file.exists():
                    # Remove partial downloads
                    for media_file in media_files:
                        try:
                            media_file.unlink()
                            cleaned_count += 1
                            self.logger.info(f"Cleaned up partial download: {media_file}")
                        except OSError:
                            pass
        
        return cleaned_count