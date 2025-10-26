"""
Pytest configuration and fixtures for PodKnow tests.
Includes special configuration for installation and platform testing.
"""

import os
import sys
import platform
import tempfile
from pathlib import Path
from unittest.mock import MagicMock
import pytest


def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (may be slow)"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (may take significant time)"
    )
    config.addinivalue_line(
        "markers", "platform: marks tests as platform-specific"
    )
    config.addinivalue_line(
        "markers", "installation: marks tests as installation-related"
    )


@pytest.fixture
def temp_config_dir():
    """Create a temporary configuration directory for testing"""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir) / ".podknow"
        config_dir.mkdir(parents=True, exist_ok=True)
        yield config_dir


@pytest.fixture
def mock_platform_info():
    """Mock platform information for testing"""
    return {
        'system': platform.system(),
        'machine': platform.machine(),
        'python_version': platform.python_version(),
        'is_apple_silicon': (
            platform.system() == "Darwin" and 
            platform.machine().lower() in ["arm64", "aarch64"]
        )
    }


@pytest.fixture
def mock_subprocess():
    """Mock subprocess for testing installation scripts"""
    mock = MagicMock()
    mock.run.return_value.returncode = 0
    mock.run.return_value.stdout = "success"
    mock.run.return_value.stderr = ""
    return mock


@pytest.fixture
def sample_config_content():
    """Sample configuration content for testing"""
    return """# PodKnow Configuration

## API Keys

```yaml
claude_api_key: "test-api-key"
```

## Analysis Prompts

### Summary Prompt
```
Analyze this podcast transcription and provide a concise summary.
```

### Topic Extraction Prompt
```
Extract the main topics discussed in this podcast episode.
```
"""


@pytest.fixture
def installation_test_env():
    """Set up environment for installation testing"""
    original_env = os.environ.copy()
    
    # Set test environment variables
    test_env = {
        'PODKNOW_TEST_MODE': '1',
        'PODKNOW_CONFIG_DIR': str(Path.home() / '.podknow_test'),
    }
    
    os.environ.update(test_env)
    
    yield test_env
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture(scope="session")
def project_root():
    """Get the project root directory"""
    return Path(__file__).parent.parent


@pytest.fixture
def mock_dependencies():
    """Mock external dependencies for testing"""
    mocks = {}
    
    # Mock MLX-Whisper for non-Apple Silicon testing
    if not (platform.system() == "Darwin" and platform.machine().lower() in ["arm64", "aarch64"]):
        mock_mlx = MagicMock()
        mock_mlx.__version__ = "0.1.0"
        sys.modules['mlx_whisper'] = mock_mlx
        mocks['mlx_whisper'] = mock_mlx
    
    # Mock OpenAI Whisper for Apple Silicon testing
    if platform.system() == "Darwin" and platform.machine().lower() in ["arm64", "aarch64"]:
        mock_whisper = MagicMock()
        mock_whisper.__version__ = "20231117"
        sys.modules['whisper'] = mock_whisper
        mocks['whisper'] = mock_whisper
    
    yield mocks
    
    # Clean up mocks
    for module_name in mocks:
        if module_name in sys.modules:
            del sys.modules[module_name]


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add platform-specific markers"""
    for item in items:
        # Mark Apple Silicon specific tests
        if "apple_silicon" in item.name.lower():
            item.add_marker(pytest.mark.skipif(
                not (platform.system() == "Darwin" and platform.machine().lower() in ["arm64", "aarch64"]),
                reason="Apple Silicon specific test"
            ))
        
        # Mark Windows specific tests
        if "windows" in item.name.lower():
            item.add_marker(pytest.mark.skipif(
                platform.system() != "Windows",
                reason="Windows specific test"
            ))
        
        # Mark macOS specific tests
        if "macos" in item.name.lower():
            item.add_marker(pytest.mark.skipif(
                platform.system() != "Darwin",
                reason="macOS specific test"
            ))
        
        # Mark Linux specific tests
        if "linux" in item.name.lower():
            item.add_marker(pytest.mark.skipif(
                platform.system() != "Linux",
                reason="Linux specific test"
            ))


@pytest.fixture
def clean_import_cache():
    """Clean import cache before and after tests"""
    # Store original modules
    original_modules = sys.modules.copy()
    
    yield
    
    # Restore original modules and clean up test imports
    modules_to_remove = []
    for module_name in sys.modules:
        if module_name not in original_modules:
            modules_to_remove.append(module_name)
    
    for module_name in modules_to_remove:
        del sys.modules[module_name]