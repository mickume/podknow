# PodKnow Configuration Guide

This guide explains how to configure PodKnow for your specific needs, including API setup, prompt customization, and advanced settings.

## Quick Start

1. **Initial Setup**
   ```bash
   podknow setup
   ```
   This creates a default configuration file at `~/.podknow/config.md`

2. **Add Your API Key**
   ```bash
   nano ~/.podknow/config.md
   ```
   Replace `your-claude-api-key-here` with your actual Claude API key

3. **Verify Configuration**
   ```bash
   podknow config-status
   ```

## Configuration File Structure

The configuration file uses Markdown format with embedded YAML blocks for settings and plain text blocks for prompts.

### Location
- Default: `~/.podknow/config.md`
- Custom: Use `PODKNOW_CONFIG_PATH` environment variable

### Basic Structure
```markdown
# PodKnow Configuration

## API Keys
```yaml
claude_api_key: "your-key-here"
```

## Analysis Prompts
### Summary Prompt
```
Your custom prompt here...
```

## Settings
```yaml
output_directory: "~/Documents/PodKnow"
```
```

## API Configuration

### Claude AI (Required)
1. **Get API Key**
   - Visit https://console.anthropic.com/
   - Create an account and generate an API key
   - Add to configuration file or set `CLAUDE_API_KEY` environment variable

2. **Model Selection**
   ```yaml
   claude_model: "claude-sonnet-4-20250514"  # Recommended (latest)
   # claude_model: "claude-haiku-4-5-20251001"    # Faster, less detailed
   # claude_model: "claude-opus-4-1-20250805"     # Most capable, slower, most expensive
   ```

### Spotify (Optional)
1. **Create Spotify App**
   - Visit https://developer.spotify.com/dashboard
   - Create a new app
   - Note the Client ID and Client Secret

2. **Add Credentials**
   ```yaml
   spotify_client_id: "your-client-id"
   spotify_client_secret: "your-client-secret"
   ```

## Prompt Customization

### Understanding Prompts
PodKnow uses four main prompts for analysis:
- **Summary**: Generates episode overview
- **Topics**: Extracts main discussion points
- **Keywords**: Identifies relevant tags
- **Sponsors**: Detects promotional content

### Customization Examples

#### Academic Research Focus
```markdown
### Summary Prompt
```
Analyze this academic podcast transcription focusing on research methodology, 
key findings, and scholarly contributions. Provide a structured summary that 
highlights the research questions, methods used, main results, and implications 
for the field. Use formal academic language appropriate for literature reviews.
```

#### Business Analysis Focus
```markdown
### Summary Prompt
```
Summarize this business podcast focusing on strategic insights, market trends, 
and actionable recommendations. Highlight key business metrics, competitive 
advantages, and growth strategies discussed. Frame the summary for business 
professionals seeking practical insights.
```

#### Content Creation Focus
```markdown
### Summary Prompt
```
Create an engaging summary of this podcast episode that captures the main 
narrative, interesting anecdotes, and key takeaways. Write in a conversational 
tone that would appeal to the podcast's target audience and encourage further 
listening.
```

### Advanced Prompt Techniques

#### Using Context Variables
Prompts can reference episode metadata:
```markdown
### Summary Prompt
```
Analyze this {duration} episode of "{podcast_title}" focusing on...
```

#### Multi-step Instructions
```markdown
### Topics Prompt
```
Follow these steps to extract topics:
1. Identify major discussion segments (5+ minutes each)
2. Summarize each segment's main theme in one sentence
3. Prioritize topics by discussion time and depth
4. Return 3-8 topics maximum, one per line
```

#### Output Format Specification
```markdown
### Keywords Prompt
```
Extract keywords in the following categories:
- People: Names of individuals mentioned
- Companies: Organizations and brands
- Technologies: Tools, platforms, methodologies
- Concepts: Abstract ideas and theories

Return as comma-separated list with categories in parentheses:
John Doe (People), Apple (Companies), Machine Learning (Technologies)
```

## Output Configuration

### Directory Structure
```yaml
# Basic output directory
output_directory: "~/Documents/PodKnow"

# Organized by podcast
output_directory: "~/Documents/PodKnow/{podcast_title}"

# Organized by date
output_directory: "~/Documents/PodKnow/{year}/{month}"
```

### Filename Templates
```yaml
# Basic template
filename_template: "{podcast_title}_{episode_number}_{date}.md"

# Date-focused
filename_template: "{date}_{podcast_title}_ep{episode_number}.md"

# Title-focused
filename_template: "{episode_title}_{podcast_title}.md"

# Custom format
filename_template: "transcript_{podcast_title}_{date}.md"
```

Available variables:
- `{podcast_title}`: Sanitized podcast name
- `{episode_title}`: Sanitized episode title
- `{episode_number}`: Episode number (if available)
- `{date}`: Publication date (YYYY-MM-DD)
- `{year}`, `{month}`, `{day}`: Date components

### Content Options
```yaml
# Include word-level timestamps
include_timestamps: true

# Enable paragraph detection
paragraph_detection: true

# Maximum audio file size (MB)
max_audio_size_mb: 500
```

## Performance Tuning

### Transcription Settings
```yaml
# Whisper model selection (speed vs accuracy)
whisper_model: "tiny"    # Fastest, least accurate
whisper_model: "base"    # Good balance (recommended)
whisper_model: "small"   # Better accuracy
whisper_model: "medium"  # High accuracy
whisper_model: "large"   # Best accuracy, slowest

# Apple Silicon optimization
use_fp16: true

# Audio processing
download_timeout: 300    # 5 minutes
chunk_size: 8192        # 8KB chunks
```

### Analysis Settings
```yaml
# Response length control
max_tokens: 4000        # Longer responses
max_tokens: 2000        # Shorter, faster responses

# Creativity control
temperature: 0.1        # More consistent (recommended)
temperature: 0.5        # More creative

# Content limits
max_analysis_length: 50000  # Max characters to analyze
min_transcription_length: 100  # Skip very short transcripts
```

### Rate Limiting
```yaml
# API retry settings
max_retries: 3
retry_delay: 1.0
exponential_backoff: true

# Search timeouts
search_timeout: 10
```

## Logging Configuration

### Log Levels
```yaml
log_level: "DEBUG"    # Detailed debugging info
log_level: "INFO"     # General information (recommended)
log_level: "WARNING"  # Only warnings and errors
log_level: "ERROR"    # Only errors
```

### Log Files
```yaml
# Enable file logging
log_file: "~/.podknow/logs/podknow.log"

# Disable file logging
log_file: ""

# Log rotation
max_log_size_mb: 10
log_backup_count: 5
```

## Environment Variables

Override configuration settings with environment variables:

```bash
# API Keys
export CLAUDE_API_KEY="your-key"
export SPOTIFY_CLIENT_ID="your-id"
export SPOTIFY_CLIENT_SECRET="your-secret"

# Paths
export PODKNOW_OUTPUT_DIR="~/Custom/Path"
export PODKNOW_CONFIG_PATH="~/custom-config.md"

# Logging
export PODKNOW_LOG_LEVEL="DEBUG"
export PODKNOW_LOG_FILE="~/custom.log"
```

## Advanced Configuration

### Custom Discovery Settings
```yaml
# Search result limits
default_search_limit: 20

# Platform priorities (higher = preferred)
platform_priorities:
  itunes: 10      # Prefer iTunes (has RSS feeds)
  spotify: 5      # Secondary option

# Deduplication
similarity_threshold: 0.8  # 80% similarity = duplicate
```

### Audio Processing
```yaml
# Supported formats
supported_formats: [".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"]

# Language detection
language: "en"              # Force English
language: "auto"            # Auto-detect (experimental)

# Quality settings
word_timestamps: true       # Enable for paragraph detection
condition_on_previous_text: true  # Better context awareness
```

## Troubleshooting

### Common Issues

1. **API Key Not Working**
   ```bash
   # Check if key is set
   podknow config-status
   
   # Test with verbose output
   podknow search "test" --verbose
   ```

2. **Configuration Not Loading**
   ```bash
   # Check file location and syntax
   podknow config-status
   
   # Recreate default config
   podknow setup --force
   ```

3. **Prompts Not Working**
   - Verify YAML syntax in configuration file
   - Check prompt block formatting (triple backticks)
   - Ensure required prompts are present

4. **Performance Issues**
   - Reduce `max_tokens` for faster responses
   - Use smaller Whisper model (`tiny` or `base`)
   - Increase `retry_delay` for rate limiting

### Validation Commands
```bash
# Check overall status
podknow config-status

# Test search functionality
podknow search "test podcast" --limit 1 --verbose

# Validate configuration file
python -c "import yaml; yaml.safe_load(open('~/.podknow/config.md').read())"
```

## Migration Guide

### From Version 0.1.x
If upgrading from an earlier version:

1. **Backup existing config**
   ```bash
   cp ~/.podknow/config.md ~/.podknow/config.md.backup
   ```

2. **Generate new config**
   ```bash
   podknow setup --force
   ```

3. **Migrate custom settings**
   - Copy API keys from backup
   - Merge custom prompts
   - Update any custom paths

### Configuration Schema Changes
- `analysis_settings` → Individual settings in root
- `output_settings` → Individual settings in root
- New prompt format with dedicated sections
- Enhanced YAML structure for better organization

## Best Practices

1. **Security**
   - Never commit API keys to version control
   - Use environment variables in shared environments
   - Regularly rotate API keys

2. **Organization**
   - Use descriptive output directory structures
   - Implement consistent filename templates
   - Enable logging for troubleshooting

3. **Performance**
   - Start with default settings
   - Adjust based on your hardware capabilities
   - Monitor API usage and costs

4. **Customization**
   - Test prompt changes with sample content
   - Keep backups of working configurations
   - Document custom modifications

## Support

For additional help:
- Check the troubleshooting section above
- Run commands with `--verbose` for detailed output
- Review log files for error details
- Consult the main PodKnow documentation