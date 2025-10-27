"""
Configuration manager implementation.
"""

import os
import re
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

from .models import Config
from ..exceptions import ConfigurationError


class ConfigManager:
    """Manages configuration loading and validation."""
    
    DEFAULT_CONFIG_PATH = Path.home() / ".podknow" / "config.md"
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize config manager with optional custom path."""
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
    
    def load_config(self) -> Config:
        """Load configuration from markdown file."""
        if not self.config_path.exists():
            raise ConfigurationError(f"Configuration file not found at {self.config_path}")
        
        try:
            content = self.config_path.read_text(encoding='utf-8')
            config_data = self._parse_markdown_config(content)
            return Config(**config_data)
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration: {str(e)}")
    
    def validate_config(self, config: Config) -> bool:
        """Validate configuration."""
        try:
            # Basic validation is handled in Config.__post_init__
            # Additional validation can be added here
            if not config.claude_api_key.strip():
                raise ConfigurationError("Claude API key cannot be empty")
            
            # Validate required prompt templates
            required_prompts = ['summary', 'topics', 'keywords', 'sponsor_detection']
            for prompt_type in required_prompts:
                if prompt_type not in config.prompts:
                    raise ConfigurationError(f"Missing required prompt template: {prompt_type}")
                if not config.prompts[prompt_type].strip():
                    raise ConfigurationError(f"Prompt template '{prompt_type}' cannot be empty")
            
            return True
        except Exception as e:
            raise ConfigurationError(f"Configuration validation failed: {str(e)}")
    
    def get_prompt_template(self, config: Config, prompt_type: str) -> str:
        """Get a specific prompt template from configuration."""
        if prompt_type not in config.prompts:
            raise ConfigurationError(f"Prompt template '{prompt_type}' not found in configuration")
        return config.prompts[prompt_type]
    
    def _parse_markdown_config(self, content: str) -> Dict[str, Any]:
        """Parse markdown configuration file and extract structured data."""
        config_data = {
            'claude_api_key': '',
            'prompts': {},
            'analysis_settings': {},
            'output_settings': {}
        }
        
        # Extract YAML blocks
        yaml_blocks = re.findall(r'```yaml\n(.*?)\n```', content, re.DOTALL)
        for yaml_block in yaml_blocks:
            try:
                yaml_data = yaml.safe_load(yaml_block)
                if isinstance(yaml_data, dict):
                    # Merge YAML data into config
                    for key, value in yaml_data.items():
                        if key in config_data:
                            if isinstance(config_data[key], dict) and isinstance(value, dict):
                                config_data[key].update(value)
                            else:
                                config_data[key] = value
            except yaml.YAMLError as e:
                raise ConfigurationError(f"Invalid YAML in configuration: {str(e)}")
        
        # Extract prompt templates
        prompt_sections = {
            'summary': r'### Summary Prompt\n```\n(.*?)\n```',
            'topics': r'### Topic Extraction Prompt\n```\n(.*?)\n```',
            'keywords': r'### Keyword Identification Prompt\n```\n(.*?)\n```',
            'sponsor_detection': r'### Sponsor Detection Prompt\n```\n(.*?)\n```'
        }
        
        for prompt_type, pattern in prompt_sections.items():
            match = re.search(pattern, content, re.DOTALL)
            if match:
                config_data['prompts'][prompt_type] = match.group(1).strip()
        
        return config_data
    
    def create_default_config(self) -> None:
        """Create a default configuration file."""
        # Read the default config template
        try:
            from pathlib import Path
            import pkg_resources
            
            # Try to read from package resources first
            try:
                default_config_content = pkg_resources.resource_string(
                    'podknow.config', 'default_config.md'
                ).decode('utf-8')
            except:
                # Fallback to reading from file system
                default_config_path = Path(__file__).parent / 'default_config.md'
                if default_config_path.exists():
                    default_config_content = default_config_path.read_text(encoding='utf-8')
                else:
                    # Use embedded default if file not found
                    default_config_content = self._get_embedded_default_config()
            
        except Exception:
            # Use embedded default as last resort
            default_config_content = self._get_embedded_default_config()
        
        # Create directory if it doesn't exist
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write default config
        self.config_path.write_text(default_config_content, encoding='utf-8')
    
    def _get_embedded_default_config(self) -> str:
        """Get embedded default configuration as fallback."""
        return '''# PodKnow Configuration

This is the default configuration file for PodKnow. Customize it according to your needs.

## API Keys

```yaml
claude_api_key: "your-claude-api-key-here"
spotify_client_id: "your-spotify-client-id"  # Optional
spotify_client_secret: "your-spotify-client-secret"  # Optional
```

## Analysis Prompts

### Summary Prompt

```
Analyze this podcast transcription and provide a concise summary in 2-3 paragraphs. 
Focus on the main points, key insights, and overall theme of the episode. 
Be objective and informative, highlighting the most important takeaways for readers.
Avoid speculation and stick to what was actually discussed in the episode.
```

### Topic Extraction Prompt

```
Extract the main topics discussed in this podcast episode. 
List each topic in one sentence that captures the essence of what was discussed about that topic.
Focus on substantial topics that received meaningful discussion time.
Return only the topic sentences, one per line, without numbering or bullets.
Aim for 3-8 topics depending on the episode length and content diversity.
```

### Keyword Identification Prompt

```
Identify relevant keywords and tags for this podcast content. 
Focus on specific terms, concepts, people, companies, technologies, or methodologies mentioned.
Include both explicit mentions and implicit themes that would help categorize this content.
Return only the keywords separated by commas, without explanations.
Prioritize terms that would be useful for search and categorization.
```

### Sponsor Detection Prompt

```
Identify any sponsored content or advertisements in this transcription. 
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

Be conservative - only mark content as sponsored if you're reasonably confident it's promotional.
```

## Output Settings

```yaml
# Default output directory for transcriptions
output_directory: "~/Documents/PodKnow"

# Filename template for generated files
filename_template: "{podcast_title}_{episode_number}_{date}.md"

# Whether to include timestamps in transcription segments
include_timestamps: true

# Enable paragraph detection using Whisper's built-in capabilities
paragraph_detection: true

# Maximum file size for audio downloads (in MB)
max_audio_size_mb: 500

# Temporary directory for audio files (leave empty for system default)
temp_directory: ""
```

## Transcription Settings

```yaml
# MLX-Whisper specific settings
whisper_model: "base"
use_fp16: true
language: "en"
word_timestamps: true

# Audio processing settings
supported_formats: [".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"]
download_timeout: 300
chunk_size: 8192
```

## Analysis Settings

```yaml
# Claude API settings
claude_model: "claude-3-5-sonnet-20241022"
max_tokens: 4000
temperature: 0.1

# Retry settings for API calls
max_retries: 3
retry_delay: 1.0

# Content processing
min_transcription_length: 100
max_analysis_length: 50000
```

## Logging Settings

```yaml
# Log level: DEBUG, INFO, WARNING, ERROR
log_level: "INFO"

# Log file location (leave empty to disable file logging)
log_file: "~/.podknow/logs/podknow.log"

# Maximum log file size in MB
max_log_size_mb: 10

# Number of backup log files to keep
log_backup_count: 5
```

## Discovery Settings

```yaml
# Default search settings
default_search_limit: 20
search_timeout: 10

# Platform priorities (higher numbers = higher priority)
platform_priorities:
  itunes: 10
  spotify: 5

# Result deduplication settings
similarity_threshold: 0.8
```

---

## Getting Started

1. Set your Claude API key in the `claude_api_key` field above
2. Optionally configure Spotify credentials for enhanced podcast discovery
3. Customize the analysis prompts to match your needs
4. Adjust output and logging settings as desired

For more information, see the PodKnow documentation.
'''
    
    def generate_config_for_first_time_setup(self) -> str:
        """Generate configuration file for first-time setup and return the path."""
        if not self.config_exists():
            self.create_default_config()
            return str(self.config_path)
        else:
            # Config already exists, return existing path
            return str(self.config_path)
    
    def get_config_status(self) -> Dict[str, Any]:
        """Get configuration status information."""
        status = {
            'config_exists': self.config_exists(),
            'config_path': str(self.config_path),
            'config_directory': str(self.config_path.parent),
            'is_valid': False,
            'missing_keys': [],
            'validation_errors': []
        }
        
        if status['config_exists']:
            try:
                config = self.load_config()
                status['is_valid'] = self.validate_config(config)
                
                # Check for missing API keys
                if not config.claude_api_key:
                    status['missing_keys'].append('claude_api_key')
                
            except Exception as e:
                status['validation_errors'].append(str(e))
        
        return status
    
    def config_exists(self) -> bool:
        """Check if configuration file exists."""
        return self.config_path.exists()