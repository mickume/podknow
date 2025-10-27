"""
Analysis service for AI-powered content analysis using Claude API.
"""

import json
import time
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
import anthropic
from anthropic import Anthropic
from anthropic.types import Message

from ..models.analysis import AnalysisResult, SponsorSegment
from ..models.output import OutputDocument
from ..models.episode import EpisodeMetadata
from ..exceptions import AnalysisError, ClaudeAPIError, ConfigurationError
from ..config.manager import ConfigManager
from ..constants import DEFAULT_CLAUDE_MODEL


class ClaudeAPIClient:
    """Claude API client with authentication, rate limiting, and error handling."""
    
    def __init__(self, api_key: str, model: str = DEFAULT_CLAUDE_MODEL, max_retries: int = 3, retry_delay: float = 1.0):
        """Initialize Claude API client.
        
        Args:
            api_key: Claude API key
            model: Claude model to use (default: DEFAULT_CLAUDE_MODEL)
            max_retries: Maximum number of retry attempts
            retry_delay: Base delay between retries in seconds
        """
        if not api_key or not api_key.strip():
            raise ConfigurationError("Claude API key is required")
        
        self.client = Anthropic(api_key=api_key)
        self.model = model
        self.max_retries = max_retries
        self.retry_delay = retry_delay
    
    def send_message(self, prompt: str, system_prompt: str = None, max_tokens: int = 4000, show_progress: bool = False) -> str:
        """Send a message to Claude API with retry logic.
        
        Args:
            prompt: User prompt to send
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens in response
            show_progress: Whether to show progress indicator for this call
            
        Returns:
            Claude's response text
            
        Raises:
            ClaudeAPIError: If API call fails after retries
        """
        messages = [{"role": "user", "content": prompt}]
        
        # Estimate response time based on prompt length (rough approximation)
        prompt_length = len(prompt) + (len(system_prompt) if system_prompt else 0)
        estimated_time = min(max(prompt_length / 1000, 2.0), 30.0)  # 2-30 seconds
        
        if show_progress:
            try:
                from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
                rich_available = True
            except ImportError:
                rich_available = False

            import threading

            if rich_available:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[bold magenta]Calling Claude API"),
                    TextColumn("•"),
                    TimeElapsedColumn(),
                    refresh_per_second=4,
                ) as progress:
                    
                    task = progress.add_task("claude_api", total=None)
                    
                    # Initialize variables for thread communication
                    response_result = None
                    api_error = None
                    
                    def make_api_call():
                        nonlocal response_result, api_error
                        for attempt in range(self.max_retries + 1):
                            try:
                                kwargs = {
                                    "model": self.model,
                                    "max_tokens": max_tokens,
                                    "messages": messages
                                }
                                
                                if system_prompt:
                                    kwargs["system"] = system_prompt
                                
                                response = self.client.messages.create(**kwargs)
                                
                                if response.content and len(response.content) > 0:
                                    response_result = response.content[0].text
                                    return
                                else:
                                    raise ClaudeAPIError("Empty response from Claude API")
                                    
                            except anthropic.RateLimitError as e:
                                if attempt < self.max_retries:
                                    delay = self.retry_delay * (2 ** attempt)
                                    time.sleep(delay)
                                    continue
                                api_error = ClaudeAPIError(f"Rate limit exceeded after {self.max_retries} retries", details=str(e))
                                return
                                
                            except anthropic.APIError as e:
                                if attempt < self.max_retries and e.status_code >= 500:
                                    delay = self.retry_delay * (2 ** attempt)
                                    time.sleep(delay)
                                    continue
                                api_error = ClaudeAPIError(f"Claude API error: {e.message}", status_code=e.status_code, details=str(e))
                                return
                                
                            except Exception as e:
                                if attempt < self.max_retries:
                                    delay = self.retry_delay * (2 ** attempt)
                                    time.sleep(delay)
                                    continue
                                api_error = ClaudeAPIError(f"Unexpected error calling Claude API: {str(e)}")
                                return
                        
                        api_error = ClaudeAPIError(f"Failed to get response after {self.max_retries} retries")
                    
                    # Start API call in background thread
                    api_thread = threading.Thread(target=make_api_call)
                    api_thread.start()
                    
                    # Update progress while API call is running
                    while api_thread.is_alive():
                        progress.update(task, advance=0.1)
                        time.sleep(0.25)
                    
                    # Wait for API call to complete
                    api_thread.join()
                    
                    # Mark as completed
                    progress.update(task, completed=True)
                    
                    if api_error:
                        raise api_error
                    
                    return response_result
            else:
                # Fallback when rich is not available but progress is requested
                print("Calling Claude API...")
                # Fall through to synchronous implementation
        
        # Synchronous implementation (used when progress=False or rich not available)
        for attempt in range(self.max_retries + 1):
            try:
                kwargs = {
                    "model": self.model,
                    "max_tokens": max_tokens,
                    "messages": messages
                }
                
                if system_prompt:
                    kwargs["system"] = system_prompt
                
                response = self.client.messages.create(**kwargs)
                
                if response.content and len(response.content) > 0:
                    return response.content[0].text
                else:
                    raise ClaudeAPIError("Empty response from Claude API")
                    
            except anthropic.RateLimitError as e:
                if attempt < self.max_retries:
                    delay = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    time.sleep(delay)
                    continue
                raise ClaudeAPIError(f"Rate limit exceeded after {self.max_retries} retries", details=str(e))
                
            except anthropic.APIError as e:
                if attempt < self.max_retries and e.status_code >= 500:
                    delay = self.retry_delay * (2 ** attempt)
                    time.sleep(delay)
                    continue
                raise ClaudeAPIError(f"Claude API error: {e.message}", status_code=e.status_code, details=str(e))
                
            except Exception as e:
                if attempt < self.max_retries:
                    delay = self.retry_delay * (2 ** attempt)
                    time.sleep(delay)
                    continue
                raise ClaudeAPIError(f"Unexpected error calling Claude API: {str(e)}")
        
        raise ClaudeAPIError(f"Failed to get response after {self.max_retries} retries")


class AnalysisService:
    """Service for AI-powered content analysis using Claude API."""
    
    def __init__(self, api_key: str, model: str = DEFAULT_CLAUDE_MODEL, prompts: Optional[Dict[str, str]] = None):
        """Initialize analysis service.
        
        Args:
            api_key: Claude API key
            model: Claude model to use (default: DEFAULT_CLAUDE_MODEL)
            prompts: Optional custom prompts for different analysis types
        """
        self.claude_client = ClaudeAPIClient(api_key, model=model)
        self.prompts = prompts or self._load_prompts_from_config()
    
    def _load_prompts_from_config(self) -> Dict[str, str]:
        """Load prompts from configuration file, with fallback to defaults."""
        try:
            config_manager = ConfigManager()
            if config_manager.config_exists():
                config = config_manager.load_config()
                # Map config prompt names to service prompt names
                prompt_mapping = {
                    'summary': 'summary',
                    'topics': 'topics', 
                    'keywords': 'keywords',
                    'sponsor_detection': 'sponsor_detection'  # Both config and service use 'sponsor_detection'
                }
                
                prompts = {}
                for service_key, config_key in prompt_mapping.items():
                    if config_key in config.prompts and config.prompts[config_key].strip():
                        prompts[service_key] = config.prompts[config_key]
                    else:
                        # Use fallback for missing prompts
                        prompts[service_key] = self._get_default_prompts()[service_key]
                
                return prompts
            else:
                # No config file, use defaults
                return self._get_default_prompts()
                
        except Exception as e:
            # If config loading fails, fall back to defaults
            print(f"Warning: Failed to load prompts from config, using defaults: {e}")
            return self._get_default_prompts()
    
    def _get_default_prompts(self) -> Dict[str, str]:
        """Get default prompts for analysis tasks (fallback)."""
        return {
            "summary": """Analyze this podcast transcription and provide a concise summary in 2-3 paragraphs. 
Focus on the main points, key insights, and overall theme of the episode. 
Be objective and informative.""",
            
            "topics": """Extract the main topics discussed in this podcast episode. 
List each topic in one sentence that captures the essence of what was discussed. 
Return only the topic sentences, one per line, without numbering or bullets.""",
            
            "keywords": """Identify relevant keywords and tags for this podcast content. 
Focus on specific terms, concepts, people, companies, or technologies mentioned. 
Return ONLY the keywords separated by commas. Do not include any explanatory text, introductions, or additional commentary. Just the keywords.""",
            
            "sponsor_detection": """Identify any sponsored content or advertisements in this transcription. 
Look for promotional language, product endorsements, discount codes, or clear advertising segments.
For each sponsor segment found, provide the starting text (first few words) and ending text (last few words) of the segment.
Also provide a confidence score from 0.0 to 1.0 indicating how certain you are this is sponsored content.
Return the results in JSON format with this structure:
[{"start_text": "...", "end_text": "...", "confidence": 0.95}]
If no sponsor content is found, return an empty array: []"""
        }
    
    def analyze_transcription(self, transcription: str) -> AnalysisResult:
        """Perform complete analysis of transcription."""
        if not transcription or not transcription.strip():
            raise AnalysisError("Transcription text is required for analysis")
        
        try:
            # Show progress for analysis steps
            try:
                from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
                rich_available = True
            except ImportError:
                rich_available = False

            # Estimate transcription length for progress context
            word_count = len(transcription.split())
            char_count = len(transcription)
            
            if rich_available:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[bold green]{task.description}"),
                    BarColumn(bar_width=None),
                    TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                    TextColumn("•"),
                    TimeElapsedColumn(),
                    refresh_per_second=4,
                ) as progress:
                    
                    # Add overall analysis task
                    analysis_task = progress.add_task(
                        f"Analyzing content ({word_count:,} words)", 
                        total=100
                    )
                    
                    start_time = time.time()
                    
                    # Step 1: Generate summary (25% of progress)
                    progress.update(analysis_task, description="[bold green]Generating summary")
                    try:
                        summary = self.generate_summary(transcription, show_progress=False)
                    except Exception as e:
                        print(f"Warning: Summary generation failed: {e}")
                        summary = "Summary generation failed."
                    progress.update(analysis_task, completed=25)
                    
                    # Step 2: Extract topics (50% of progress)
                    progress.update(analysis_task, description="[bold green]Extracting topics")
                    try:
                        topics = self.extract_topics(transcription, show_progress=False)
                    except Exception as e:
                        print(f"Warning: Topic extraction failed: {e}")
                        topics = []
                    progress.update(analysis_task, completed=50)
                    
                    # Step 3: Identify keywords (75% of progress)
                    progress.update(analysis_task, description="[bold green]Identifying keywords")
                    try:
                        keywords = self.identify_keywords(transcription, show_progress=False)
                    except Exception as e:
                        print(f"Warning: Keyword identification failed: {e}")
                        keywords = []
                    progress.update(analysis_task, completed=75)
                    
                    # Step 4: Detect sponsor content (100% of progress)
                    progress.update(analysis_task, description="[bold green]Detecting sponsor content")
                    try:
                        sponsor_segments = self.detect_sponsor_content(transcription, show_progress=False)
                    except Exception as e:
                        print(f"Warning: Sponsor detection failed: {e}")
                        sponsor_segments = []
                    progress.update(analysis_task, completed=100)
                    
                    # Calculate analysis time
                    analysis_time = time.time() - start_time
            else:
                # Fallback when rich is not available
                start_time = time.time()
                
                print("Generating summary...")
                try:
                    summary = self.generate_summary(transcription, show_progress=False)
                except Exception as e:
                    print(f"Warning: Summary generation failed: {e}")
                    summary = "Summary generation failed."
                
                print("Extracting topics...")
                try:
                    topics = self.extract_topics(transcription, show_progress=False)
                except Exception as e:
                    print(f"Warning: Topic extraction failed: {e}")
                    topics = []
                
                print("Identifying keywords...")
                try:
                    keywords = self.identify_keywords(transcription, show_progress=False)
                except Exception as e:
                    print(f"Warning: Keyword identification failed: {e}")
                    keywords = []
                
                print("Detecting sponsor content...")
                try:
                    sponsor_segments = self.detect_sponsor_content(transcription, show_progress=False)
                except Exception as e:
                    print(f"Warning: Sponsor detection failed: {e}")
                    sponsor_segments = []
                
                analysis_time = time.time() - start_time
            
            # Show completion summary
            print(f"✅ Analysis completed!")
            print(f"   Summary: {len(summary.split())} words")
            print(f"   Topics: {len(topics)} identified")
            print(f"   Keywords: {len(keywords)} extracted")
            print(f"   Sponsor segments: {len(sponsor_segments)} detected")
            print(f"   Processing time: {analysis_time:.1f}s")
            
            return AnalysisResult(
                summary=summary,
                topics=topics,
                keywords=keywords,
                sponsor_segments=sponsor_segments
            )
            
        except Exception as e:
            if isinstance(e, (AnalysisError, ClaudeAPIError)):
                raise
            raise AnalysisError(f"Failed to analyze transcription: {str(e)}")
    
    def generate_summary(self, transcription: str, show_progress: bool = True) -> str:
        """Generate content summary using Claude AI."""
        if not transcription or not transcription.strip():
            raise AnalysisError("Transcription text is required for summary generation")
        
        try:
            prompt = f"{self.prompts['summary']}\n\nTranscription:\n{transcription}"
            response = self.claude_client.send_message(prompt, show_progress=show_progress)
            
            if not response or not response.strip():
                raise AnalysisError("Claude API returned empty summary")
            
            return response.strip()
            
        except ClaudeAPIError:
            raise
        except Exception as e:
            raise AnalysisError(f"Failed to generate summary: {str(e)}")
    
    def extract_topics(self, transcription: str, show_progress: bool = True) -> List[str]:
        """Extract main topics from transcription."""
        if not transcription or not transcription.strip():
            raise AnalysisError("Transcription text is required for topic extraction")
        
        try:
            prompt = f"{self.prompts['topics']}\n\nTranscription:\n{transcription}"
            response = self.claude_client.send_message(prompt, show_progress=show_progress)
            
            if not response or not response.strip():
                raise AnalysisError("Claude API returned empty topics response")
            
            # Split response into individual topics and clean them
            topics = [topic.strip() for topic in response.strip().split('\n') if topic.strip()]
            
            if not topics:
                raise AnalysisError("No topics extracted from transcription")
            
            return topics
            
        except ClaudeAPIError:
            raise
        except Exception as e:
            raise AnalysisError(f"Failed to extract topics: {str(e)}")
    
    def identify_keywords(self, transcription: str, show_progress: bool = True) -> List[str]:
        """Identify relevant keywords from transcription."""
        if not transcription or not transcription.strip():
            raise AnalysisError("Transcription text is required for keyword identification")
        
        try:
            prompt = f"{self.prompts['keywords']}\n\nTranscription:\n{transcription}"
            response = self.claude_client.send_message(prompt, show_progress=show_progress)
            
            if not response or not response.strip():
                raise AnalysisError("Claude API returned empty keywords response")
            
            # Clean response by removing common prefatory text
            cleaned_response = response.strip()
            
            # Remove common prefixes that Claude might add
            prefixes_to_remove = [
                "Here are the relevant keywords:",
                "Here are the keywords:",
                "Relevant keywords:",
                "Keywords:",
                "The relevant keywords are:",
                "The keywords are:"
            ]
            
            for prefix in prefixes_to_remove:
                if cleaned_response.lower().startswith(prefix.lower()):
                    cleaned_response = cleaned_response[len(prefix):].strip()
                    break
            
            # Split by commas and clean keywords
            keywords = [keyword.strip() for keyword in cleaned_response.split(',') if keyword.strip()]
            
            if not keywords:
                raise AnalysisError("No keywords extracted from transcription")
            
            return keywords
            
        except ClaudeAPIError:
            raise
        except Exception as e:
            raise AnalysisError(f"Failed to identify keywords: {str(e)}")
    
    def detect_sponsor_content(self, transcription: str, show_progress: bool = True) -> List[SponsorSegment]:
        """Detect sponsor content segments in transcription."""
        if not transcription or not transcription.strip():
            print("Warning: Empty transcription provided for sponsor detection")
            return []
        
        try:
            # Check if sponsor_detection prompt is available
            if 'sponsor_detection' not in self.prompts:
                print("Warning: Sponsor detection prompt not available, skipping sponsor detection")
                return []
            
            prompt = f"{self.prompts['sponsor_detection']}\n\nTranscription:\n{transcription}"
            response = self.claude_client.send_message(prompt, show_progress=show_progress)
            
            if not response or not response.strip():
                return []  # No sponsor content found
            
            # Parse JSON response
            try:
                sponsor_data = json.loads(response.strip())
                if not isinstance(sponsor_data, list):
                    print("Warning: Claude returned invalid sponsor data format, skipping sponsor detection")
                    return []
                
                sponsor_segments = []
                for item in sponsor_data:
                    if not isinstance(item, dict):
                        continue
                    
                    start_text = item.get('start_text', '').strip()
                    end_text = item.get('end_text', '').strip()
                    confidence = item.get('confidence', 0.0)
                    
                    if start_text and end_text and isinstance(confidence, (int, float)):
                        sponsor_segments.append(SponsorSegment(
                            start_text=start_text,
                            end_text=end_text,
                            confidence=float(confidence)
                        ))
                
                return sponsor_segments
                
            except (json.JSONDecodeError, ValueError, KeyError) as e:
                # If JSON parsing fails, assume no sponsor content
                print(f"Warning: Failed to parse sponsor detection response: {e}")
                return []
            
        except ClaudeAPIError as e:
            # Claude API errors should be warnings for sponsor detection
            print(f"Warning: Claude API error during sponsor detection: {e}")
            return []
        except Exception as e:
            # Other errors should also be warnings for sponsor detection
            print(f"Warning: Failed to detect sponsor content: {e}")
            return []
    
    def generate_markdown_output(self, output_doc: OutputDocument) -> str:
        """Generate markdown output with analysis results integrated.
        
        Args:
            output_doc: OutputDocument containing metadata, transcription, and analysis
            
        Returns:
            Formatted markdown string with frontmatter and content
        """
        try:
            # Show progress for markdown generation
            from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
            import time
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]Generating markdown output"),
                BarColumn(bar_width=None),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                refresh_per_second=4,
            ) as progress:
                
                task = progress.add_task("markdown", total=100)
                
                # Generate frontmatter (20%)
                progress.update(task, description="[bold blue]Creating frontmatter")
                frontmatter = self._generate_frontmatter(output_doc)
                progress.update(task, completed=20)
                
                # Generate content sections (40%)
                progress.update(task, description="[bold blue]Formatting summary")
                summary_section = self._generate_summary_section(output_doc.analysis)
                progress.update(task, completed=40)
                
                # Generate topics section (60%)
                progress.update(task, description="[bold blue]Formatting topics")
                topics_section = self._generate_topics_section(output_doc.analysis)
                progress.update(task, completed=60)
                
                # Generate transcription section (80%)
                progress.update(task, description="[bold blue]Processing transcription")
                transcription_section = self._generate_transcription_section(
                    output_doc.transcription, 
                    output_doc.analysis.sponsor_segments
                )
                progress.update(task, completed=80)
                
                # Combine all sections (100%)
                progress.update(task, description="[bold blue]Finalizing document")
                markdown_content = f"""{frontmatter}

# Episode Summary

{output_doc.analysis.summary}

## Topics Covered

{topics_section}

## Transcription

{transcription_section}
"""
                progress.update(task, completed=100)
            
            # Show completion info
            word_count = len(markdown_content.split())
            line_count = len(markdown_content.split('\n'))
            print(f"✅ Markdown document generated!")
            print(f"   Document size: {word_count:,} words, {line_count:,} lines")
            
            return markdown_content
            
        except Exception as e:
            raise AnalysisError(f"Failed to generate markdown output: {str(e)}")
    
    def _generate_frontmatter(self, output_doc: OutputDocument) -> str:
        """Generate YAML frontmatter for the markdown document."""
        metadata = output_doc.metadata
        analysis = output_doc.analysis
        
        # Format keywords as YAML array
        keywords_yaml = json.dumps(analysis.keywords)
        
        frontmatter = f"""---
podcast_title: "{metadata.podcast_title}"
episode_title: "{metadata.episode_title}"
episode_number: {metadata.episode_number if metadata.episode_number else 'null'}
publication_date: "{metadata.publication_date.strftime('%Y-%m-%d')}"
duration: "{metadata.duration}"
transcribed_at: "{output_doc.processing_timestamp.strftime('%Y-%m-%dT%H:%M:%SZ')}"
audio_url: "{metadata.audio_url}"
keywords: {keywords_yaml}
sponsor_segments_detected: {len(analysis.sponsor_segments)}
---"""
        
        return frontmatter
    
    def _generate_summary_section(self, analysis: AnalysisResult) -> str:
        """Generate the summary section."""
        return analysis.summary
    
    def _generate_topics_section(self, analysis: AnalysisResult) -> str:
        """Generate the topics section with bullet points."""
        topics_list = []
        for topic in analysis.topics:
            topics_list.append(f"- {topic}")
        
        return "\n".join(topics_list)
    
    def _generate_transcription_section(self, transcription: str, sponsor_segments: List[SponsorSegment]) -> str:
        """Generate transcription section with sponsor content marked.
        
        Preserves original Whisper paragraph formatting while adding sponsor markers.
        """
        # Always start with the original transcription to preserve Whisper's paragraph detection
        if not sponsor_segments:
            return transcription
        
        # Work with the original transcription to preserve formatting
        marked_transcription = transcription
        
        # Find sponsor segments in the text with fuzzy matching
        segments_with_positions = []
        for segment in sponsor_segments:
            # Try to find the start and end text with some flexibility
            start_pos = self._find_text_position(marked_transcription, segment.start_text)
            if start_pos != -1:
                end_pos = self._find_text_position(marked_transcription, segment.end_text, start_pos)
                if end_pos != -1:
                    end_pos += len(segment.end_text)
                    segments_with_positions.append((start_pos, end_pos, segment))
        
        # Sort by start position (reverse order to avoid position shifts when inserting)
        segments_with_positions.sort(key=lambda x: x[0], reverse=True)
        
        # Insert sponsor markers while preserving paragraph breaks
        for start_pos, end_pos, segment in segments_with_positions:
            confidence_percent = int(segment.confidence * 100)
            
            # Use more subtle markers that don't disrupt paragraph flow
            sponsor_start = f"**[SPONSOR START - {confidence_percent}%]** "
            sponsor_end = f" **[SPONSOR END]**"
            
            marked_transcription = (
                marked_transcription[:start_pos] + 
                sponsor_start + 
                marked_transcription[start_pos:end_pos] + 
                sponsor_end + 
                marked_transcription[end_pos:]
            )
        
        return marked_transcription
    
    def _find_text_position(self, text: str, search_text: str, start_from: int = 0) -> int:
        """Find text position with some flexibility for minor variations."""
        # First try exact match
        pos = text.find(search_text, start_from)
        if pos != -1:
            return pos
        
        # If exact match fails, try with normalized whitespace
        normalized_search = ' '.join(search_text.split())
        normalized_text = ' '.join(text.split())
        
        pos = normalized_text.find(normalized_search, start_from)
        if pos != -1:
            # Convert position back to original text
            # This is approximate but should work for most cases
            words_before = len(normalized_text[:pos].split())
            original_words = text.split()
            if words_before < len(original_words):
                return text.find(original_words[words_before])
        
        return -1