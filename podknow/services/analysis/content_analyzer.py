"""Content analysis orchestrator that manages AI provider selection and fallback logic."""

import asyncio
import time
from typing import Optional, Union, Dict, Any
from enum import Enum

from ...models.analysis import AnalysisResult
from ...models.transcription import Transcription
from ...config.config_manager import ConfigManager, PodKnowConfig
from ...config.template_manager import TemplateManager
from ...exceptions import PodKnowError
from .claude_analyzer import ClaudeAnalyzer, ClaudeAPIError, ClaudeRateLimitError
from .ollama_analyzer import OllamaAnalyzer, OllamaConnectionError, OllamaModelError, OllamaAPIError


class AnalysisProvider(Enum):
    """Available AI analysis providers."""
    CLAUDE = "claude"
    OLLAMA = "ollama"


class ContentAnalysisError(PodKnowError):
    """Raised when content analysis fails across all providers."""
    pass


class ContentAnalyzer:
    """Orchestrates AI-powered content analysis with provider selection and fallback logic."""
    
    def __init__(
        self,
        config: Optional[PodKnowConfig] = None,
        config_manager: Optional[ConfigManager] = None,
        template_manager: Optional[TemplateManager] = None
    ):
        """Initialize ContentAnalyzer with configuration and template management."""
        self.config_manager = config_manager or ConfigManager()
        self.config = config or self.config_manager.get_config()
        self.template_manager = template_manager or TemplateManager(
            template_directory=self.config.storage.template_directory
        )
        
        # Initialize analyzers
        self._claude_analyzer: Optional[ClaudeAnalyzer] = None
        self._ollama_analyzer: Optional[OllamaAnalyzer] = None
        
        # Load templates
        try:
            self.template_manager.load_templates()
        except Exception as e:
            raise ContentAnalysisError(f"Failed to load analysis templates: {e}")
    
    def _get_claude_analyzer(self) -> Optional[ClaudeAnalyzer]:
        """Get or create Claude analyzer if configured."""
        if self._claude_analyzer is not None:
            return self._claude_analyzer
        
        claude_config = self.config.ai_analysis.claude
        api_key = claude_config.get("api_key")
        
        if not api_key:
            return None
        
        model = claude_config.get("model", "claude-3-sonnet-20240229")
        
        self._claude_analyzer = ClaudeAnalyzer(
            api_key=api_key,
            model=model,
            template_manager=self.template_manager
        )
        
        return self._claude_analyzer
    
    def _get_ollama_analyzer(self) -> Optional[OllamaAnalyzer]:
        """Get or create Ollama analyzer if configured."""
        if self._ollama_analyzer is not None:
            return self._ollama_analyzer
        
        ollama_config = self.config.ai_analysis.ollama
        base_url = ollama_config.get("base_url", "http://localhost:11434")
        model = ollama_config.get("model", "llama2")
        
        self._ollama_analyzer = OllamaAnalyzer(
            model=model,
            base_url=base_url,
            template_manager=self.template_manager
        )
        
        return self._ollama_analyzer
    
    def get_primary_provider(self) -> AnalysisProvider:
        """Get the configured primary analysis provider."""
        primary = self.config.ai_analysis.primary_provider.lower()
        
        if primary == "claude":
            return AnalysisProvider.CLAUDE
        elif primary == "ollama":
            return AnalysisProvider.OLLAMA
        else:
            # Default to Claude if configured, otherwise Ollama
            if self._get_claude_analyzer() is not None:
                return AnalysisProvider.CLAUDE
            else:
                return AnalysisProvider.OLLAMA
    
    def get_fallback_provider(self) -> Optional[AnalysisProvider]:
        """Get the fallback analysis provider."""
        primary = self.get_primary_provider()
        
        if primary == AnalysisProvider.CLAUDE:
            # Fallback to Ollama if available
            if self._get_ollama_analyzer() is not None:
                return AnalysisProvider.OLLAMA
        elif primary == AnalysisProvider.OLLAMA:
            # Fallback to Claude if available
            if self._get_claude_analyzer() is not None:
                return AnalysisProvider.CLAUDE
        
        return None
    
    async def _analyze_with_provider(
        self,
        provider: AnalysisProvider,
        transcription: Transcription,
        episode_title: str = "",
        podcast_title: str = "",
        publication_date: str = ""
    ) -> AnalysisResult:
        """Perform analysis with a specific provider."""
        if provider == AnalysisProvider.CLAUDE:
            analyzer = self._get_claude_analyzer()
            if analyzer is None:
                raise ContentAnalysisError("Claude analyzer not configured")
            
            async with analyzer:
                return await analyzer.analyze_content(
                    transcription, episode_title, podcast_title, publication_date
                )
        
        elif provider == AnalysisProvider.OLLAMA:
            analyzer = self._get_ollama_analyzer()
            if analyzer is None:
                raise ContentAnalysisError("Ollama analyzer not configured")
            
            async with analyzer:
                return await analyzer.analyze_content(
                    transcription, episode_title, podcast_title, publication_date
                )
        
        else:
            raise ContentAnalysisError(f"Unknown provider: {provider}")
    
    def _analyze_with_provider_sync(
        self,
        provider: AnalysisProvider,
        transcription: Transcription,
        episode_title: str = "",
        podcast_title: str = "",
        publication_date: str = ""
    ) -> AnalysisResult:
        """Perform analysis with a specific provider (synchronous)."""
        if provider == AnalysisProvider.CLAUDE:
            analyzer = self._get_claude_analyzer()
            if analyzer is None:
                raise ContentAnalysisError("Claude analyzer not configured")
            
            return analyzer.analyze_content_sync(
                transcription, episode_title, podcast_title, publication_date
            )
        
        elif provider == AnalysisProvider.OLLAMA:
            analyzer = self._get_ollama_analyzer()
            if analyzer is None:
                raise ContentAnalysisError("Ollama analyzer not configured")
            
            return analyzer.analyze_content_sync(
                transcription, episode_title, podcast_title, publication_date
            )
        
        else:
            raise ContentAnalysisError(f"Unknown provider: {provider}")
    
    async def analyze_content(
        self,
        transcription: Transcription,
        episode_title: str = "",
        podcast_title: str = "",
        publication_date: str = "",
        preferred_provider: Optional[AnalysisProvider] = None
    ) -> AnalysisResult:
        """
        Perform complete content analysis with automatic provider selection and fallback.
        
        Args:
            transcription: The transcription to analyze
            episode_title: Episode title for context
            podcast_title: Podcast title for context
            publication_date: Publication date for context
            preferred_provider: Override the configured primary provider
            
        Returns:
            AnalysisResult with summary, topics, keywords, and metadata
            
        Raises:
            ContentAnalysisError: If analysis fails with all available providers
        """
        # Determine provider order
        primary_provider = preferred_provider or self.get_primary_provider()
        fallback_provider = self.get_fallback_provider()
        
        providers_to_try = [primary_provider]
        if fallback_provider and fallback_provider != primary_provider:
            providers_to_try.append(fallback_provider)
        
        last_error = None
        
        for provider in providers_to_try:
            try:
                result = await self._analyze_with_provider(
                    provider, transcription, episode_title, podcast_title, publication_date
                )
                
                # Add provider selection metadata
                result.metadata.update({
                    "provider_used": provider.value,
                    "primary_provider": primary_provider.value,
                    "fallback_used": provider != primary_provider
                })
                
                return result
                
            except (ClaudeRateLimitError, ClaudeAPIError) as e:
                last_error = e
                if provider == AnalysisProvider.CLAUDE:
                    # Claude-specific errors, try fallback
                    continue
                else:
                    # This shouldn't happen, but handle it
                    raise ContentAnalysisError(f"Unexpected Claude error with {provider}: {e}")
            
            except (OllamaConnectionError, OllamaModelError, OllamaAPIError) as e:
                last_error = e
                if provider == AnalysisProvider.OLLAMA:
                    # Ollama-specific errors, try fallback
                    continue
                else:
                    # This shouldn't happen, but handle it
                    raise ContentAnalysisError(f"Unexpected Ollama error with {provider}: {e}")
            
            except ContentAnalysisError:
                # Re-raise content analysis errors
                raise
            
            except Exception as e:
                last_error = e
                # Unexpected error, try fallback
                continue
        
        # All providers failed
        provider_names = [p.value for p in providers_to_try]
        raise ContentAnalysisError(
            f"Content analysis failed with all available providers ({', '.join(provider_names)}). "
            f"Last error: {last_error}"
        )
    
    def analyze_content_sync(
        self,
        transcription: Transcription,
        episode_title: str = "",
        podcast_title: str = "",
        publication_date: str = "",
        preferred_provider: Optional[AnalysisProvider] = None
    ) -> AnalysisResult:
        """
        Perform complete content analysis with automatic provider selection and fallback (synchronous).
        
        Args:
            transcription: The transcription to analyze
            episode_title: Episode title for context
            podcast_title: Podcast title for context
            publication_date: Publication date for context
            preferred_provider: Override the configured primary provider
            
        Returns:
            AnalysisResult with summary, topics, keywords, and metadata
            
        Raises:
            ContentAnalysisError: If analysis fails with all available providers
        """
        # Determine provider order
        primary_provider = preferred_provider or self.get_primary_provider()
        fallback_provider = self.get_fallback_provider()
        
        providers_to_try = [primary_provider]
        if fallback_provider and fallback_provider != primary_provider:
            providers_to_try.append(fallback_provider)
        
        last_error = None
        
        for provider in providers_to_try:
            try:
                result = self._analyze_with_provider_sync(
                    provider, transcription, episode_title, podcast_title, publication_date
                )
                
                # Add provider selection metadata
                result.metadata.update({
                    "provider_used": provider.value,
                    "primary_provider": primary_provider.value,
                    "fallback_used": provider != primary_provider
                })
                
                return result
                
            except (ClaudeRateLimitError, ClaudeAPIError) as e:
                last_error = e
                if provider == AnalysisProvider.CLAUDE:
                    # Claude-specific errors, try fallback
                    continue
                else:
                    # This shouldn't happen, but handle it
                    raise ContentAnalysisError(f"Unexpected Claude error with {provider}: {e}")
            
            except (OllamaConnectionError, OllamaModelError, OllamaAPIError) as e:
                last_error = e
                if provider == AnalysisProvider.OLLAMA:
                    # Ollama-specific errors, try fallback
                    continue
                else:
                    # This shouldn't happen, but handle it
                    raise ContentAnalysisError(f"Unexpected Ollama error with {provider}: {e}")
            
            except ContentAnalysisError:
                # Re-raise content analysis errors
                raise
            
            except Exception as e:
                last_error = e
                # Unexpected error, try fallback
                continue
        
        # All providers failed
        provider_names = [p.value for p in providers_to_try]
        raise ContentAnalysisError(
            f"Content analysis failed with all available providers ({', '.join(provider_names)}). "
            f"Last error: {last_error}"
        )
    
    async def check_provider_availability(self) -> Dict[str, bool]:
        """Check availability of all configured providers."""
        availability = {}
        
        # Check Claude
        claude_analyzer = self._get_claude_analyzer()
        if claude_analyzer:
            try:
                # Simple test to check if API key works
                async with claude_analyzer:
                    # We can't easily test Claude without making a request,
                    # so we'll assume it's available if configured
                    availability["claude"] = True
            except Exception:
                availability["claude"] = False
        else:
            availability["claude"] = False
        
        # Check Ollama
        ollama_analyzer = self._get_ollama_analyzer()
        if ollama_analyzer:
            try:
                async with ollama_analyzer:
                    availability["ollama"] = await ollama_analyzer.is_available()
            except Exception:
                availability["ollama"] = False
        else:
            availability["ollama"] = False
        
        return availability
    
    def check_provider_availability_sync(self) -> Dict[str, bool]:
        """Check availability of all configured providers (synchronous)."""
        availability = {}
        
        # Check Claude
        claude_analyzer = self._get_claude_analyzer()
        if claude_analyzer:
            # We can't easily test Claude without making a request,
            # so we'll assume it's available if configured
            availability["claude"] = True
        else:
            availability["claude"] = False
        
        # Check Ollama
        ollama_analyzer = self._get_ollama_analyzer()
        if ollama_analyzer:
            try:
                availability["ollama"] = ollama_analyzer.is_available_sync()
            except Exception:
                availability["ollama"] = False
        else:
            availability["ollama"] = False
        
        return availability
    
    def reload_config(self) -> None:
        """Reload configuration and reinitialize analyzers."""
        self.config = self.config_manager.reload_config()
        
        # Reset analyzers to force recreation with new config
        self._claude_analyzer = None
        self._ollama_analyzer = None
        
        # Reload templates
        self.template_manager.reload_templates()
    
    def get_analysis_info(self) -> Dict[str, Any]:
        """Get information about the current analysis configuration."""
        primary_provider = self.get_primary_provider()
        fallback_provider = self.get_fallback_provider()
        
        info = {
            "primary_provider": primary_provider.value,
            "fallback_provider": fallback_provider.value if fallback_provider else None,
            "claude_configured": self._get_claude_analyzer() is not None,
            "ollama_configured": self._get_ollama_analyzer() is not None,
            "templates_loaded": len(self.template_manager.list_templates()),
            "template_directory": str(self.template_manager.template_directory)
        }
        
        # Add provider-specific info
        if self._get_claude_analyzer():
            info["claude_model"] = self.config.ai_analysis.claude.get("model", "claude-3-sonnet")
        
        if self._get_ollama_analyzer():
            ollama_config = self.config.ai_analysis.ollama
            info["ollama_model"] = ollama_config.get("model", "llama2")
            info["ollama_base_url"] = ollama_config.get("base_url", "http://localhost:11434")
        
        return info