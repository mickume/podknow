"""Configuration management with YAML support and environment variable substitution."""

import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic import BaseModel, Field, ValidationError, validator


class PodcastDirectoryConfig(BaseModel):
    """Configuration for podcast directory APIs."""
    
    enabled: bool = True
    api_key: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None


class TranscriptionConfig(BaseModel):
    """Configuration for transcription engine."""
    
    engine: str = "mlx-whisper"
    model: str = "base"
    language_detection: bool = True
    english_only: bool = True


class AIAnalysisConfig(BaseModel):
    """Configuration for AI analysis providers."""
    
    primary_provider: str = "claude"
    claude: Dict[str, Any] = Field(default_factory=lambda: {
        "api_key": None,
        "model": "claude-3-sonnet"
    })
    ollama: Dict[str, Any] = Field(default_factory=lambda: {
        "base_url": "http://localhost:11434",
        "model": "llama2"
    })


class StorageConfig(BaseModel):
    """Configuration for local storage paths."""
    
    subscriptions_file: str = "~/.podknow/subscriptions.json"
    output_directory: str = "~/Documents/PodKnow"
    template_directory: str = "~/.podknow/templates"
    
    @validator('subscriptions_file', 'output_directory', 'template_directory')
    def expand_path(cls, v: str) -> str:
        """Expand user home directory in paths."""
        return str(Path(v).expanduser())


class PodKnowConfig(BaseModel):
    """Main configuration model for PodKnow."""
    
    podcast_directories: Dict[str, PodcastDirectoryConfig] = Field(
        default_factory=lambda: {
            "apple_podcasts": PodcastDirectoryConfig(),
            "spotify": PodcastDirectoryConfig()
        }
    )
    transcription: TranscriptionConfig = Field(default_factory=TranscriptionConfig)
    ai_analysis: AIAnalysisConfig = Field(default_factory=AIAnalysisConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)


class ConfigManager:
    """Manages configuration loading, validation, and environment variable substitution."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize ConfigManager with optional config file path."""
        self.config_path = config_path or Path.home() / ".podknow" / "config.yaml"
        self._config: Optional[PodKnowConfig] = None
    
    def load_config(self) -> PodKnowConfig:
        """Load and validate configuration from YAML file with environment variable substitution."""
        if self._config is not None:
            return self._config
        
        try:
            if not self.config_path.exists():
                # Create default config if it doesn't exist
                self._create_default_config()
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                raw_config = yaml.safe_load(f)
            
            if raw_config is None:
                raw_config = {}
            
            # Substitute environment variables
            substituted_config = self._substitute_env_vars(raw_config)
            
            # Validate configuration
            self._config = PodKnowConfig(**substituted_config)
            
            return self._config
            
        except FileNotFoundError:
            raise ConfigurationError(
                f"Configuration file not found: {self.config_path}. "
                "Run 'podknow init' to create a default configuration."
            )
        except yaml.YAMLError as e:
            raise ConfigurationError(
                f"Invalid YAML in configuration file {self.config_path}: {e}"
            )
        except ValidationError as e:
            raise ConfigurationError(
                f"Configuration validation failed: {self._format_validation_error(e)}"
            )
        except Exception as e:
            raise ConfigurationError(
                f"Failed to load configuration from {self.config_path}: {e}"
            )
    
    def reload_config(self) -> PodKnowConfig:
        """Reload configuration from file, discarding cached version."""
        self._config = None
        return self.load_config()
    
    def get_config(self) -> PodKnowConfig:
        """Get current configuration, loading if necessary."""
        if self._config is None:
            return self.load_config()
        return self._config
    
    def _create_default_config(self) -> None:
        """Create a default configuration file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        default_config = {
            "podcast_directories": {
                "apple_podcasts": {
                    "enabled": True,
                    "api_key": "${APPLE_PODCASTS_API_KEY}"
                },
                "spotify": {
                    "enabled": True,
                    "client_id": "${SPOTIFY_CLIENT_ID}",
                    "client_secret": "${SPOTIFY_CLIENT_SECRET}"
                }
            },
            "transcription": {
                "engine": "mlx-whisper",
                "model": "base",
                "language_detection": True,
                "english_only": True
            },
            "ai_analysis": {
                "primary_provider": "claude",
                "claude": {
                    "api_key": "${CLAUDE_API_KEY}",
                    "model": "claude-3-sonnet"
                },
                "ollama": {
                    "base_url": "http://localhost:11434",
                    "model": "llama2"
                }
            },
            "storage": {
                "subscriptions_file": "~/.podknow/subscriptions.json",
                "output_directory": "~/Documents/PodKnow",
                "template_directory": "~/.podknow/templates"
            }
        }
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(default_config, f, default_flow_style=False, indent=2)
    
    def _substitute_env_vars(self, config: Any) -> Any:
        """Recursively substitute environment variables in configuration."""
        if isinstance(config, dict):
            return {key: self._substitute_env_vars(value) for key, value in config.items()}
        elif isinstance(config, list):
            return [self._substitute_env_vars(item) for item in config]
        elif isinstance(config, str):
            return self._substitute_env_var_string(config)
        else:
            return config
    
    def _substitute_env_var_string(self, value: str) -> str:
        """Substitute environment variables in a string value."""
        # Pattern matches ${VAR_NAME} or ${VAR_NAME:-default_value}
        pattern = r'\$\{([^}:]+)(?::([^}]*))?\}'
        
        def replace_var(match):
            var_name = match.group(1)
            default_value = match.group(2) if match.group(2) is not None else ""
            
            env_value = os.getenv(var_name)
            if env_value is not None:
                return env_value
            elif default_value:
                return default_value
            else:
                # Return None for missing required environment variables
                return None
        
        result = re.sub(pattern, replace_var, value)
        
        # If the entire string was a single environment variable that's None, return None
        if result is None or (result == value and "${" in value):
            # Check if any required env vars are missing
            missing_vars = re.findall(r'\$\{([^}:]+)\}', value)
            if missing_vars:
                return None
        
        return result
    
    def _format_validation_error(self, error: ValidationError) -> str:
        """Format validation error for user-friendly display."""
        errors = []
        for err in error.errors():
            field_path = " -> ".join(str(loc) for loc in err["loc"])
            message = err["msg"]
            errors.append(f"  {field_path}: {message}")
        
        return "Configuration validation errors:\n" + "\n".join(errors)


class ConfigurationError(Exception):
    """Raised when configuration loading or validation fails."""
    pass