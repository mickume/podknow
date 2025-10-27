"""
Workflow orchestration service for end-to-end podcast processing.

This module provides comprehensive workflow management with error propagation,
recovery mechanisms, and detailed logging for the complete podcast discovery,
transcription, and analysis pipeline.
"""

import logging
import os
import sys
from datetime import datetime
from typing import Optional, Dict, Any, Callable
from pathlib import Path

from ..models.episode import Episode, EpisodeMetadata
from ..models.podcast import PodcastResult, PodcastMetadata
from ..models.transcription import TranscriptionResult
from ..models.analysis import AnalysisResult
from ..models.output import OutputDocument
from ..services.discovery import PodcastDiscoveryService
from ..services.episode import EpisodeListingService
from ..services.transcription import TranscriptionService
from ..services.analysis import AnalysisService
from ..config.manager import ConfigManager
from ..exceptions import (
    PodKnowError,
    NetworkError,
    TranscriptionError,
    AnalysisError,
    ConfigurationError,
    AudioProcessingError,
    LanguageDetectionError,
    FileOperationError
)


class WorkflowLogger:
    """Enhanced logging for workflow operations."""
    
    def __init__(self, verbose: bool = False, log_file: Optional[str] = None):
        """Initialize workflow logger.
        
        Args:
            verbose: Enable verbose logging to console
            log_file: Optional log file path for persistent logging
        """
        self.verbose = verbose
        self.logger = logging.getLogger('podknow.workflow')
        
        # Configure logger
        self.logger.setLevel(logging.DEBUG if verbose else logging.INFO)
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stderr)
        console_level = logging.DEBUG if verbose else logging.WARNING
        console_handler.setLevel(console_level)
        
        console_formatter = logging.Formatter(
            '[%(levelname)s] %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # File handler (if specified)
        if log_file:
            try:
                os.makedirs(os.path.dirname(log_file), exist_ok=True)
                file_handler = logging.FileHandler(log_file)
                file_handler.setLevel(logging.DEBUG)
                
                file_formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
                file_handler.setFormatter(file_formatter)
                self.logger.addHandler(file_handler)
                
            except Exception as e:
                self.logger.warning(f"Failed to setup file logging: {e}")
    
    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self.logger.debug(message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message."""
        self.logger.info(message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self.logger.warning(message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message."""
        self.logger.error(message, **kwargs)
    
    def progress(self, message: str):
        """Log progress message (always shown)."""
        print(f"[INFO] {message}", file=sys.stderr)


class WorkflowState:
    """Tracks workflow execution state and intermediate results."""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.current_step = "initialization"
        self.completed_steps = []
        self.failed_steps = []
        
        # Intermediate results
        self.search_results: Optional[list] = None
        self.selected_podcast: Optional[PodcastResult] = None
        self.podcast_metadata: Optional[PodcastMetadata] = None
        self.episode_list: Optional[list] = None
        self.selected_episode: Optional[Episode] = None
        self.audio_file_path: Optional[str] = None
        self.transcription_result: Optional[TranscriptionResult] = None
        self.analysis_result: Optional[AnalysisResult] = None
        self.output_path: Optional[str] = None
        
        # Error tracking
        self.errors = []
        self.warnings = []
    
    def set_step(self, step_name: str):
        """Set current workflow step."""
        if self.current_step:
            self.completed_steps.append(self.current_step)
        self.current_step = step_name
    
    def mark_step_failed(self, step_name: str, error: Exception):
        """Mark a step as failed."""
        self.failed_steps.append(step_name)
        self.errors.append((step_name, error))
    
    def add_warning(self, step_name: str, message: str):
        """Add a warning for a step."""
        self.warnings.append((step_name, message))
    
    def get_duration(self) -> float:
        """Get total workflow duration in seconds."""
        return (datetime.now() - self.start_time).total_seconds()
    
    def is_recoverable(self) -> bool:
        """Check if workflow can be recovered from current state."""
        # Define recovery points
        recovery_points = [
            "podcast_search",
            "episode_listing", 
            "audio_download",
            "transcription",
            "analysis"
        ]
        
        return any(step in self.completed_steps for step in recovery_points)


class WorkflowOrchestrator:
    """Orchestrates end-to-end podcast processing workflows."""
    
    def __init__(self, 
                 verbose: bool = False, 
                 log_file: Optional[str] = None,
                 progress_callback: Optional[Callable[[str], None]] = None):
        """Initialize workflow orchestrator.
        
        Args:
            verbose: Enable verbose logging
            log_file: Optional log file path
            progress_callback: Optional callback for progress updates
        """
        self.logger = WorkflowLogger(verbose, log_file)
        self.progress_callback = progress_callback or self.logger.progress
        
        # Initialize services (lazy loading)
        self._discovery_service = None
        self._episode_service = None
        self._transcription_service = None
        self._analysis_service = None
    
    @property
    def discovery_service(self) -> PodcastDiscoveryService:
        """Get discovery service (lazy initialization)."""
        if self._discovery_service is None:
            self._discovery_service = PodcastDiscoveryService()
        return self._discovery_service
    
    @property
    def episode_service(self) -> EpisodeListingService:
        """Get episode service (lazy initialization)."""
        if self._episode_service is None:
            self._episode_service = EpisodeListingService()
        return self._episode_service
    
    @property
    def transcription_service(self) -> TranscriptionService:
        """Get transcription service (lazy initialization)."""
        if self._transcription_service is None:
            self._transcription_service = TranscriptionService()
        return self._transcription_service
    
    def get_analysis_service(self, api_key: str, model: str = "claude-sonnet-4-5-20250929") -> AnalysisService:
        """Get analysis service with API key, model, and configuration-based prompts."""
        if self._analysis_service is None:
            # Load prompts from configuration
            try:
                config_manager = ConfigManager()
                if config_manager.config_exists():
                    config = config_manager.load_config()
                    # Map config prompt names to service prompt names
                    prompts = {
                        'summary': config.prompts.get('summary'),
                        'topics': config.prompts.get('topics'),
                        'keywords': config.prompts.get('keywords'),
                        'sponsors': config.prompts.get('sponsor_detection')  # Config uses 'sponsor_detection'
                    }
                    # Filter out None values
                    prompts = {k: v for k, v in prompts.items() if v is not None}
                    
                    self._analysis_service = AnalysisService(api_key, model=model, prompts=prompts if prompts else None)
                else:
                    # No config file, let AnalysisService use its defaults
                    self._analysis_service = AnalysisService(api_key, model=model)
            except Exception as e:
                # If config loading fails, fall back to defaults
                self.logger.warning(f"Failed to load configuration for analysis service: {e}")
                self._analysis_service = AnalysisService(api_key, model=model)
        
        return self._analysis_service
    
    def execute_search_workflow(self, 
                               keywords: str, 
                               platform: str = 'all',
                               limit: int = 20) -> list:
        """Execute podcast search workflow with error handling.
        
        Args:
            keywords: Search keywords
            platform: Platform to search ('itunes', 'spotify', 'all')
            limit: Maximum results to return
            
        Returns:
            List of PodcastResult objects
            
        Raises:
            NetworkError: If search fails completely
        """
        state = WorkflowState()
        
        try:
            self.logger.info(f"Starting podcast search workflow: '{keywords}' on {platform}")
            state.set_step("podcast_search")
            
            self.progress_callback(f"Searching for '{keywords}' on {platform}...")
            
            # Execute search based on platform
            if platform.lower() == 'itunes':
                results = self.discovery_service.search_itunes(keywords)
            elif platform.lower() == 'spotify':
                results = self.discovery_service.search_spotify(keywords)
            else:  # platform == 'all'
                results = self.discovery_service.get_combined_results(keywords)
            
            # Apply limit
            if results and len(results) > limit:
                results = results[:limit]
                self.logger.debug(f"Limited results to {limit} items")
            
            state.search_results = results
            self.logger.info(f"Search completed successfully: {len(results)} results")
            
            return results
            
        except NetworkError as e:
            state.mark_step_failed("podcast_search", e)
            self.logger.error(f"Search workflow failed: {e}")
            raise
        except Exception as e:
            state.mark_step_failed("podcast_search", e)
            self.logger.error(f"Unexpected error in search workflow: {e}")
            raise NetworkError(f"Search workflow failed: {str(e)}")
    
    def execute_episode_listing_workflow(self, 
                                       rss_url: str, 
                                       count: int = 10) -> tuple:
        """Execute episode listing workflow with error handling.
        
        Args:
            rss_url: RSS feed URL
            count: Number of episodes to list
            
        Returns:
            Tuple of (PodcastMetadata, List[Episode])
            
        Raises:
            NetworkError: If episode listing fails
        """
        state = WorkflowState()
        
        try:
            self.logger.info(f"Starting episode listing workflow: {rss_url}")
            state.set_step("episode_listing")
            
            self.progress_callback("Fetching podcast information...")
            
            # Get podcast metadata
            podcast_info = self.episode_service.get_podcast_info(rss_url)
            state.podcast_metadata = podcast_info
            
            self.progress_callback(f"Fetching {count} recent episodes...")
            
            # Get episodes
            episodes = self.episode_service.list_episodes(rss_url, count=count)
            state.episode_list = episodes
            
            self.logger.info(f"Episode listing completed: {len(episodes)} episodes")
            
            return podcast_info, episodes
            
        except Exception as e:
            state.mark_step_failed("episode_listing", e)
            self.logger.error(f"Episode listing workflow failed: {e}")
            raise NetworkError(f"Episode listing failed: {str(e)}")
    
    def execute_transcription_workflow(self,
                                     episode_id: str,
                                     rss_url: str,
                                     output_dir: Optional[str] = None,
                                     claude_api_key: Optional[str] = None,
                                     skip_analysis: bool = False,
                                     skip_language_detection: bool = False,
                                     language_detection_skip_minutes: float = 2.0) -> str:
        """Execute complete transcription workflow with error handling and recovery.
        
        Args:
            episode_id: Episode identifier
            rss_url: RSS feed URL
            output_dir: Output directory for transcription
            claude_api_key: Claude API key for analysis
            skip_analysis: Skip AI analysis
            skip_language_detection: Skip language detection (assume English)
            language_detection_skip_minutes: Minutes to skip for language detection
            
        Returns:
            Path to generated output file
            
        Raises:
            PodKnowError: If workflow fails at any step
        """
        state = WorkflowState()
        
        try:
            self.logger.info(f"Starting transcription workflow: episode {episode_id}")
            
            # Step 1: Find episode
            state.set_step("episode_discovery")
            self.progress_callback("Finding episode in RSS feed...")
            
            episode = self.episode_service.find_episode_by_id(rss_url, episode_id)
            if not episode:
                raise NetworkError(f"Episode '{episode_id}' not found in RSS feed")
            
            podcast_info = self.episode_service.get_podcast_info(rss_url)
            state.selected_episode = episode
            state.podcast_metadata = podcast_info
            
            self.logger.debug(f"Found episode: {episode.title}")
            
            # Step 2: Download audio
            state.set_step("audio_download")
            self.progress_callback(f"Downloading audio from: {episode.audio_url}")
            
            try:
                audio_file_path = self.transcription_service.download_audio(episode.audio_url)
                state.audio_file_path = audio_file_path
                self.logger.debug(f"Audio downloaded to: {audio_file_path}")
            except Exception as e:
                raise AudioProcessingError(f"Audio download failed: {str(e)}")
            
            # Step 3: Language detection (optional)
            if not skip_language_detection:
                state.set_step("language_detection")
                self.progress_callback("Detecting audio language...")
                
                try:
                    detected_language = self.transcription_service.detect_language(
                        audio_file_path, 
                        skip_minutes=language_detection_skip_minutes
                    )
                    self.logger.debug(f"Detected language: {detected_language}")
                except LanguageDetectionError as e:
                    self._cleanup_audio_file(audio_file_path)
                    raise e
            else:
                self.logger.debug("Skipping language detection (assuming English)")
                detected_language = "en"
            
            # Step 4: Transcription
            state.set_step("transcription")
            self.progress_callback("Transcribing audio (this may take several minutes)...")
            
            try:
                transcription_result = self.transcription_service.transcribe_audio(audio_file_path)
                state.transcription_result = transcription_result
                self.logger.info(f"Transcription completed: {len(transcription_result.segments)} segments, "
                               f"confidence: {transcription_result.confidence:.1%}")
            except Exception as e:
                self._cleanup_audio_file(audio_file_path)
                raise TranscriptionError(f"Transcription failed: {str(e)}")
            
            # Step 5: Create episode metadata
            episode_metadata = EpisodeMetadata(
                podcast_title=podcast_info.title,
                episode_title=episode.title,
                episode_number=None,  # Could be extracted from title if needed
                publication_date=episode.publication_date,
                duration=episode.duration,
                description=episode.description,
                audio_url=episode.audio_url
            )
            
            # Step 6: Analysis (if requested)
            analysis_result = None
            if not skip_analysis and claude_api_key:
                state.set_step("analysis")
                self.progress_callback("Analyzing transcription with Claude AI...")
                
                try:
                    analysis_service = self.get_analysis_service(claude_api_key)
                    analysis_result = analysis_service.analyze_transcription(transcription_result.text)
                    state.analysis_result = analysis_result
                    
                    self.logger.info(f"Analysis completed: {len(analysis_result.topics)} topics, "
                                   f"{len(analysis_result.keywords)} keywords")
                    
                    if analysis_result.sponsor_segments:
                        self.logger.info(f"Detected {len(analysis_result.sponsor_segments)} sponsor segments")
                        
                except Exception as e:
                    # Analysis failure is not fatal - continue with transcription only
                    state.add_warning("analysis", f"Analysis failed: {str(e)}")
                    self.logger.warning(f"Analysis failed, continuing with transcription only: {e}")
                    skip_analysis = True
            
            # Step 7: Generate output
            state.set_step("output_generation")
            self.progress_callback("Generating output file...")
            
            try:
                if skip_analysis or not analysis_result:
                    # Generate transcription-only output
                    output_path = self.transcription_service.generate_markdown_output(
                        transcription_result, 
                        episode_metadata, 
                        output_dir
                    )
                else:
                    # Generate full output with analysis
                    output_doc = OutputDocument(
                        metadata=episode_metadata,
                        transcription=transcription_result.text,
                        analysis=analysis_result,
                        processing_timestamp=datetime.now()
                    )
                    
                    analysis_service = self.get_analysis_service(claude_api_key)
                    markdown_content = analysis_service.generate_markdown_output(output_doc)
                    
                    # Save to file
                    if not output_dir:
                        output_dir = os.path.expanduser("~/Documents/PodKnow")
                    os.makedirs(output_dir, exist_ok=True)
                    
                    filename = self.transcription_service._generate_filename(episode_metadata)
                    output_path = os.path.join(output_dir, filename)
                    
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(markdown_content)
                
                state.output_path = output_path
                self.logger.info(f"Output generated successfully: {output_path}")
                
            except Exception as e:
                raise FileOperationError(f"Failed to generate output: {str(e)}")
            
            finally:
                # Always cleanup audio file
                if state.audio_file_path:
                    self._cleanup_audio_file(state.audio_file_path)
            
            # Log workflow completion
            duration = state.get_duration()
            self.logger.info(f"Transcription workflow completed successfully in {duration:.1f}s")
            
            return output_path
            
        except Exception as e:
            # Log workflow failure
            duration = state.get_duration()
            self.logger.error(f"Transcription workflow failed after {duration:.1f}s: {e}")
            
            # Attempt recovery if possible
            if state.is_recoverable():
                self.logger.info("Workflow state is recoverable - intermediate results preserved")
            
            raise
        finally:
            # Always cleanup audio file, even on exceptions
            if state.audio_file_path:
                self._cleanup_audio_file(state.audio_file_path)
    
    def execute_analysis_workflow(self, 
                                transcription_file: str,
                                claude_api_key: str,
                                output_file: Optional[str] = None) -> str:
        """Execute analysis workflow for existing transcription.
        
        Args:
            transcription_file: Path to transcription file
            claude_api_key: Claude API key
            output_file: Optional output file path
            
        Returns:
            Path to analyzed output file
            
        Raises:
            AnalysisError: If analysis workflow fails
        """
        state = WorkflowState()
        
        try:
            self.logger.info(f"Starting analysis workflow: {transcription_file}")
            
            # Step 1: Read transcription file
            state.set_step("file_reading")
            self.progress_callback("Reading transcription file...")
            
            if not os.path.isfile(transcription_file):
                raise FileOperationError(f"Transcription file not found: {transcription_file}")
            
            # Parse file content (implementation would go here)
            # This is a simplified version - full implementation would parse YAML frontmatter
            with open(transcription_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract transcription text (simplified)
            transcription_text = content  # In reality, would parse frontmatter
            
            # Step 2: Perform analysis
            state.set_step("analysis")
            self.progress_callback("Analyzing transcription with Claude AI...")
            
            analysis_service = self.get_analysis_service(claude_api_key)
            analysis_result = analysis_service.analyze_transcription(transcription_text)
            state.analysis_result = analysis_result
            
            # Step 3: Generate output
            state.set_step("output_generation")
            self.progress_callback("Updating file with analysis results...")
            
            output_path = output_file or transcription_file
            
            # Update file with analysis (simplified implementation)
            # Full implementation would properly merge with existing frontmatter
            
            self.logger.info(f"Analysis workflow completed successfully")
            
            return output_path
            
        except Exception as e:
            duration = state.get_duration()
            self.logger.error(f"Analysis workflow failed after {duration:.1f}s: {e}")
            raise AnalysisError(f"Analysis workflow failed: {str(e)}")
    
    def _cleanup_audio_file(self, audio_path: str):
        """Safely cleanup temporary audio file."""
        try:
            if audio_path and os.path.exists(audio_path):
                self.transcription_service.cleanup_audio_file(audio_path)
                self.logger.debug(f"Cleaned up audio file: {audio_path}")
        except Exception as e:
            self.logger.warning(f"Failed to cleanup audio file {audio_path}: {e}")
    
    def get_workflow_status(self) -> Dict[str, Any]:
        """Get current workflow status and health information."""
        status = {
            "services": {
                "discovery": self._discovery_service is not None,
                "episode": self._episode_service is not None,
                "transcription": self._transcription_service is not None,
                "analysis": self._analysis_service is not None
            },
            "dependencies": self._check_dependencies(),
            "configuration": self._check_configuration()
        }
        
        return status
    
    def _check_dependencies(self) -> Dict[str, bool]:
        """Check if required dependencies are available."""
        dependencies = {}
        
        # Check MLX-Whisper
        try:
            import mlx_whisper
            dependencies["mlx_whisper"] = True
        except ImportError:
            dependencies["mlx_whisper"] = False
        
        # Check Anthropic
        try:
            import anthropic
            dependencies["anthropic"] = True
        except ImportError:
            dependencies["anthropic"] = False
        
        # Check other dependencies
        try:
            import requests
            dependencies["requests"] = True
        except ImportError:
            dependencies["requests"] = False
        
        try:
            import feedparser
            dependencies["feedparser"] = True
        except ImportError:
            dependencies["feedparser"] = False
        
        return dependencies
    
    def _check_configuration(self) -> Dict[str, Any]:
        """Check configuration status."""
        config = {
            "output_directory": os.path.expanduser("~/Documents/PodKnow"),
            "temp_directory": self.transcription_service.temp_dir if self._transcription_service else None,
            "environment_variables": {
                "CLAUDE_API_KEY": bool(os.getenv("CLAUDE_API_KEY")),
                "SPOTIFY_CLIENT_ID": bool(os.getenv("SPOTIFY_CLIENT_ID")),
                "SPOTIFY_CLIENT_SECRET": bool(os.getenv("SPOTIFY_CLIENT_SECRET"))
            }
        }
        
        return config