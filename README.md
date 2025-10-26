# PodKnow

A command-line podcast transcription and analysis tool optimized for Apple Silicon.

## Features

- **Podcast Discovery**: Search across iTunes and Spotify APIs
- **Episode Management**: List and select episodes from RSS feeds  
- **Audio Transcription**: MLX-Whisper powered transcription for Apple Silicon
- **AI Analysis**: Claude AI powered content analysis and summarization
- **Configurable Prompts**: Customizable AI prompts via markdown configuration

## Installation

### Requirements

- Python 3.13+
- Apple Silicon Mac (for MLX-Whisper optimization)
- Claude AI API key

### Install with pip

```bash
# Create virtual environment
python3.13 -m venv podknow-env
source podknow-env/bin/activate

# Install package
pip install -e .
```

### Install with uv (recommended)

```bash
# Create virtual environment
python3.13 -m venv podknow-env
source podknow-env/bin/activate

# Install with uv (faster)
uv pip install -e .
```

## Usage

```bash
# Search for podcasts
podknow search "machine learning"

# List recent episodes
podknow list-episodes "https://example.com/podcast.rss" --count 5

# Transcribe an episode
podknow transcribe episode_123

# Analyze existing transcription
podknow analyze transcription.md
```

## Configuration

Create a configuration file at `~/.podknow/config.md` with your API keys and custom prompts.

## Project Structure

```
podknow/
├── __init__.py
├── models/           # Data models and type definitions
├── services/         # Business logic services
├── cli/             # Command-line interface
├── config/          # Configuration management
└── exceptions.py    # Custom exception hierarchy
```

## Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black .

# Type checking
mypy podknow/
```

## License

MIT License