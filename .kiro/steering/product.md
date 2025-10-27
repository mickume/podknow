# Product Overview

PodKnow is a command-line podcast transcription and analysis tool optimized for Apple Silicon Macs. It enables users to discover podcasts, download episodes, and generate AI-powered transcriptions with content analysis.

## Core Features

- **Podcast Discovery**: Search across iTunes and Spotify APIs by title, author, or keywords
- **Episode Management**: List and select episodes from RSS feeds with unique identifiers
- **Audio Transcription**: MLX-Whisper powered transcription optimized for Apple Silicon (M-series chips)
- **AI Analysis**: Claude AI integration for content summarization, topic extraction, and sponsor detection
- **Configurable Prompts**: Markdown-based configuration system for customizable AI prompts

## Target Platform

- Primary: Apple Silicon Macs (M1, M2, M3+ series)
- Secondary: Standard platforms with OpenAI Whisper fallback
- Python 3.13+ required

## Workflow

1. Search and discover podcasts via iTunes/Spotify APIs
2. List recent episodes from RSS feeds
3. Download and transcribe episodes using MLX-Whisper
4. Analyze transcriptions with Claude AI for summaries, topics, keywords, and sponsor detection
5. Output structured markdown files with metadata and analysis

## Configuration

Uses markdown-based configuration files in `~/.podknow/config.md` for API keys and customizable AI prompts, allowing non-technical users to modify behavior without code changes.