# Technology Stack

## Build System & Package Management

- **Build System**: setuptools with pyproject.toml configuration
- **Package Manager**: pip or uv (recommended for faster installs)
- **Python Version**: 3.13+ required
- **Virtual Environment**: Required for isolation

## Core Dependencies

### CLI Framework
- **Click**: Command-line interface framework with decorators and context management

### Audio Processing
- **MLX-Whisper**: Apple Silicon optimized transcription (primary)
- **OpenAI Whisper**: Fallback for non-Apple Silicon platforms
- **librosa**: Audio analysis and processing
- **soundfile**: Audio file I/O operations

### AI Integration
- **anthropic**: Claude AI API client for content analysis

### Data & Networking
- **pydantic**: Data validation and serialization with type hints
- **requests**: HTTP client for API calls
- **feedparser**: RSS feed parsing
- **python-dateutil**: Date/time parsing utilities

### Output & UI
- **rich**: Enhanced CLI output formatting and progress bars
- **tqdm**: Progress bars for long-running operations
- **pyyaml**: YAML parsing for configuration

## Development Tools

### Code Quality
- **black**: Code formatting (line-length: 88)
- **ruff**: Fast Python linter and formatter
- **mypy**: Static type checking with strict configuration

### Testing
- **pytest**: Test framework with coverage reporting
- **pytest-mock**: Mocking utilities
- **pytest-cov**: Coverage reporting (HTML, XML, terminal)

## Common Commands

### Installation
```bash
# Standard installation
pip install -e .

# Development installation
pip install -e ".[dev]"

# Fast installation with uv
uv pip install -e .
```

### Development Workflow
```bash
# Run tests with coverage
make test
# or: pytest tests/ -v --cov=podknow --cov-report=term-missing

# Format code
make format
# or: black podknow/ tests/ && ruff check --fix podknow/ tests/

# Lint code
make lint
# or: ruff check podknow/ tests/ && mypy podknow/

# Clean build artifacts
make clean

# Check platform compatibility
make check-platform

# Verify dependencies
make verify-deps
```

### Platform-Specific Notes

- **Apple Silicon**: Uses MLX-Whisper for optimized performance
- **Other Platforms**: Falls back to OpenAI Whisper with torch
- **Configuration**: Platform detection handled automatically in setup.py