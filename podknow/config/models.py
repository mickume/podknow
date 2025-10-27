"""
Configuration data models.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from pathlib import Path
import os

from ..constants import DEFAULT_CLAUDE_MODEL


@dataclass
class Config:
    """Enhanced configuration model for PodKnow application."""
    
    # API Keys
    claude_api_key: Optional[str] = None
    spotify_client_id: Optional[str] = None
    spotify_client_secret: Optional[str] = None
    
    # Output settings
    output_directory: str = "~/Documents/PodKnow"
    filename_template: str = "{podcast_title}_{episode_number}_{date}.md"
    include_timestamps: bool = True
    paragraph_detection: bool = True
    max_audio_size_mb: int = 500
    temp_directory: str = ""
    
    # Analysis settings
    claude_model: str = DEFAULT_CLAUDE_MODEL
    max_tokens: int = 4000
    temperature: float = 0.1
    max_retries: int = 3
    retry_delay: float = 1.0
    min_transcription_length: int = 100
    max_analysis_length: int = 50000
    
    # Transcription settings
    whisper_model: str = "base"
    use_fp16: bool = True
    language: str = "en"
    word_timestamps: bool = True
    supported_formats: list = field(default_factory=lambda: [".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"])
    download_timeout: int = 300
    chunk_size: int = 8192
    
    # Logging settings
    log_level: str = "INFO"
    log_file: Optional[str] = None
    verbose: bool = False
    max_log_size_mb: int = 10
    log_backup_count: int = 5
    
    # Discovery settings
    default_search_limit: int = 20
    search_timeout: int = 10
    platform_priorities: Dict[str, int] = field(default_factory=lambda: {"itunes": 10, "spotify": 5})
    similarity_threshold: float = 0.8
    
    # Analysis prompts
    prompts: Dict[str, str] = field(default_factory=dict)
    
    # Legacy compatibility
    analysis_settings: Dict[str, Any] = field(default_factory=dict)
    output_settings: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate and normalize configuration data."""
        # Expand user paths
        self.output_directory = os.path.expanduser(self.output_directory)
        if self.log_file:
            self.log_file = os.path.expanduser(self.log_file)
        if self.temp_directory:
            self.temp_directory = os.path.expanduser(self.temp_directory)
        
        # Load environment variables if not set
        if not self.claude_api_key:
            self.claude_api_key = os.getenv('CLAUDE_API_KEY')
        if not self.spotify_client_id:
            self.spotify_client_id = os.getenv('SPOTIFY_CLIENT_ID')
        if not self.spotify_client_secret:
            self.spotify_client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
        
        # Override with environment variables if set
        if os.getenv('PODKNOW_OUTPUT_DIR'):
            self.output_directory = os.path.expanduser(os.getenv('PODKNOW_OUTPUT_DIR'))
        if os.getenv('PODKNOW_LOG_LEVEL'):
            self.log_level = os.getenv('PODKNOW_LOG_LEVEL')
        if os.getenv('PODKNOW_LOG_FILE'):
            self.log_file = os.path.expanduser(os.getenv('PODKNOW_LOG_FILE'))
        
        # Set default prompts if not provided
        if not self.prompts:
            self.prompts = self._get_default_prompts()
        
        # Migrate legacy settings
        if self.analysis_settings:
            self._migrate_analysis_settings()
        if self.output_settings:
            self._migrate_output_settings()
    
    def _get_default_prompts(self) -> Dict[str, str]:
        """Get default analysis prompts."""
        return {
            "summary": """Analyze this podcast transcription and provide a concise summary in 2-3 paragraphs. 
Focus on the main points, key insights, and overall theme of the episode. 
Be objective and informative, highlighting the most important takeaways for readers.
Avoid speculation and stick to what was actually discussed in the episode.""",
            
            "topics": """Extract the main topics discussed in this podcast episode. 
List each topic in one sentence that captures the essence of what was discussed about that topic.
Focus on substantial topics that received meaningful discussion time.
Return only the topic sentences, one per line, without numbering or bullets.
Aim for 3-8 topics depending on the episode length and content diversity.""",
            
            "keywords": """Identify relevant keywords and tags for this podcast content. 
Focus on specific terms, concepts, people, companies, technologies, or methodologies mentioned.
Include both explicit mentions and implicit themes that would help categorize this content.
Return only the keywords separated by commas, without explanations.
Prioritize terms that would be useful for search and categorization.""",
            
            "sponsor_detection": """Identify any sponsored content or advertisements in this transcription. 
Look for promotional language, product endorsements, discount codes, or clear advertising segments.
Pay attention to phrases like "this episode is sponsored by", "thanks to our sponsor", 
discount codes, special offers, or obvious product promotions.

For each sponsor segment found, provide:
1. The starting text (first few words where the sponsor content begins)
2. The ending text (last few words where the sponsor content ends)  
3. A confidence score from 0.0 to 1.0 indicating how certain you are this is sponsored content

Return the results in JSON format with this structure:
[{"start_text": "...", "end_text": "...", "confidence": 0.95}]

If no sponsor content is found, return an empty array: []

Be conservative - only mark content as sponsored if you're reasonably confident it's promotional."""
        }
    
    def _migrate_analysis_settings(self):
        """Migrate legacy analysis settings."""
        for key, value in self.analysis_settings.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def _migrate_output_settings(self):
        """Migrate legacy output settings."""
        for key, value in self.output_settings.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def validate(self) -> bool:
        """Validate configuration completeness."""
        # Claude API key is required for analysis
        if not self.claude_api_key:
            return False
        
        # Check that output directory is writable
        try:
            os.makedirs(self.output_directory, exist_ok=True)
            test_file = os.path.join(self.output_directory, '.podknow_test')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
        except (OSError, PermissionError):
            return False
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'claude_api_key': self.claude_api_key,
            'spotify_client_id': self.spotify_client_id,
            'spotify_client_secret': self.spotify_client_secret,
            'output_directory': self.output_directory,
            'filename_template': self.filename_template,
            'include_timestamps': self.include_timestamps,
            'paragraph_detection': self.paragraph_detection,
            'max_audio_size_mb': self.max_audio_size_mb,
            'temp_directory': self.temp_directory,
            'claude_model': self.claude_model,
            'max_tokens': self.max_tokens,
            'temperature': self.temperature,
            'max_retries': self.max_retries,
            'retry_delay': self.retry_delay,
            'min_transcription_length': self.min_transcription_length,
            'max_analysis_length': self.max_analysis_length,
            'whisper_model': self.whisper_model,
            'use_fp16': self.use_fp16,
            'language': self.language,
            'word_timestamps': self.word_timestamps,
            'supported_formats': self.supported_formats,
            'download_timeout': self.download_timeout,
            'chunk_size': self.chunk_size,
            'log_level': self.log_level,
            'log_file': self.log_file,
            'verbose': self.verbose,
            'max_log_size_mb': self.max_log_size_mb,
            'log_backup_count': self.log_backup_count,
            'default_search_limit': self.default_search_limit,
            'search_timeout': self.search_timeout,
            'platform_priorities': self.platform_priorities,
            'similarity_threshold': self.similarity_threshold,
            'prompts': self.prompts
        }