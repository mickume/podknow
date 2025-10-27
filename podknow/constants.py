"""
Constants used throughout the PodKnow application.
"""

# Claude AI Model Configuration
DEFAULT_CLAUDE_MODEL = "claude-sonnet-4-20250514"

# Alternative Claude Models (for reference in documentation)
CLAUDE_MODELS = {
    "sonnet": "claude-sonnet-4-20250514",  # Recommended balance of speed and quality
    "haiku": "claude-haiku-4-5-20251001",      # Fastest, less detailed
    "opus": "claude-opus-4-1-20250805",        # Most capable, slower, most expensive
}

# API Configuration
DEFAULT_MAX_TOKENS = 4000
DEFAULT_TEMPERATURE = 0.1
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 1.0

# File and Directory Defaults
DEFAULT_OUTPUT_DIRECTORY = "~/Documents/PodKnow"
DEFAULT_FILENAME_TEMPLATE = "{podcast_title}_{episode_number}_{date}.md"

# Transcription Settings
DEFAULT_WHISPER_MODEL = "base"
DEFAULT_LANGUAGE = "en"
DEFAULT_CHUNK_SIZE = 8192
DEFAULT_DOWNLOAD_TIMEOUT = 300

# Analysis Settings
DEFAULT_MIN_TRANSCRIPTION_LENGTH = 100
DEFAULT_MAX_ANALYSIS_LENGTH = 50000

# Logging Settings
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_MAX_LOG_SIZE_MB = 10
DEFAULT_LOG_BACKUP_COUNT = 5

# Discovery Settings
DEFAULT_SEARCH_LIMIT = 20
DEFAULT_SEARCH_TIMEOUT = 10
DEFAULT_SIMILARITY_THRESHOLD = 0.8

# Platform Priorities
DEFAULT_PLATFORM_PRIORITIES = {
    "itunes": 10,
    "spotify": 5
}