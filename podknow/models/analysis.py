"""AI analysis-related data models."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class Topic(BaseModel):
    """Represents a topic extracted from episode content."""
    
    name: str = Field(..., description="Topic name or title")
    description: str = Field(..., description="One-sentence topic description")
    relevance_score: Optional[float] = Field(
        None, 
        description="Topic relevance score (0-1)",
        ge=0.0,
        le=1.0
    )
    timestamps: List[float] = Field(
        default_factory=list,
        description="Timestamps where topic is discussed"
    )


class AnalysisResult(BaseModel):
    """Represents the result of AI-powered content analysis."""
    
    summary: str = Field(..., description="Episode summary")
    topics: List[Topic] = Field(
        default_factory=list,
        description="Extracted topics with descriptions"
    )
    keywords: List[str] = Field(
        default_factory=list,
        description="Relevant keywords from episode content"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional analysis metadata"
    )
    analysis_provider: str = Field(..., description="AI provider used for analysis")
    analysis_model: Optional[str] = Field(None, description="Specific model used")
    processing_time: float = Field(..., description="Analysis processing time in seconds")
    
    @property
    def topic_count(self) -> int:
        """Get the number of topics identified."""
        return len(self.topics)
    
    @property
    def keyword_count(self) -> int:
        """Get the number of keywords identified."""
        return len(self.keywords)
    
    def get_top_topics(self, limit: int = 5) -> List[Topic]:
        """Get top topics by relevance score."""
        if not self.topics:
            return []
        
        # Sort by relevance score if available, otherwise return first N
        if all(topic.relevance_score is not None for topic in self.topics):
            sorted_topics = sorted(
                self.topics, 
                key=lambda t: t.relevance_score or 0.0, 
                reverse=True
            )
        else:
            sorted_topics = self.topics
            
        return sorted_topics[:limit]