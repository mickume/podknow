"""
Configuration service for dynamic prompt loading and template substitution.
"""

import re
from typing import Dict, Any, Optional
from pathlib import Path

from ..config.manager import ConfigManager
from ..config.models import Config
from ..exceptions import ConfigurationError


class ConfigService:
    """Service for managing configuration and dynamic prompt loading."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize config service with optional custom config path."""
        self.config_manager = ConfigManager(config_path)
        self._config: Optional[Config] = None
        self._config_loaded = False
    
    def get_config(self, force_reload: bool = False) -> Config:
        """Get configuration, loading it if necessary."""
        if not self._config_loaded or force_reload:
            self._config = self.config_manager.load_config()
            self.config_manager.validate_config(self._config)
            self._config_loaded = True
        return self._config
    
    def get_prompt(self, prompt_type: str, **kwargs) -> str:
        """Get a prompt template with optional variable substitution."""
        config = self.get_config()
        
        if prompt_type not in config.prompts:
            raise ConfigurationError(f"Prompt template '{prompt_type}' not found")
        
        template = config.prompts[prompt_type]
        
        # Perform variable substitution if kwargs provided
        if kwargs:
            template = self._substitute_variables(template, kwargs)
        
        return template
    
    def reload_config(self) -> Config:
        """Force reload configuration from file."""
        return self.get_config(force_reload=True)
    
    def get_analysis_setting(self, setting_name: str, default: Any = None) -> Any:
        """Get an analysis setting from configuration."""
        config = self.get_config()
        return config.analysis_settings.get(setting_name, default)
    
    def get_output_setting(self, setting_name: str, default: Any = None) -> Any:
        """Get an output setting from configuration."""
        config = self.get_config()
        return config.output_settings.get(setting_name, default)
    
    def get_claude_api_key(self) -> str:
        """Get Claude API key from configuration."""
        config = self.get_config()
        return config.claude_api_key
    
    def validate_prompt_template(self, template: str, required_vars: Optional[list] = None) -> bool:
        """Validate a prompt template for required variables."""
        if required_vars:
            # Find all variables in template (format: {variable_name})
            template_vars = set(re.findall(r'\{(\w+)\}', template))
            required_vars_set = set(required_vars)
            
            missing_vars = required_vars_set - template_vars
            if missing_vars:
                raise ConfigurationError(
                    f"Prompt template missing required variables: {', '.join(missing_vars)}"
                )
        
        return True
    
    def _substitute_variables(self, template: str, variables: Dict[str, Any]) -> str:
        """Substitute variables in template string."""
        try:
            # Use format() for variable substitution
            return template.format(**variables)
        except KeyError as e:
            raise ConfigurationError(f"Missing variable for template substitution: {e}")
        except ValueError as e:
            raise ConfigurationError(f"Invalid template format: {e}")
    
    def ensure_config_exists(self) -> bool:
        """Ensure configuration file exists, create default if not."""
        if not self.config_manager.config_exists():
            try:
                self.config_manager.create_default_config()
                return True
            except Exception as e:
                raise ConfigurationError(f"Failed to create default configuration: {str(e)}")
        return True
    
    def get_output_directory(self) -> Path:
        """Get configured output directory, expanding user path."""
        output_dir = self.get_output_setting('output_directory', '~/Documents/PodKnow')
        return Path(output_dir).expanduser()
    
    def get_filename_template(self) -> str:
        """Get configured filename template."""
        return self.get_output_setting(
            'filename_template', 
            '{podcast_title}_{episode_number}_{date}.md'
        )
    
    def format_filename(self, **kwargs) -> str:
        """Format filename using template and provided variables."""
        template = self.get_filename_template()
        
        # Clean variables for filename use
        cleaned_kwargs = {}
        for key, value in kwargs.items():
            if isinstance(value, str):
                # Remove invalid filename characters
                cleaned_value = re.sub(r'[<>:"/\\|?*]', '_', value)
                cleaned_kwargs[key] = cleaned_value
            else:
                cleaned_kwargs[key] = value
        
        try:
            return template.format(**cleaned_kwargs)
        except KeyError as e:
            raise ConfigurationError(f"Missing variable for filename template: {e}")