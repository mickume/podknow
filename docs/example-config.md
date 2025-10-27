# PodKnow Configuration Example

This is an example configuration file for PodKnow. Copy this to `~/.podknow/config.md` and customize it according to your needs.

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
Identify relevant keywords and tags for this podcast content. 
Focus on specific terms, concepts, people, companies, technologies, or methodologies mentioned.
Include both explicit mentions and implicit themes that would help categorize this content.
Return ONLY the keywords separated by commas. Do not include any explanatory text, introductions, or additional commentary. Just the keywords.
Prioritize terms that would be useful for search and categorization.
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

## Usage Instructions

1. **Copy this file to your configuration directory:**
   ```bash
   mkdir -p ~/.podknow
   cp docs/example-config.md ~/.podknow/config.md
   ```

2. **Add your Claude API key:**
   - Get an API key from https://console.anthropic.com/
   - Replace "your-claude-api-key-here" with your actual key

3. **Optionally add Spotify credentials:**
   - Create a Spotify app at https://developer.spotify.com/
   - Add the client ID and secret to the configuration

4. **Customize the prompts for your use case:**
   - Modify the analysis prompts to match your specific needs
   - See the examples below for different use cases

## Prompt Customization Examples

### Academic Research Configuration

```markdown
### Summary Prompt
```
Analyze this academic podcast transcription focusing on research methodology, 
key findings, and scholarly contributions. Provide a structured summary that 
highlights the research questions, methods used, main results, and implications 
for the field. Use formal academic language appropriate for literature reviews.
Include citations or references mentioned in the discussion.
```

### Topic Extraction Prompt
```
Extract the main research topics and themes discussed in this academic podcast. 
Focus on methodological approaches, theoretical frameworks, and empirical findings.
List each topic as a complete sentence that captures the academic contribution.
Prioritize topics that represent significant research areas or novel insights.
Return 4-10 topics depending on the episode's academic depth.
```

### Keyword Identification Prompt
```
Identify academic keywords and research terms from this podcast content.
Focus on: research methodologies, theoretical concepts, academic disciplines,
statistical methods, research tools, scholarly terminology, and field-specific jargon.
Include author names, institution names, and publication titles when mentioned.
Return only the keywords separated by commas, prioritizing terms useful for academic indexing.
```
```

### Business Analysis Configuration

```markdown
### Summary Prompt
```
Summarize this business podcast focusing on strategic insights, market trends, 
and actionable recommendations. Highlight key business metrics, competitive 
advantages, growth strategies, and market opportunities discussed. 
Frame the summary for business professionals seeking practical insights and 
decision-making guidance. Include specific numbers, percentages, or data points mentioned.
```

### Topic Extraction Prompt
```
Extract the main business topics and strategic themes discussed in this episode.
Focus on market analysis, business strategies, competitive dynamics, financial insights,
and operational excellence topics. List each topic as a sentence that captures
the business value and strategic importance. Prioritize topics with actionable insights.
Return 5-8 topics that would be relevant for business strategy discussions.
```

### Keyword Identification Prompt
```
Identify business and industry keywords from this podcast content.
Focus on: company names, industry terms, business strategies, market segments,
financial metrics, technology platforms, business models, and competitive advantages.
Include executive names, brand names, and specific business terminology.
Return only the keywords separated by commas, prioritizing terms useful for business intelligence.
```
```

### Content Creation Configuration

```markdown
### Summary Prompt
```
Create an engaging summary of this podcast episode that captures the main 
narrative, interesting anecdotes, and key takeaways. Write in a conversational 
tone that would appeal to the podcast's target audience and encourage further 
listening. Highlight memorable quotes, surprising insights, and entertaining moments.
Focus on the human elements and storytelling aspects of the discussion.
```

### Topic Extraction Prompt
```
Extract the main content themes and narrative elements discussed in this episode.
Focus on storytelling elements, key messages, audience insights, and engaging topics
that would resonate with content creators and their audiences. List each topic
as an engaging sentence that captures the entertainment or educational value.
Return 4-7 topics that would be useful for content planning and audience engagement.
```

### Keyword Identification Prompt
```
Identify content and media keywords from this podcast.
Focus on: content formats, platforms, audience demographics, engagement strategies,
creator tools, media trends, storytelling techniques, and audience interests.
Include creator names, platform names, and content-specific terminology.
Return only the keywords separated by commas, prioritizing terms useful for content strategy.
```
```

### Journalism Configuration

```markdown
### Summary Prompt
```
Analyze this podcast transcription from a journalistic perspective, focusing on
newsworthy elements, factual claims, source credibility, and public interest angles.
Provide a structured summary that highlights key facts, quotes from credible sources,
and potential story leads. Identify any claims that would require fact-checking
or additional verification. Use objective, news-style language.
```

### Topic Extraction Prompt
```
Extract the main news topics and journalistic angles discussed in this episode.
Focus on current events, policy implications, social issues, and newsworthy developments.
List each topic as a clear, factual sentence suitable for news reporting.
Prioritize topics with public interest value and newsworthiness.
Return 3-6 topics that could serve as the basis for news stories or investigations.
```

### Keyword Identification Prompt
```
Identify news and journalism keywords from this podcast content.
Focus on: news topics, policy areas, government entities, public figures,
current events, social issues, and journalistic beats (politics, technology, health, etc.).
Include names of officials, organizations, and specific policy or legal terms.
Return only the keywords separated by commas, prioritizing terms useful for news categorization.
```
```

## Environment Variables Alternative

Instead of editing the configuration file, you can use environment variables:

```bash
# API Keys
export CLAUDE_API_KEY="your-claude-api-key"
export SPOTIFY_CLIENT_ID="your-spotify-client-id"
export SPOTIFY_CLIENT_SECRET="your-spotify-client-secret"

# Paths
export PODKNOW_OUTPUT_DIR="~/Custom/Output/Path"
export PODKNOW_CONFIG_PATH="~/custom-config.md"

# Logging
export PODKNOW_LOG_LEVEL="DEBUG"
export PODKNOW_LOG_FILE="~/podknow-debug.log"

# Then run PodKnow normally
podknow search "technology podcast"
```

## Validation

After creating your configuration file, validate it:

```bash
# Check configuration status
podknow config-status

# Test with a simple search
podknow search "test" --limit 1 --verbose

# Verify prompts are loading correctly
podknow transcribe --help  # Should show no configuration errors
```

## Notes

- **File Format**: The configuration uses Markdown with embedded YAML blocks
- **Prompt Sections**: Each prompt must be in its own section with triple backticks
- **YAML Syntax**: Ensure proper indentation and quoting in YAML blocks
- **File Location**: Must be at `~/.podknow/config.md` or set via `PODKNOW_CONFIG_PATH`
- **Permissions**: Ensure the configuration file is readable by the PodKnow process

For more detailed information, see the full [Configuration Guide](configuration.md).