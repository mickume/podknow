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
    
    def send_message(self, prompt: str, system_prompt: str = None, max_tokens: int = 4000) -> str:
        """Send a message to Claude API with retry logic.
        
        Args:
            prompt: User prompt to send
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens in response
            
        Returns:
            Claude's response text
            
        Raises:
            ClaudeAPIError: If API call fails after retries
        """
        messages = [{"role": "user", "content": prompt}]
        
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
                    'sponsors': 'sponsor_detection'  # Config uses 'sponsor_detection', service uses 'sponsors'
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
            
            "sponsors": """Identify any sponsored content or advertisements in this transcription. 
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
            # Generate all analysis components
            summary = self.generate_summary(transcription)
            topics = self.extract_topics(transcription)
            keywords = self.identify_keywords(transcription)
            sponsor_segments = self.detect_sponsor_content(transcription)
            
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
    
    def generate_summary(self, transcription: str) -> str:
        """Generate content summary using Claude AI."""
        if not transcription or not transcription.strip():
            raise AnalysisError("Transcription text is required for summary generation")
        
        try:
            prompt = f"{self.prompts['summary']}\n\nTranscription:\n{transcription}"
            response = self.claude_client.send_message(prompt)
            
            if not response or not response.strip():
                raise AnalysisError("Claude API returned empty summary")
            
            return response.strip()
            
        except ClaudeAPIError:
            raise
        except Exception as e:
            raise AnalysisError(f"Failed to generate summary: {str(e)}")
    
    def extract_topics(self, transcription: str) -> List[str]:
        """Extract main topics from transcription."""
        if not transcription or not transcription.strip():
            raise AnalysisError("Transcription text is required for topic extraction")
        
        try:
            prompt = f"{self.prompts['topics']}\n\nTranscription:\n{transcription}"
            response = self.claude_client.send_message(prompt)
            
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
    
    def identify_keywords(self, transcription: str) -> List[str]:
        """Identify relevant keywords from transcription."""
        if not transcription or not transcription.strip():
            raise AnalysisError("Transcription text is required for keyword identification")
        
        try:
            prompt = f"{self.prompts['keywords']}\n\nTranscription:\n{transcription}"
            response = self.claude_client.send_message(prompt)
            
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
    
    def detect_sponsor_content(self, transcription: str) -> List[SponsorSegment]:
        """Detect sponsor content segments in transcription."""
        if not transcription or not transcription.strip():
            raise AnalysisError("Transcription text is required for sponsor detection")
        
        try:
            prompt = f"{self.prompts['sponsors']}\n\nTranscription:\n{transcription}"
            response = self.claude_client.send_message(prompt)
            
            if not response or not response.strip():
                return []  # No sponsor content found
            
            # Parse JSON response
            try:
                sponsor_data = json.loads(response.strip())
                if not isinstance(sponsor_data, list):
                    raise ValueError("Response must be a JSON array")
                
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
                return []
            
        except ClaudeAPIError:
            raise
        except Exception as e:
            raise AnalysisError(f"Failed to detect sponsor content: {str(e)}")
    
    def generate_markdown_output(self, output_doc: OutputDocument) -> str:
        """Generate markdown output with analysis results integrated.
        
        Args:
            output_doc: OutputDocument containing metadata, transcription, and analysis
            
        Returns:
            Formatted markdown string with frontmatter and content
        """
        try:
            # Generate frontmatter
            frontmatter = self._generate_frontmatter(output_doc)
            
            # Generate content sections
            summary_section = self._generate_summary_section(output_doc.analysis)
            topics_section = self._generate_topics_section(output_doc.analysis)
            transcription_section = self._generate_transcription_section(
                output_doc.transcription, 
                output_doc.analysis.sponsor_segments
            )
            
            # Combine all sections
            markdown_content = f"""{frontmatter}

# Episode Summary

{output_doc.analysis.summary}

## Topics Covered

{topics_section}

## Transcription

{transcription_section}
"""
            
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