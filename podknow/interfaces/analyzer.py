"""Abstract interface for content analysis services."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from ..models.analysis import AnalysisResult


class ContentAnalyzerInterface(ABC):
    """Abstract interface for AI-powered content analysis services."""
    
    @abstractmethod
    async def analyze_content(
        self, 
        transcription_text: str, 
        episode_metadata: Dict[str, Any],
        analysis_templates: Optional[Dict[str, str]] = None
    ) -> AnalysisResult:
        """
        Analyze transcribed content to extract insights.
        
        Args:
            transcription_text: The transcribed episode text
            episode_metadata: Episode metadata for context
            analysis_templates: Custom templates for analysis prompts
            
        Returns:
            Analysis results including summary, topics, and keywords
            
        Raises:
            AnalysisError: When content analysis fails
        """
        pass
    
    @abstractmethod
    async def generate_summary(self, transcription_text: str) -> str:
        """
        Generate a summary of the transcribed content.
        
        Args:
            transcription_text: The transcribed episode text
            
        Returns:
            Episode summary text
            
        Raises:
            AnalysisError: When summary generation fails
        """
        pass
    
    @abstractmethod
    async def extract_topics(self, transcription_text: str) -> List[Dict[str, Any]]:
        """
        Extract topics from the transcribed content.
        
        Args:
            transcription_text: The transcribed episode text
            
        Returns:
            List of topics with descriptions
            
        Raises:
            AnalysisError: When topic extraction fails
        """
        pass
    
    @abstractmethod
    async def identify_keywords(self, transcription_text: str) -> List[str]:
        """
        Identify relevant keywords from the transcribed content.
        
        Args:
            transcription_text: The transcribed episode text
            
        Returns:
            List of relevant keywords
            
        Raises:
            AnalysisError: When keyword identification fails
        """
        pass
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the name of the analysis provider."""
        pass
    
    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the analysis service is currently available."""
        pass
    
    @abstractmethod
    async def validate_connection(self) -> bool:
        """
        Validate connection to the analysis service.
        
        Returns:
            True if connection is valid, False otherwise
        """
        pass