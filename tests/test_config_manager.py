"""
Tests for configuration manager and config service.
"""

import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch, mock_open

from podknow.config.manager import ConfigManager
from podknow.config.models import Config
from podknow.services.config import ConfigService
from podknow.exceptions import ConfigurationError


class TestConfigManager:
    """Test cases for ConfigManager."""
    
    def test_init_with_default_path(self):
        """Test ConfigManager initialization with default path."""
        manager = ConfigManager()
        expected_path = Path.home() / ".podknow" / "config.md"
        assert manager.config_path == expected_path
    
    def test_init_with_custom_path(self):
        """Test ConfigManager initialization with custom path."""
        custom_path = Path("/tmp/custom_config.md")
        manager = ConfigManager(custom_path)
        assert manager.config_path == custom_path
    
    def test_load_config_file_not_found(self):
        """Test loading config when file doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "nonexistent.md"
            manager = ConfigManager(config_path)
            
            with pytest.raises(ConfigurationError, match="Configuration file not found"):
                manager.load_config()
    
    def test_load_valid_config(self):
        """Test loading a valid configuration file."""
        config_content = '''# PodKnow Configuration

## API Keys

```yaml
claude_api_key: "test-api-key"
```

## Analysis Prompts

### Summary Prompt
```
Test summary prompt
```

### Topic Extraction Prompt
```
Test topic prompt
```

### Keyword Identification Prompt
```
Test keyword prompt
```

### Sponsor Detection Prompt
```
Test sponsor prompt
```

## Output Settings

```yaml
output_settings:
  output_directory: "~/test"
  include_timestamps: true

analysis_settings:
  max_summary_length: 300
```
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(config_content)
            config_path = Path(f.name)
        
        try:
            manager = ConfigManager(config_path)
            config = manager.load_config()
            
            assert config.claude_api_key == "test-api-key"
            assert "summary" in config.prompts
            assert config.prompts["summary"] == "Test summary prompt"
            assert config.output_settings["output_directory"] == "~/test"
            assert config.analysis_settings["max_summary_length"] == 300
        finally:
            config_path.unlink()
    
    def test_load_config_invalid_yaml(self):
        """Test loading config with invalid YAML."""
        config_content = '''# PodKnow Configuration

```yaml
invalid: yaml: content: [
```
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(config_content)
            config_path = Path(f.name)
        
        try:
            manager = ConfigManager(config_path)
            with pytest.raises(ConfigurationError, match="Invalid YAML"):
                manager.load_config()
        finally:
            config_path.unlink()
    
    def test_validate_config_success(self):
        """Test successful config validation."""
        config = Config(
            claude_api_key="valid-key",
            prompts={
                "summary": "Test summary",
                "topics": "Test topics",
                "keywords": "Test keywords",
                "sponsor_detection": "Test sponsor"
            },
            analysis_settings={},
            output_settings={}
        )
        
        manager = ConfigManager()
        assert manager.validate_config(config) is True
    
    def test_validate_config_empty_api_key(self):
        """Test config validation with empty API key."""
        config = Config(
            claude_api_key="   ",  # Empty/whitespace key
            prompts={"summary": "Test"},
            analysis_settings={},
            output_settings={}
        )
        
        manager = ConfigManager()
        with pytest.raises(ConfigurationError, match="Claude API key cannot be empty"):
            manager.validate_config(config)
    
    def test_validate_config_missing_prompt(self):
        """Test config validation with missing required prompt."""
        config = Config(
            claude_api_key="valid-key",
            prompts={"summary": "Test"},  # Missing other required prompts
            analysis_settings={},
            output_settings={}
        )
        
        manager = ConfigManager()
        with pytest.raises(ConfigurationError, match="Missing required prompt template"):
            manager.validate_config(config)
    
    def test_validate_config_empty_prompt(self):
        """Test config validation with empty prompt."""
        config = Config(
            claude_api_key="valid-key",
            prompts={
                "summary": "",  # Empty prompt
                "topics": "Test topics",
                "keywords": "Test keywords",
                "sponsor_detection": "Test sponsor"
            },
            analysis_settings={},
            output_settings={}
        )
        
        manager = ConfigManager()
        with pytest.raises(ConfigurationError, match="Prompt template 'summary' cannot be empty"):
            manager.validate_config(config)
    
    def test_get_prompt_template_success(self):
        """Test getting existing prompt template."""
        config = Config(
            claude_api_key="valid-key",
            prompts={"test_prompt": "This is a test prompt"},
            analysis_settings={},
            output_settings={}
        )
        
        manager = ConfigManager()
        prompt = manager.get_prompt_template(config, "test_prompt")
        assert prompt == "This is a test prompt"
    
    def test_get_prompt_template_not_found(self):
        """Test getting non-existent prompt template."""
        config = Config(
            claude_api_key="valid-key",
            prompts={"existing": "test prompt"},  # Need at least one prompt
            analysis_settings={},
            output_settings={}
        )
        
        manager = ConfigManager()
        with pytest.raises(ConfigurationError, match="Prompt template 'nonexistent' not found"):
            manager.get_prompt_template(config, "nonexistent")
    
    def test_create_default_config(self):
        """Test creating default configuration file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.md"
            manager = ConfigManager(config_path)
            
            manager.create_default_config()
            
            assert config_path.exists()
            content = config_path.read_text()
            assert "claude_api_key" in content
            assert "Summary Prompt" in content
            assert "Topic Extraction Prompt" in content
    
    def test_config_exists(self):
        """Test checking if config file exists."""
        with tempfile.NamedTemporaryFile(suffix='.md') as f:
            config_path = Path(f.name)
            manager = ConfigManager(config_path)
            assert manager.config_exists() is True
        
        # File should be deleted now
        assert manager.config_exists() is False


class TestConfigService:
    """Test cases for ConfigService."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "test_config.md"
        
        # Create a valid test config
        config_content = '''# Test Configuration

```yaml
claude_api_key: "test-key"
```

### Summary Prompt
```
Test summary: {content}
```

### Topic Extraction Prompt
```
Extract topics from: {content}
```

### Keyword Identification Prompt
```
Find keywords in: {content}
```

### Sponsor Detection Prompt
```
Detect sponsors in: {content}
```

```yaml
analysis_settings:
  max_summary_length: 500

output_settings:
  output_directory: "~/test_output"
  filename_template: "{title}_{date}.md"
```
'''
        self.config_path.write_text(config_content)
    
    def test_get_config_loads_once(self):
        """Test that config is loaded only once unless forced."""
        service = ConfigService(self.config_path)
        
        config1 = service.get_config()
        config2 = service.get_config()
        
        # Should be the same instance (cached)
        assert config1 is config2
    
    def test_get_config_force_reload(self):
        """Test forcing config reload."""
        service = ConfigService(self.config_path)
        
        config1 = service.get_config()
        config2 = service.get_config(force_reload=True)
        
        # Should be different instances
        assert config1 is not config2
        assert config1.claude_api_key == config2.claude_api_key
    
    def test_get_prompt_without_substitution(self):
        """Test getting prompt without variable substitution."""
        service = ConfigService(self.config_path)
        
        prompt = service.get_prompt("summary")
        assert prompt == "Test summary: {content}"
    
    def test_get_prompt_with_substitution(self):
        """Test getting prompt with variable substitution."""
        service = ConfigService(self.config_path)
        
        prompt = service.get_prompt("summary", content="test content")
        assert prompt == "Test summary: test content"
    
    def test_get_prompt_missing_variable(self):
        """Test getting prompt with missing substitution variable."""
        service = ConfigService(self.config_path)
        
        with pytest.raises(ConfigurationError, match="Missing variable for template substitution"):
            service.get_prompt("summary", wrong_var="test")
    
    def test_get_prompt_nonexistent(self):
        """Test getting non-existent prompt."""
        service = ConfigService(self.config_path)
        
        with pytest.raises(ConfigurationError, match="Prompt template 'nonexistent' not found"):
            service.get_prompt("nonexistent")
    
    def test_get_analysis_setting(self):
        """Test getting analysis setting."""
        service = ConfigService(self.config_path)
        
        setting = service.get_analysis_setting("max_summary_length")
        assert setting == 500
        
        # Test default value
        default_setting = service.get_analysis_setting("nonexistent", "default")
        assert default_setting == "default"
    
    def test_get_output_setting(self):
        """Test getting output setting."""
        service = ConfigService(self.config_path)
        
        setting = service.get_output_setting("output_directory")
        assert setting == "~/test_output"
    
    def test_get_claude_api_key(self):
        """Test getting Claude API key."""
        service = ConfigService(self.config_path)
        
        api_key = service.get_claude_api_key()
        assert api_key == "test-key"
    
    def test_validate_prompt_template_success(self):
        """Test successful prompt template validation."""
        service = ConfigService(self.config_path)
        
        template = "Hello {name}, your {item} is ready"
        result = service.validate_prompt_template(template, ["name", "item"])
        assert result is True
    
    def test_validate_prompt_template_missing_vars(self):
        """Test prompt template validation with missing variables."""
        service = ConfigService(self.config_path)
        
        template = "Hello {name}"
        with pytest.raises(ConfigurationError, match="missing required variables"):
            service.validate_prompt_template(template, ["name", "missing_var"])
    
    def test_get_output_directory(self):
        """Test getting output directory with path expansion."""
        service = ConfigService(self.config_path)
        
        output_dir = service.get_output_directory()
        assert isinstance(output_dir, Path)
        # Should expand the ~ to actual home directory
        assert str(output_dir).startswith(str(Path.home()))
    
    def test_format_filename(self):
        """Test filename formatting."""
        service = ConfigService(self.config_path)
        
        filename = service.format_filename(title="Test Podcast", date="2024-01-01")
        assert filename == "Test Podcast_2024-01-01.md"
    
    def test_format_filename_clean_invalid_chars(self):
        """Test filename formatting with invalid characters."""
        service = ConfigService(self.config_path)
        
        filename = service.format_filename(title="Test/Podcast:Episode", date="2024-01-01")
        assert filename == "Test_Podcast_Episode_2024-01-01.md"
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)