"""Ollama local LLM integration for content analysis."""

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


class OllamaConnectionError(PodKnowError):
    """Raised when unable to connect to Ollama server."""
    pass


class OllamaModelError(PodKnowError):
    """Raised when Ollama model is not available or fails."""
    pass


class OllamaAPIError(PodKnowError):
    """Raised when Ollama API returns an error."""
    pass


class OllamaRequest(BaseModel):
    """Ollama API request model."""
    
    model: str = Field(...)
    prompt: str = Field(...)
    stream: bool = Field(default=False)
    options: Dict[str, Any] = Field(default_factory=dict)


class OllamaAnalyzer:
    """Ollama local LLM integration for AI-powered content analysis."""
    
    def __init__(
        self,
        model: str = "llama2",
        base_url: str = "http://localhost:11434",
        template_manager: Optional[TemplateManager] = None,
        timeout: float = 300.0,  # Longer timeout for local models
        max_retries: int = 2
    ):
        """Initialize Ollama analyzer with configuration."""
        self.model = model
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        self.template_manager = template_manager or TemplateManager()
        
        # HTTP client configuration
        self._client: Optional[httpx.AsyncClient] = None
        
        # Model availability cache
        self._model_available: Optional[bool] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            headers={"content-type": "application/json"}
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
            headers={"content-type": "application/json"}
        )
    
    async def _check_server_health(self) -> bool:
        """Check if Ollama server is running and accessible."""
        if not self._client:
            raise OllamaConnectionError("Client not initialized. Use async context manager.")
        
        try:
            response = await self._client.get(f"{self.base_url}/api/tags")
            return response.status_code == 200
        except httpx.RequestError:
            return False
    
    def _check_server_health_sync(self) -> bool:
        """Check if Ollama server is running and accessible (synchronous)."""
        try:
            with self._get_sync_client() as client:
                response = client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except httpx.RequestError:
            return False
    
    async def _check_model_availability(self) -> bool:
        """Check if the specified model is available."""
        if self._model_available is not None:
            return self._model_available
        
        if not self._client:
            raise OllamaConnectionError("Client not initialized. Use async context manager.")
        
        try:
            response = await self._client.get(f"{self.base_url}/api/tags")
            if response.status_code != 200:
                self._model_available = False
                return False
            
            data = response.json()
            models = data.get("models", [])
            available_models = [model.get("name", "").split(":")[0] for model in models]
            
            self._model_available = self.model in available_models
            return self._model_available
            
        except httpx.RequestError as e:
            raise OllamaConnectionError(f"Failed to check model availability: {e}")
        except (KeyError, json.JSONDecodeError) as e:
            raise OllamaAPIError(f"Invalid response format: {e}")
    
    def _check_model_availability_sync(self) -> bool:
        """Check if the specified model is available (synchronous)."""
        if self._model_available is not None:
            return self._model_available
        
        try:
            with self._get_sync_client() as client:
                response = client.get(f"{self.base_url}/api/tags")
                if response.status_code != 200:
                    self._model_available = False
                    return False
                
                data = response.json()
                models = data.get("models", [])
                available_models = [model.get("name", "").split(":")[0] for model in models]
                
                self._model_available = self.model in available_models
                return self._model_available
                
        except httpx.RequestError as e:
            raise OllamaConnectionError(f"Failed to check model availability: {e}")
        except (KeyError, json.JSONDecodeError) as e:
            raise OllamaAPIError(f"Invalid response format: {e}")
    
    async def _pull_model(self) -> bool:
        """Attempt to pull the model if it's not available."""
        if not self._client:
            raise OllamaConnectionError("Client not initialized. Use async context manager.")
        
        try:
            # Start model pull
            response = await self._client.post(
                f"{self.base_url}/api/pull",
                json={"name": self.model}
            )
            
            if response.status_code != 200:
                return False
            
            # Wait for pull to complete (this might take a while)
            # For now, we'll just return True and let the user handle model pulling manually
            return True
            
        except httpx.RequestError:
            return False
    
    async def _make_request(self, request: OllamaRequest) -> Dict[str, Any]:
        """Make async request to Ollama API with error handling and retries."""
        if not self._client:
            raise OllamaConnectionError("Client not initialized. Use async context manager.")
        
        # Check server health
        if not await self._check_server_health():
            raise OllamaConnectionError(
                f"Ollama server is not running at {self.base_url}. "
                "Please start Ollama server and ensure the model is available."
            )
        
        # Check model availability
        if not await self._check_model_availability():
            raise OllamaModelError(
                f"Model '{self.model}' is not available. "
                f"Please pull the model using: ollama pull {self.model}"
            )
        
        for attempt in range(self.max_retries):
            try:
                response = await self._client.post(
                    f"{self.base_url}/api/generate",
                    json=request.dict()
                )
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    raise OllamaModelError(f"Model '{self.model}' not found")
                else:
                    error_msg = f"API request failed with status {response.status_code}"
                    try:
                        error_data = response.json()
                        error_msg += f": {error_data.get('error', 'Unknown error')}"
                    except:
                        pass
                    
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    else:
                        raise OllamaAPIError(error_msg)
                        
            except httpx.TimeoutException:
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                else:
                    raise OllamaAPIError("Request timeout")
            except httpx.RequestError as e:
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                else:
                    raise OllamaAPIError(f"Request failed: {e}")
        
        raise OllamaAPIError("Max retries exceeded")
    
    def _make_request_sync(self, request: OllamaRequest) -> Dict[str, Any]:
        """Make synchronous request to Ollama API with error handling and retries."""
        # Check server health
        if not self._check_server_health_sync():
            raise OllamaConnectionError(
                f"Ollama server is not running at {self.base_url}. "
                "Please start Ollama server and ensure the model is available."
            )
        
        # Check model availability
        if not self._check_model_availability_sync():
            raise OllamaModelError(
                f"Model '{self.model}' is not available. "
                f"Please pull the model using: ollama pull {self.model}"
            )
        
        with self._get_sync_client() as client:
            for attempt in range(self.max_retries):
                try:
                    response = client.post(
                        f"{self.base_url}/api/generate",
                        json=request.dict()
                    )
                    
                    if response.status_code == 200:
                        return response.json()
                    elif response.status_code == 404:
                        raise OllamaModelError(f"Model '{self.model}' not found")
                    else:
                        error_msg = f"API request failed with status {response.status_code}"
                        try:
                            error_data = response.json()
                            error_msg += f": {error_data.get('error', 'Unknown error')}"
                        except:
                            pass
                        
                        if attempt < self.max_retries - 1:
                            time.sleep(2 ** attempt)  # Exponential backoff
                            continue
                        else:
                            raise OllamaAPIError(error_msg)
                            
                except httpx.TimeoutException:
                    if attempt < self.max_retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                    else:
                        raise OllamaAPIError("Request timeout")
                except httpx.RequestError as e:
                    if attempt < self.max_retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                    else:
                        raise OllamaAPIError(f"Request failed: {e}")
        
        raise OllamaAPIError("Max retries exceeded")
    
    def _extract_content_from_response(self, response: Dict[str, Any]) -> str:
        """Extract text content from Ollama API response."""
        try:
            content = response.get("response", "")
            if not content:
                raise OllamaAPIError("Empty response content")
            
            return content.strip()
            
        except (KeyError, TypeError) as e:
            raise OllamaAPIError(f"Invalid response format: {e}")
    
    async def generate_summary(
        self, 
        transcription: Transcription,
        episode_title: str = "",
        podcast_title: str = "",
        publication_date: str = ""
    ) -> str:
        """Generate episode summary using Ollama."""
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
            
            request = OllamaRequest(
                model=self.model,
                prompt=prompt,
                options={
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "num_predict": 2000
                }
            )
            
            response = await self._make_request(request)
            return self._extract_content_from_response(response)
            
        except TemplateError as e:
            raise OllamaAPIError(f"Template error: {e}")
        except Exception as e:
            raise OllamaAPIError(f"Failed to generate summary: {e}")
    
    def generate_summary_sync(
        self, 
        transcription: Transcription,
        episode_title: str = "",
        podcast_title: str = "",
        publication_date: str = ""
    ) -> str:
        """Generate episode summary using Ollama (synchronous)."""
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
            
            request = OllamaRequest(
                model=self.model,
                prompt=prompt,
                options={
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "num_predict": 2000
                }
            )
            
            response = self._make_request_sync(request)
            return self._extract_content_from_response(response)
            
        except TemplateError as e:
            raise OllamaAPIError(f"Template error: {e}")
        except Exception as e:
            raise OllamaAPIError(f"Failed to generate summary: {e}")
    
    async def extract_topics(
        self, 
        transcription: Transcription,
        episode_title: str = "",
        podcast_title: str = ""
    ) -> List[Topic]:
        """Extract topics from transcription using Ollama."""
        try:
            # Load and render topics template
            template_vars = {
                "episode_title": episode_title,
                "podcast_title": podcast_title,
                "transcription": transcription.text
            }
            
            prompt = self.template_manager.render_template("topics", **template_vars)
            
            request = OllamaRequest(
                model=self.model,
                prompt=prompt,
                options={
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "num_predict": 1500
                }
            )
            
            response = await self._make_request(request)
            content = self._extract_content_from_response(response)
            
            return self._parse_topics_from_content(content)
            
        except TemplateError as e:
            raise OllamaAPIError(f"Template error: {e}")
        except Exception as e:
            raise OllamaAPIError(f"Failed to extract topics: {e}")
    
    def extract_topics_sync(
        self, 
        transcription: Transcription,
        episode_title: str = "",
        podcast_title: str = ""
    ) -> List[Topic]:
        """Extract topics from transcription using Ollama (synchronous)."""
        try:
            # Load and render topics template
            template_vars = {
                "episode_title": episode_title,
                "podcast_title": podcast_title,
                "transcription": transcription.text
            }
            
            prompt = self.template_manager.render_template("topics", **template_vars)
            
            request = OllamaRequest(
                model=self.model,
                prompt=prompt,
                options={
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "num_predict": 1500
                }
            )
            
            response = self._make_request_sync(request)
            content = self._extract_content_from_response(response)
            
            return self._parse_topics_from_content(content)
            
        except TemplateError as e:
            raise OllamaAPIError(f"Template error: {e}")
        except Exception as e:
            raise OllamaAPIError(f"Failed to extract topics: {e}")
    
    async def extract_keywords(
        self, 
        transcription: Transcription,
        episode_title: str = "",
        podcast_title: str = ""
    ) -> List[str]:
        """Extract keywords from transcription using Ollama."""
        try:
            # Load and render keywords template
            template_vars = {
                "episode_title": episode_title,
                "podcast_title": podcast_title,
                "transcription": transcription.text
            }
            
            prompt = self.template_manager.render_template("keywords", **template_vars)
            
            request = OllamaRequest(
                model=self.model,
                prompt=prompt,
                options={
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "num_predict": 800
                }
            )
            
            response = await self._make_request(request)
            content = self._extract_content_from_response(response)
            
            return self._parse_keywords_from_content(content)
            
        except TemplateError as e:
            raise OllamaAPIError(f"Template error: {e}")
        except Exception as e:
            raise OllamaAPIError(f"Failed to extract keywords: {e}")
    
    def extract_keywords_sync(
        self, 
        transcription: Transcription,
        episode_title: str = "",
        podcast_title: str = ""
    ) -> List[str]:
        """Extract keywords from transcription using Ollama (synchronous)."""
        try:
            # Load and render keywords template
            template_vars = {
                "episode_title": episode_title,
                "podcast_title": podcast_title,
                "transcription": transcription.text
            }
            
            prompt = self.template_manager.render_template("keywords", **template_vars)
            
            request = OllamaRequest(
                model=self.model,
                prompt=prompt,
                options={
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "num_predict": 800
                }
            )
            
            response = self._make_request_sync(request)
            content = self._extract_content_from_response(response)
            
            return self._parse_keywords_from_content(content)
            
        except TemplateError as e:
            raise OllamaAPIError(f"Template error: {e}")
        except Exception as e:
            raise OllamaAPIError(f"Failed to extract keywords: {e}")
    
    async def analyze_content(
        self,
        transcription: Transcription,
        episode_title: str = "",
        podcast_title: str = "",
        publication_date: str = ""
    ) -> AnalysisResult:
        """Perform complete content analysis using Ollama."""
        start_time = time.time()
        
        try:
            # Run analysis tasks sequentially for local models to avoid overload
            summary = await self.generate_summary(
                transcription, episode_title, podcast_title, publication_date
            )
            topics = await self.extract_topics(transcription, episode_title, podcast_title)
            keywords = await self.extract_keywords(transcription, episode_title, podcast_title)
            
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
                analysis_provider="ollama",
                analysis_model=self.model,
                processing_time=processing_time
            )
            
        except Exception as e:
            raise OllamaAPIError(f"Content analysis failed: {e}")
    
    def analyze_content_sync(
        self,
        transcription: Transcription,
        episode_title: str = "",
        podcast_title: str = "",
        publication_date: str = ""
    ) -> AnalysisResult:
        """Perform complete content analysis using Ollama (synchronous)."""
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
                analysis_provider="ollama",
                analysis_model=self.model,
                processing_time=processing_time
            )
            
        except Exception as e:
            raise OllamaAPIError(f"Content analysis failed: {e}")
    
    def _parse_topics_from_content(self, content: str) -> List[Topic]:
        """Parse topics from Ollama response content."""
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
        
        # Another fallback: simple numbered list without bold
        if not topics:
            pattern = r'^\d+\.\s*([^:]+):\s*(.+)$'
            for line in content.split('\n'):
                line = line.strip()
                match = re.match(pattern, line)
                if match:
                    name = match.group(1).strip()
                    description = match.group(2).strip()
                    topics.append(Topic(name=name, description=description))
        
        return topics
    
    def _parse_keywords_from_content(self, content: str) -> List[str]:
        """Parse keywords from Ollama response content."""
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
    
    async def is_available(self) -> bool:
        """Check if Ollama service and model are available."""
        try:
            return await self._check_server_health() and await self._check_model_availability()
        except (OllamaConnectionError, OllamaModelError):
            return False
    
    def is_available_sync(self) -> bool:
        """Check if Ollama service and model are available (synchronous)."""
        try:
            return self._check_server_health_sync() and self._check_model_availability_sync()
        except (OllamaConnectionError, OllamaModelError):
            return False