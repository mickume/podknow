# PodKnow Configuration

This is the default configuration file for PodKnow. Copy this file to `~/.podknow/config.md` and customize it according to your needs.

## API Keys

```yaml
claude_api_key: "your-claude-api-key-here"
spotify_client_id: "your-spotify-client-id"  # Optional
spotify_client_secret: "your-spotify-client-secret"  # Optional
```

## Analysis Prompts

### Summary Prompt

```
Analyze this podcast transcription and provide a concise summary in 2-3 paragraphs. 
Focus on the main points, key insights, and overall theme of the episode. 
Be objective and informative, highlighting the most important takeaways for readers.
Avoid speculation and stick to what was actually discussed in the episode.
```

### Topic Extraction Prompt

```
Extract the main topics discussed in this podcast episode. 
List each topic in one sentence that captures the essence of what was discussed about that topic.
Focus on substantial topics that received meaningful discussion time.
Return only the topic sentences, one per line, without numbering or bullets.
Aim for 3-8 topics depending on the episode length and content diversity.
```

### Keyword Identification Prompt

```
Extract 30-40 highly specific, searchable keywords from this podcast content.

FOCUS ON (in priority order):
1. Named entities: Specific people, companies, products, books, organizations, places
2. Technical terms: Technologies, methodologies, frameworks, tools, platforms
3. Domain-specific concepts: Industry jargon, specialized terminology, specific theories
4. Concrete topics: Specific events, projects, research areas, market segments

EXAMPLES OF GOOD KEYWORDS:
- "GPT-4", "Tesla Model S", "Y Combinator", "Sam Altman", "The Lean Startup"
- "quantum entanglement", "CRISPR gene editing", "blockchain consensus"
- "venture capital", "product-market fit", "A/B testing"

EXAMPLES OF BAD KEYWORDS (DO NOT INCLUDE):
- "technology", "innovation", "future", "growth", "success"
- "artificial intelligence" (too broad - use specific AI technologies instead)
- "leadership", "strategy", "business" (unless referring to specific methodologies)

REQUIREMENTS:
- Return 130-40 keywords total
- Be as specific as possible - prefer "React hooks" over "web development"
- Include version numbers, model names, or other specifics when mentioned
- Use exact names as mentioned in the podcast

Return ONLY the keywords separated by commas.
```

### Sponsor Detection Prompt

```
Identify any sponsored content or advertisements in this transcription. 
Look for promotional language, product endorsements, discount codes, or clear advertising segments.
Pay attention to phrases like "this episode is sponsored by", "thanks to our sponsor", 
discount codes, special offers, or obvious product promotions.

For each sponsor segment found, provide:
1. The starting text (first few words where the sponsor content begins)
2. The ending text (last few words where the sponsor content ends)  
3. A confidence score from 0.0 to 1.0 indicating how certain you are this is sponsored content

Return the results in JSON format with this structure:
[{"start_text": "...", "end_text": "...", "confidence": 0.95}]

If no sponsor content is found, return an empty array: []

Be conservative - only mark content as sponsored if you're reasonably confident it's promotional.
```

## Output Settings

```yaml
# Default output directory for transcriptions
output_directory: "~/Documents/PodKnow"

# Filename template for generated files
# Available variables: {podcast_title}, {episode_title}, {episode_number}, {date}
filename_template: "{podcast_title}_{episode_number}_{date}.md"

# Whether to include timestamps in transcription segments
include_timestamps: true

# Enable paragraph detection using Whisper's built-in capabilities
paragraph_detection: true

# Maximum file size for audio downloads (in MB)
max_audio_size_mb: 500

# Temporary directory for audio files (leave empty for system default)
temp_directory: ""
```

## Transcription Settings

```yaml
# MLX-Whisper specific settings
whisper_model: "base"  # Options: tiny, base, small, medium, large
use_fp16: true  # Use half precision for Apple Silicon optimization
language: "en"  # Force English language detection
word_timestamps: true  # Enable word-level timestamps for paragraph detection

# Audio processing settings
supported_formats: [".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"]
download_timeout: 300  # Timeout for audio downloads in seconds
chunk_size: 8192  # Download chunk size in bytes
```

## Analysis Settings

```yaml
# Claude API settings
claude_model: "claude-sonnet-4-20250514"
max_tokens: 4000
temperature: 0.1  # Lower temperature for more consistent results

# Retry settings for API calls
max_retries: 3
retry_delay: 1.0  # Base delay in seconds
exponential_backoff: true

# Content processing
min_transcription_length: 100  # Minimum characters for analysis
max_analysis_length: 50000  # Maximum characters to send to Claude
```

## Logging Settings

```yaml
# Log level: DEBUG, INFO, WARNING, ERROR
log_level: "INFO"

# Log file location (leave empty to disable file logging)
log_file: "~/.podknow/logs/podknow.log"

# Maximum log file size in MB
max_log_size_mb: 10

# Number of backup log files to keep
log_backup_count: 5
```

## Discovery Settings

```yaml
# Default search settings
default_search_limit: 20
search_timeout: 10  # Timeout for search API calls

# Platform priorities (higher numbers = higher priority)
platform_priorities:
  itunes: 10
  spotify: 5

# Result deduplication settings
similarity_threshold: 0.8  # Threshold for considering results duplicates
```

---

## Configuration File Setup

To use this configuration:

1. Create the PodKnow configuration directory:
   ```bash
   mkdir -p ~/.podknow
   ```

2. Copy this file to your configuration directory:
   ```bash
   cp podknow/config/default_config.md ~/.podknow/config.md
   ```

3. Edit the configuration file with your API keys and preferences:
   ```bash
   nano ~/.podknow/config.md
   ```

4. Set your Claude API key (required for analysis):
   - Get an API key from https://console.anthropic.com/
   - Add it to the `claude_api_key` field in the configuration
   - Or set the `CLAUDE_API_KEY` environment variable

5. Optionally set Spotify credentials for enhanced podcast discovery:
   - Create a Spotify app at https://developer.spotify.com/
   - Add the client ID and secret to the configuration
   - Or set `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET` environment variables

## Environment Variables

PodKnow supports these environment variables as alternatives to configuration file settings:

- `CLAUDE_API_KEY`: Claude API key for analysis
- `SPOTIFY_CLIENT_ID`: Spotify app client ID
- `SPOTIFY_CLIENT_SECRET`: Spotify app client secret
- `PODKNOW_OUTPUT_DIR`: Default output directory
- `PODKNOW_LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `PODKNOW_LOG_FILE`: Log file path

Environment variables take precedence over configuration file settings.

## Customizing Prompts

The analysis prompts can be customized to match your specific needs:

### For Academic Research
- Modify the summary prompt to focus on methodology and findings
- Adjust topic extraction to identify research themes
- Customize keywords to prioritize: researchers, institutions, specific studies, methodologies, scientific terms (15-20 keywords)

### For Business Analysis
- Update prompts to focus on business insights and strategies
- Customize keywords to emphasize: company names, executives, product names, market terms, frameworks (15-20 keywords)
- Modify sponsor detection for business partnership identification

### For Content Creation
- Adjust summary style for audience engagement
- Focus topic extraction on content themes and narratives
- Customize keywords for SEO: specific topics, creator names, platforms, tools, trends (15-20 keywords)

## Troubleshooting Configuration

### Common Issues

1. **API Key Not Working**
   - Verify the key is correct and has proper permissions
   - Check if the key is properly quoted in YAML
   - Ensure no extra spaces or characters

2. **File Paths Not Working**
   - Use absolute paths or proper tilde expansion
   - Ensure directories exist and are writable
   - Check file permissions

3. **Prompts Not Loading**
   - Verify YAML syntax is correct
   - Check for proper indentation
   - Ensure prompt blocks are properly formatted

4. **Performance Issues**
   - Adjust `max_tokens` for faster responses
   - Increase `retry_delay` for rate limiting
   - Reduce `max_analysis_length` for large files

### Getting Help

If you encounter issues with configuration:

1. Run PodKnow with `--verbose` flag for detailed logging
2. Check the log file for specific error messages
3. Verify all required dependencies are installed
4. Ensure API keys have proper permissions and quotas

For more help, refer to the main documentation or create an issue in the project repository.