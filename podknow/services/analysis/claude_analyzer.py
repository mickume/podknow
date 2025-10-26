"""Claude API integration for content analysis."""

import asyncio
import time
from typing import Dict, List, Optional, Any
import json
import re

import httpx
from pydantic import BaseModel, Field

from ...models.analysis import AnalysisResult, Topic
from ...models.transcription import Transcription
from ...config.template_manager import TemplateManager, TemplateError
from ...exceptions import PodKnowError


class ClaudeRateLimitError(PodKnowError):
    """Raised when Claude API rate limits are exceeded."""
    pass


class ClaudeAPIError(PodKnowError):
    """Raised when Claude API returns an error."""
    pass


class ClaudeRequest(BaseModel):
    """Claude API request model."""
    
    model: str = Field(default="claude-3-sonnet-20240229")
    max_tokens: int = Field(default=4000)
    messages: List[Dict[str, str]] = Field(default_factory=list)
    temperature: float = Field(default=0.1, ge=0.0, le=1.0)
    system: Optional[str] = None


class ClaudeAnalyzer:
    """Claude API integration for AI-powered content analysis."""
    
    def __init__(
        self, 
        api_key: str,
        model: str = "claude-3-sonnet-20240229",
        template_manager: Optional[TemplateManager] = None,
        base_url: str = "https://api.anthropic.com/v1",
        timeout: float = 120.0,
        max_retries: int = 3
    ):
        """Initialize Claude analyzer with API configuration."""
        if not api_key:
            raise ValueError("Claude API key is required")
        
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.template_manager = template_manager or TemplateManager()
        
        # Rate limiting state
        self._last_request_time = 0.0
        self._min_request_interval = 1.0  # Minimum seconds between requests
        
        # HTTP client configuration
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            headers={
                "x-api-key": self.api_key,
                "content-type": "application/json",
                "anthropic-version": "2023-06-01"
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    def _get_sync_client(self) -> httpx.Client:
        """Get synchronous HTTP client for non-async usage."""
        return httpx.Client(
            timeout=httpx.Timeout(self.timeout),
            headers={
                "x-api-key": self.api_key,
                "content-type": "application/json",
                "anthropic-version": "2023-06-01"
            }
        )
    
    async def _rate_limit_delay(self) -> None:
        """Apply rate limiting delay between requests."""
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        
        if time_since_last < self._min_request_interval:
            delay = self._min_request_interval - time_since_last
            await asyncio.sleep(delay)
        
        self._last_request_time = time.time()
    
    def _rate_limit_delay_sync(self) -> None:
        """Apply rate limiting delay between requests (synchronous)."""
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        
        if time_since_last < self._min_request_interval:
            delay = self._min_request_interval - time_since_last
            time.sleep(delay)
        
        self._last_request_time = time.time()
    
    async def _make_request(self, request: ClaudeRequest) -> Dict[str, Any]:
        """Make async request to Claude API with error handling and retries."""
        if not self._client:
            raise ClaudeAPIError("Client not initialized. Use async context manager.")
        
        await self._rate_limit_delay()
        
        for attempt in range(self.max_retries):
            try:
                response = await self._client.post(
                    f"{self.base_url}/messages",
                    json=request.dict(exclude_none=True)
                )
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:
                    # Rate limit exceeded
                    retry_after = int(response.headers.get("retry-after", 60))
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(retry_after)
                        continue
                    else:
                        raise ClaudeRateLimitError(
                            f"Rate limit exceeded. Retry after {retry_after} seconds."
                        )
                elif response.status_code == 400:
                    error_data = response.json()
                    raise ClaudeAPIError(
                        f"Bad request: {error_data.get('error', {}).get('message', 'Unknown error')}"
                    )
                elif response.status_code == 401:
                    raise ClaudeAPIError("Invalid API key")
                elif response.status_code == 403:
                    raise ClaudeAPIError("Access forbidden. Check API key permissions.")
                else:
                    error_msg = f"API request failed with status {response.status_code}"
                    try:
                        error_data = response.json()
                        error_msg += f": {error_data.get('error', {}).get('message', 'Unknown error')}"
                    except:
                        pass
                    
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    else:
                        raise ClaudeAPIError(error_msg)
                        
            except httpx.TimeoutException:
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                else:
                    raise ClaudeAPIError("Request timeout")
            except httpx.RequestError as e:
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                else:
                    raise ClaudeAPIError(f"Request failed: {e}")
        
        raise ClaudeAPIError("Max retries exceeded")
    
    def _make_request_sync(self, request: ClaudeRequest) -> Dict[str, Any]:
        """Make synchronous request to Claude API with error handling and retries."""
        self._rate_limit_delay_sync()
        
        with self._get_sync_client() as client:
            for attempt in range(self.max_retries):
                try:
                    response = client.post(
                        f"{self.base_url}/messages",
                        json=request.dict(exclude_none=True)
                    )
                    
                    if response.status_code == 200:
                        return response.json()
                    elif response.status_code == 429:
                        # Rate limit exceeded
                        retry_after = int(response.headers.get("retry-after", 60))
                        if attempt < self.max_retries - 1:
                            time.sleep(retry_after)
                            continue
                        else:
                            raise ClaudeRateLimitError(
                                f"Rate limit exceeded. Retry after {retry_after} seconds."
                            )
                    elif response.status_code == 400:
                        error_data = response.json()
                        raise ClaudeAPIError(
                            f"Bad request: {error_data.get('error', {}).get('message', 'Unknown error')}"
                        )
                    elif response.status_code == 401:
                        raise ClaudeAPIError("Invalid API key")
                    elif response.status_code == 403:
                        raise ClaudeAPIError("Access forbidden. Check API key permissions.")
                    else:
                        error_msg = f"API request failed with status {response.status_code}"
                        try:
                            error_data = response.json()
                            error_msg += f": {error_data.get('error', {}).get('message', 'Unknown error')}"
                        except:
                            pass
                        
                        if attempt < self.max_retries - 1:
                            time.sleep(2 ** attempt)  # Exponential backoff
                            continue
                        else:
                            raise ClaudeAPIError(error_msg)
                            
                except httpx.TimeoutException:
                    if attempt < self.max_retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                    else:
                        raise ClaudeAPIError("Request timeout")
                except httpx.RequestError as e:
                    if attempt < self.max_retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                    else:
                        raise ClaudeAPIError(f"Request failed: {e}")
        
        raise ClaudeAPIError("Max retries exceeded")
    
    def _extract_content_from_response(self, response: Dict[str, Any]) -> str:
        """Extract text content from Claude API response."""
        try:
            content = response.get("content", [])
            if not content:
                raise ClaudeAPIError("Empty response content")
            
            # Claude returns content as a list of content blocks
            text_content = []
            for block in content:
                if block.get("type") == "text":
                    text_content.append(block.get("text", ""))
            
            if not text_content:
                raise ClaudeAPIError("No text content in response")
            
            return "\n".join(text_content).strip()
            
        except (KeyError, TypeError) as e:
            raise ClaudeAPIError(f"Invalid response format: {e}")
    
    async def generate_summary(
        self, 
        transcription: Transcription,
        episode_title: str = "",
        podcast_title: str = "",
        publication_date: str = ""
    ) -> str:
        """Generate episode summary using Claude API."""
        try:
            # Load and render summary template
            template_vars = {
                "episode_title": episode_title,
                "podcast_title": podcast_title,
                "duration": int(transcription.duration / 60),  # Convert to minutes
                "publication_date": publication_date,
                "transcription": transcription.text
            }
            
            prompt = self.template_manager.render_template("summary", **template_vars)
            
            request = ClaudeRequest(
                model=self.model,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            
            response = await self._make_request(request)
            return self._extract_content_from_response(response)
            
        except TemplateError as e:
            raise ClaudeAPIError(f"Template error: {e}")
        except Exception as e:
            raise ClaudeAPIError(f"Failed to generate summary: {e}")
    
    def generate_summary_sync(
        self, 
        transcription: Transcription,
        episode_title: str = "",
        podcast_title: str = "",
        publication_date: str = ""
    ) -> str:
        """Generate episode summary using Claude API (synchronous)."""
        try:
            # Load and render summary template
            template_vars = {
                "episode_title": episode_title,
                "podcast_title": podcast_title,
                "duration": int(transcription.duration / 60),  # Convert to minutes
                "publication_date": publication_date,
                "transcription": transcription.text
            }
            
            prompt = self.template_manager.render_template("summary", **template_vars)
            
            request = ClaudeRequest(
                model=self.model,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            
            response = self._make_request_sync(request)
            return self._extract_content_from_response(response)
            
        except TemplateError as e:
            raise ClaudeAPIError(f"Template error: {e}")
        except Exception as e:
            raise ClaudeAPIError(f"Failed to generate summary: {e}")
    
    async def extract_topics(
        self, 
        transcription: Transcription,
        episode_title: str = "",
        podcast_title: str = ""
    ) -> List[Topic]:
        """Extract topics from transcription using Claude API."""
        try:
            # Load and render topics template
            template_vars = {
                "episode_title": episode_title,
                "podcast_title": podcast_title,
                "transcription": transcription.text
            }
            
            prompt = self.template_manager.render_template("topics", **template_vars)
            
            request = ClaudeRequest(
                model=self.model,
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            
            response = await self._make_request(request)
            content = self._extract_content_from_response(response)
            
            return self._parse_topics_from_content(content)
            
        except TemplateError as e:
            raise ClaudeAPIError(f"Template error: {e}")
        except Exception as e:
            raise ClaudeAPIError(f"Failed to extract topics: {e}")
    
    def extract_topics_sync(
        self, 
        transcription: Transcription,
        episode_title: str = "",
        podcast_title: str = ""
    ) -> List[Topic]:
        """Extract topics from transcription using Claude API (synchronous)."""
        try:
            # Load and render topics template
            template_vars = {
                "episode_title": episode_title,
                "podcast_title": podcast_title,
                "transcription": transcription.text
            }
            
            prompt = self.template_manager.render_template("topics", **template_vars)
            
            request = ClaudeRequest(
                model=self.model,
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            
            response = self._make_request_sync(request)
            content = self._extract_content_from_response(response)
            
            return self._parse_topics_from_content(content)
            
        except TemplateError as e:
            raise ClaudeAPIError(f"Template error: {e}")
        except Exception as e:
            raise ClaudeAPIError(f"Failed to extract topics: {e}")
    
    async def extract_keywords(
        self, 
        transcription: Transcription,
        episode_title: str = "",
        podcast_title: str = ""
    ) -> List[str]:
        """Extract keywords from transcription using Claude API."""
        try:
            # Load and render keywords template
            template_vars = {
                "episode_title": episode_title,
                "podcast_title": podcast_title,
                "transcription": transcription.text
            }
            
            prompt = self.template_manager.render_template("keywords", **template_vars)
            
            request = ClaudeRequest(
                model=self.model,
                max_tokens=800,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            
            response = await self._make_request(request)
            content = self._extract_content_from_response(response)
            
            return self._parse_keywords_from_content(content)
            
        except TemplateError as e:
            raise ClaudeAPIError(f"Template error: {e}")
        except Exception as e:
            raise ClaudeAPIError(f"Failed to extract keywords: {e}")
    
    def extract_keywords_sync(
        self, 
        transcription: Transcription,
        episode_title: str = "",
        podcast_title: str = ""
    ) -> List[str]:
        """Extract keywords from transcription using Claude API (synchronous)."""
        try:
            # Load and render keywords template
            template_vars = {
                "episode_title": episode_title,
                "podcast_title": podcast_title,
                "transcription": transcription.text
            }
            
            prompt = self.template_manager.render_template("keywords", **template_vars)
            
            request = ClaudeRequest(
                model=self.model,
                max_tokens=800,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            
            response = self._make_request_sync(request)
            content = self._extract_content_from_response(response)
            
            return self._parse_keywords_from_content(content)
            
        except TemplateError as e:
            raise ClaudeAPIError(f"Template error: {e}")
        except Exception as e:
            raise ClaudeAPIError(f"Failed to extract keywords: {e}")
    
    async def analyze_content(
        self,
        transcription: Transcription,
        episode_title: str = "",
        podcast_title: str = "",
        publication_date: str = ""
    ) -> AnalysisResult:
        """Perform complete content analysis using Claude API."""
        start_time = time.time()
        
        try:
            # Run all analysis tasks concurrently
            summary_task = self.generate_summary(
                transcription, episode_title, podcast_title, publication_date
            )
            topics_task = self.extract_topics(transcription, episode_title, podcast_title)
            keywords_task = self.extract_keywords(transcription, episode_title, podcast_title)
            
            summary, topics, keywords = await asyncio.gather(
                summary_task, topics_task, keywords_task
            )
            
            processing_time = time.time() - start_time
            
            return AnalysisResult(
                summary=summary,
                topics=topics,
                keywords=keywords,
                metadata={
                    "episode_title": episode_title,
                    "podcast_title": podcast_title,
                    "publication_date": publication_date,
                    "transcription_duration": transcription.duration,
                    "transcription_word_count": transcription.word_count
                },
                analysis_provider="claude",
                analysis_model=self.model,
                processing_time=processing_time
            )
            
        except Exception as e:
            raise ClaudeAPIError(f"Content analysis failed: {e}")
    
    def analyze_content_sync(
        self,
        transcription: Transcription,
        episode_title: str = "",
        podcast_title: str = "",
        publication_date: str = ""
    ) -> AnalysisResult:
        """Perform complete content analysis using Claude API (synchronous)."""
        start_time = time.time()
        
        try:
            # Run analysis tasks sequentially
            summary = self.generate_summary_sync(
                transcription, episode_title, podcast_title, publication_date
            )
            topics = self.extract_topics_sync(transcription, episode_title, podcast_title)
            keywords = self.extract_keywords_sync(transcription, episode_title, podcast_title)
            
            processing_time = time.time() - start_time
            
            return AnalysisResult(
                summary=summary,
                topics=topics,
                keywords=keywords,
                metadata={
                    "episode_title": episode_title,
                    "podcast_title": podcast_title,
                    "publication_date": publication_date,
                    "transcription_duration": transcription.duration,
                    "transcription_word_count": transcription.word_count
                },
                analysis_provider="claude",
                analysis_model=self.model,
                processing_time=processing_time
            )
            
        except Exception as e:
            raise ClaudeAPIError(f"Content analysis failed: {e}")
    
    def _parse_topics_from_content(self, content: str) -> List[Topic]:
        """Parse topics from Claude response content."""
        topics = []
        
        # Look for numbered list pattern: "1. **Topic Name**: Description"
        pattern = r'^\d+\.\s*\*\*([^*]+)\*\*:\s*(.+)$'
        
        for line in content.split('\n'):
            line = line.strip()
            match = re.match(pattern, line)
            if match:
                name = match.group(1).strip()
                description = match.group(2).strip()
                topics.append(Topic(name=name, description=description))
        
        # Fallback: look for simpler patterns if no matches found
        if not topics:
            # Try pattern: "- **Topic Name**: Description"
            pattern = r'^[-*]\s*\*\*([^*]+)\*\*:\s*(.+)$'
            for line in content.split('\n'):
                line = line.strip()
                match = re.match(pattern, line)
                if match:
                    name = match.group(1).strip()
                    description = match.group(2).strip()
                    topics.append(Topic(name=name, description=description))
        
        return topics
    
    def _parse_keywords_from_content(self, content: str) -> List[str]:
        """Parse keywords from Claude response content."""
        keywords = []
        
        # Look for comma-separated keywords in the content
        # Find lines that contain keywords (usually after "Keywords:" or similar)
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Skip empty lines and headers
            if not line or line.startswith('#') or line.startswith('##'):
                continue
            
            # Look for lines with comma-separated values
            if ',' in line and not line.endswith(':'):
                # Split by comma and clean up
                line_keywords = [kw.strip() for kw in line.split(',')]
                line_keywords = [kw for kw in line_keywords if kw and len(kw) > 1]
                keywords.extend(line_keywords)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_keywords = []
        for keyword in keywords:
            if keyword.lower() not in seen:
                seen.add(keyword.lower())
                unique_keywords.append(keyword)
        
        return unique_keywords