# PodKnow

A command-line podcast management and transcription tool optimized for Apple Silicon.

## Features

- Discover podcasts from Apple Podcasts and Spotify
- Subscribe to and manage podcast feeds locally
- Download and transcribe episodes using MLX-Whisper
- AI-powered content analysis with Claude API and Ollama
- Generate structured markdown files with episode content
- Configurable templates for customized analysis

## Requirements

- Python 3.13+
- macOS with Apple Silicon (M1/M2/M3)
- MLX-Whisper for transcription

## Installation

```bash
pip install -e .
```

## Quick Start

```bash
# Search for podcasts
podknow search "python programming"

# Subscribe to a podcast
podknow subscribe <podcast-id>

# Process new episodes
podknow update

# Analyze episode content
podknow analyze <episode-id>
```

## Configuration

Create a configuration file at `~/.podknow/config.yaml`:

```yaml
podcast_directories:
  apple_podcasts:
    enabled: true
    api_key: ${APPLE_PODCASTS_API_KEY}
  spotify:
    enabled: true
    client_id: ${SPOTIFY_CLIENT_ID}
    client_secret: ${SPOTIFY_CLIENT_SECRET}

ai_analysis:
  primary_provider: claude
  claude:
    api_key: ${CLAUDE_API_KEY}
    model: claude-3-sonnet
```

## Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black podknow/
isort podknow/

# Type checking
mypy podknow/
```

## License

MIT