# PodKnow

A command-line podcast transcription and analysis tool optimized for Apple Silicon.

## Features

- **Podcast Discovery**: Search across iTunes and Spotify APIs by title, author, or keywords
- **Episode Management**: List and select episodes from RSS feeds with unique identifiers
- **Audio Transcription**: MLX-Whisper powered transcription for Apple Silicon (with OpenAI Whisper fallback)
- **AI Analysis**: Claude AI powered content analysis including summaries, topics, keywords, and sponsor detection
- **Configurable Prompts**: Customizable AI prompts via markdown configuration
- **Smart Workflow Orchestration**: Enhanced error handling, recovery mechanisms, and detailed logging
- **Rich CLI Experience**: Progress bars, verbose mode, and colored output
- **Language Detection**: Automatic language detection with configurable skip options

## Installation

### Requirements

- Python 3.13+
- Apple Silicon Mac (for MLX-Whisper optimization) or any platform (OpenAI Whisper fallback)
- Claude AI API key (get one from [Anthropic Console](https://console.anthropic.com/))

### Install with pip

```bash
# Create virtual environment
python3.13 -m venv podknow-env
source podknow-env/bin/activate

# Install package
pip install -e .

# Or use the Makefile
make install
```

### Install with uv (recommended for faster installation)

```bash
# Create virtual environment
python3.13 -m venv podknow-env
source podknow-env/bin/activate

# Install with uv (faster)
uv pip install -e .

# Or use the Makefile
make install-uv
```

### First-time Setup

After installation, run the setup command to create a default configuration:

```bash
# Create configuration file
podknow setup

# Edit the configuration file to add your Claude API key
nano ~/.podknow/config.md

# Verify your configuration
podknow config-status
```

## Usage

### Search for Podcasts

```bash
# Search all platforms
podknow search "machine learning"

# Search specific platform
podknow search "Tim Ferris" --platform itunes
podknow search "startup stories" --platform spotify

# Limit results
podknow search "AI podcasts" --limit 10
```

### List Episodes

```bash
# List recent episodes from RSS feed
podknow list https://feeds.example.com/podcast.rss

# List specific number of episodes
podknow list https://feeds.example.com/podcast.rss --count 5

# Show episode descriptions
podknow list https://feeds.example.com/podcast.rss --show-descriptions
```

### Transcribe Episodes

```bash
# Transcribe an episode (requires --rss-url flag)
podknow transcribe episode_abc123 --rss-url https://feeds.example.com/podcast.rss

# Transcribe without AI analysis (faster)
podknow transcribe episode_abc123 --rss-url https://feeds.example.com/podcast.rss --skip-analysis

# Custom output directory
podknow transcribe episode_abc123 --rss-url https://feeds.example.com/podcast.rss --output-dir ./transcripts

# Skip language detection (assume English)
podknow transcribe episode_abc123 --rss-url https://feeds.example.com/podcast.rss --skip-language-detection

# Verbose mode for detailed logging
podknow transcribe episode_abc123 --rss-url https://feeds.example.com/podcast.rss --verbose
```

### Analyze Existing Transcriptions

```bash
# Analyze existing transcription file
podknow analyze transcription.md

# Specify output file
podknow analyze transcription.md --output-file analyzed_transcript.md

# Use custom API key
podknow analyze transcription.md --claude-api-key your-api-key
```

### Configuration Management

```bash
# Create or reset configuration
podknow setup

# Force overwrite existing configuration
podknow setup --force

# Check configuration status
podknow config-status
```

### Global Options

All commands support these global options:

```bash
# Enable verbose output
podknow --verbose search "AI"

# Log to file
podknow --log-file debug.log transcribe episode_123 --rss-url https://example.com/feed.rss

# Show version
podknow --version
```

## Configuration

The configuration file is stored at `~/.podknow/config.md` and uses markdown format with embedded YAML blocks.

### Configuration Structure

```markdown
# PodKnow Configuration

## API Keys

```yaml
claude_api_key: "your-claude-api-key-here"
spotify_client_id: "optional-spotify-client-id"
spotify_client_secret: "optional-spotify-client-secret"
```

## Analysis Prompts

### Summary Prompt
Analyze this podcast transcription and provide a concise summary...

### Topic Extraction Prompt
Extract the main topics discussed in this podcast episode...

### Keyword Identification Prompt
Identify relevant keywords and tags for this podcast content...

### Sponsor Detection Prompt
Identify any sponsored content or advertisements...
```

You can customize the AI prompts by editing the configuration file. The prompts are loaded automatically when running analysis.

## Project Structure

```
podknow/
├── __init__.py              # Package initialization
├── __main__.py              # Module entry point
├── cli/                     # Command-line interface
│   ├── __init__.py
│   └── main.py             # Click-based CLI commands
├── models/                  # Data models and type definitions
│   ├── __init__.py
│   ├── analysis.py         # AnalysisResult, SponsorSegment
│   ├── episode.py          # Episode, EpisodeMetadata
│   ├── output.py           # OutputDocument
│   ├── podcast.py          # PodcastResult, PodcastMetadata
│   └── transcription.py    # TranscriptionResult, TranscriptionSegment
├── services/                # Business logic services
│   ├── __init__.py
│   ├── analysis.py         # Claude AI integration
│   ├── config.py           # Configuration service
│   ├── discovery.py        # iTunes/Spotify search
│   ├── episode.py          # Episode management
│   ├── rss.py              # RSS feed parsing
│   ├── transcription.py    # MLX-Whisper/OpenAI Whisper
│   └── workflow.py         # Workflow orchestration
├── config/                  # Configuration management
│   ├── __init__.py
│   ├── manager.py          # ConfigManager class
│   └── models.py           # Configuration data models
├── utils/                   # Utility modules
│   ├── __init__.py
│   ├── cli_errors.py       # CLI error handling
│   └── progress.py         # Progress bar utilities
├── constants.py             # Application constants
└── exceptions.py            # Custom exception hierarchy
```

## Development

### Install Development Dependencies

```bash
# Install with development extras
pip install -e ".[dev]"

# Or use the Makefile
make install-dev
```

### Development Workflow

```bash
# Run all tests with coverage
make test

# Run linting checks
make lint

# Format code (black + ruff)
make format

# Type checking with mypy
mypy podknow/

# Clean build artifacts
make clean

# Check platform and dependencies
make check-platform
make verify-deps
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=podknow --cov-report=term-missing

# Run specific test markers
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m "not slow"    # Skip slow tests
```

### Code Quality Tools

- **Black**: Code formatting (line length: 88)
- **Ruff**: Fast Python linter with modern rules
- **Mypy**: Static type checking with strict configuration
- **Pytest**: Testing framework with coverage reporting

## Platform Support

### Apple Silicon (M1, M2, M3+)

PodKnow automatically detects Apple Silicon and uses MLX-Whisper for optimized transcription performance.

Dependencies installed:
- `mlx>=0.0.6`
- `mlx-whisper>=0.1.0`

### Other Platforms

On non-Apple Silicon platforms, PodKnow falls back to OpenAI Whisper with torch backend.

Dependencies installed:
- `openai-whisper>=20231117`
- `torch>=2.0.0`

Check your platform configuration:
```bash
make check-platform
```

## Dependencies

### Core Dependencies
- **click** (>=8.0.0): CLI framework
- **requests** (>=2.28.0): HTTP client
- **feedparser** (>=6.0.0): RSS parsing
- **pydantic** (>=2.0.0): Data validation
- **anthropic** (>=0.8.0): Claude AI client
- **python-dateutil** (>=2.8.0): Date parsing
- **pyyaml** (>=6.0.0): YAML configuration
- **rich** (>=13.0.0): CLI formatting and progress bars
- **tqdm** (>=4.64.0): Additional progress indicators

### Audio Processing
- **mlx-whisper** (>=0.1.0): Apple Silicon transcription
- **openai-whisper** (>=20231117): Standard platform transcription
- **librosa** (>=0.10.0): Audio processing utilities
- **soundfile** (>=0.12.0): Audio file I/O

## License

MIT License