# PodKnow

A command-line tool that downloads podcast episodes from RSS feeds and transcribes them using OpenAI Whisper.

## What It Does

PodKnow takes a podcast RSS feed URL and:
1. Downloads the audio/video file for an episode
2. Transcribes it using OpenAI Whisper
3. Creates a markdown file with episode metadata and full transcription

Perfect for creating searchable, text-based archives of your favorite podcasts.

## Installation

**Requirements:** Python 3.13 or 3.12 (Python 3.14+ not supported due to dependency limitations)

```bash
# Create virtual environment with Python 3.13
python3.13 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

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
