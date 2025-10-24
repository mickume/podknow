# PodKnow

A command-line tool that downloads podcast episodes from RSS feeds and transcribes them using Whisper, optimized for Apple Silicon.

## What It Does

PodKnow takes a podcast RSS feed URL and:
1. Downloads the audio/video file for an episode
2. Transcribes it using **MLX-Whisper** (optimized for Apple M-series chips)
3. Creates a markdown file with episode metadata and full transcription

Perfect for creating searchable, text-based archives of your favorite podcasts.

## ⚡ Apple Silicon Optimization

PodKnow is optimized for Apple M-series processors (M1/M2/M3/M4) and automatically uses:
- **Metal Performance Shaders (MPS)** - GPU acceleration
- **Apple Neural Engine** - Ultra-fast AI inference
- **AMX coprocessor** - Optimized matrix operations

**Performance on M4 Max:**
- Transcription: **52x faster than real-time**
- Power consumption: **25W** (vs 190W on GPU workstations)
- Example: 1-hour podcast transcribed in ~70 seconds

## Installation

**Requirements:**
- Python 3.13 or 3.12 (Python 3.14+ not supported)
- **Apple Silicon Mac (M1/M2/M3/M4)** for optimal performance

```bash
# Create virtual environment with Python 3.13
python3.13 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies (includes MLX-Whisper for Apple Silicon)
pip install -r requirements.txt
```

**Note:** MLX-Whisper only works on Apple Silicon. The code will automatically fall back to standard OpenAI Whisper on other platforms (Intel Macs, Linux, Windows).

## Usage

### List Available Episodes

```bash
python podknow.py <rss_feed_url> --list
```

Example:
```bash
python podknow.py https://feeds.megaphone.fm/vergecast --list --limit 5
```

This shows the most recent episodes with their position numbers.

### Download and Transcribe an Episode

```bash
python podknow.py <rss_feed_url> -e <episode_number>
```

Examples:
```bash
# Process the latest episode
python podknow.py https://feeds.megaphone.fm/vergecast

# Process a specific episode by position (from --list output)
python podknow.py https://feeds.megaphone.fm/vergecast -e 2

# Specify output directory
python podknow.py https://feeds.megaphone.fm/vergecast -e 2 -o ./my-transcripts
```

## Command-Line Options

- `rss_url` - Podcast RSS feed URL (required)
- `-l, --list` - List recent episodes without processing
- `-n, --limit` - Number of episodes to list (default: 10)
- `-e, --episode` - Episode number/position to process
- `-o, --output` - Output directory for markdown files (default: ./output)
- `-p, --paragraph-threshold` - Minimum pause in seconds to create paragraph breaks (default: 2.0)

## Output

Creates a markdown file containing:
- Episode title and metadata
- Publication date and duration
- Episode description
- Links mentioned in the episode
- Full transcription with detected language
- **Readable paragraph breaks** - Automatically segments text based on speech pauses
- **Timestamps** - Each paragraph includes a timestamp for easy navigation

Files are saved to `./output/` by default.

## Customizing Paragraph Breaks

By default, pauses of 2 seconds or longer create new paragraphs. You can adjust this:

```bash
# More paragraphs (break on shorter pauses)
python podknow.py <url> -e 1 --paragraph-threshold 1.0

# Fewer paragraphs (only break on longer pauses)
python podknow.py <url> -e 1 --paragraph-threshold 3.0
```

## Optional: Ollama for LLM Processing

If you want to use local LLMs for post-processing (future feature), install Ollama:

```bash
# Install Ollama (native Apple Silicon version)
brew install ollama

# Start Ollama service
ollama serve

# Pull a small, fast model
ollama pull llama3.2:3b
```

**Note:** Ollama automatically uses Metal GPU acceleration on Apple Silicon - no configuration needed!

## Performance Tips for Apple Silicon

1. **First run downloads models** - The first transcription will download the Whisper model (~500MB). Subsequent runs are much faster.

2. **Memory usage** - Your M4 can use ~75% of system RAM for AI tasks. For example:
   - 32GB Mac: Can handle 34B parameter models
   - 64GB Mac: Can handle 70B+ parameter models

3. **Docker not recommended** - Run PodKnow natively on macOS. Docker containers don't support Metal GPU acceleration on Mac.

4. **Monitor with Activity Monitor** - Check "GPU History" to see Metal acceleration in action during transcription.
