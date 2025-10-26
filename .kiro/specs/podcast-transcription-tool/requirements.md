# Requirements Document

## Introduction

PodKnow is a command-line podcast management and transcription tool that enables users to discover, subscribe to, and transcribe podcast episodes. The system integrates with podcast directories, downloads audio content, transcribes using MLX-Whisper (optimized for Apple Silicon), and generates enhanced markdown files with episode metadata, transcriptions, and AI-powered analysis.

## Glossary

- **PodKnow**: The command-line podcast transcription tool system
- **Podcast_Directory**: Public podcast discovery endpoints (iTunes Search API, Spotify Web API public endpoints)
- **RSS_Feed**: XML feed containing podcast episode metadata and media URLs
- **MLX_Whisper**: Apple Silicon-optimized speech-to-text transcription engine
- **Subscription_Manager**: Local component managing subscribed podcast feeds
- **Episode_Processor**: Component handling audio download and transcription
- **Content_Analyzer**: AI-powered component for generating summaries and analysis
- **Metadata_Template**: Local markdown configuration file for LLM prompts

## Requirements

### Requirement 1

**User Story:** As a podcast enthusiast, I want to search for podcasts by title, author, or keywords, so that I can discover relevant content to subscribe to.

#### Acceptance Criteria

1. WHEN a user provides search terms, THE Podcast_Directory SHALL return matching podcast results with metadata
2. THE PodKnow SHALL display search results including podcast title, author, and description
3. THE PodKnow SHALL support search queries containing multiple keywords
4. THE PodKnow SHALL integrate with public iTunes Search API and Spotify Web API endpoints without requiring API keys
5. WHERE search results exceed ten items, THE PodKnow SHALL paginate results

### Requirement 2

**User Story:** As a user, I want to subscribe to podcasts locally, so that I can track and manage my podcast feeds without relying on external services.

#### Acceptance Criteria

1. WHEN a user selects a podcast from search results, THE Subscription_Manager SHALL store the RSS feed URL locally
2. THE Subscription_Manager SHALL maintain a local file containing subscribed podcast metadata
3. THE PodKnow SHALL allow users to list all subscribed podcasts
4. THE PodKnow SHALL enable users to unsubscribe from podcasts
5. THE Subscription_Manager SHALL check for new episodes across all subscribed feeds

### Requirement 3

**User Story:** As a user, I want to download and transcribe English podcast episodes, so that I can access searchable text content from audio.

#### Acceptance Criteria

1. WHEN a new English episode is detected, THE Episode_Processor SHALL download the media file
2. THE Episode_Processor SHALL transcribe audio using MLX_Whisper engine
3. IF an episode language is not English, THEN THE Episode_Processor SHALL skip transcription
4. THE Episode_Processor SHALL support both audio and video media formats
5. THE PodKnow SHALL optimize transcription performance for Apple M-series processors

### Requirement 4

**User Story:** As a user, I want to generate structured markdown files with episode content, so that I can easily review and reference podcast information.

#### Acceptance Criteria

1. THE PodKnow SHALL create a markdown file containing episode metadata as frontmatter and original transcription
2. THE Content_Analyzer SHALL generate episode summaries using AI analysis
3. THE Content_Analyzer SHALL extract topic lists with one-sentence descriptions
4. THE Content_Analyzer SHALL identify relevant keywords from episode content
5. THE PodKnow SHALL create a second markdown file with enhanced analysis content

### Requirement 5

**User Story:** As a user, I want to configure AI analysis behavior through editable templates, so that I can customize output without modifying code.

#### Acceptance Criteria

1. THE PodKnow SHALL read LLM prompts and instructions from local Metadata_Template files
2. THE Metadata_Template SHALL be editable markdown files containing analysis directives
3. THE Content_Analyzer SHALL support both Claude API and local Ollama LLM options
4. THE PodKnow SHALL allow users to switch between AI providers through configuration
5. WHERE Metadata_Template files are modified, THE Content_Analyzer SHALL use updated instructions immediately

### Requirement 6

**User Story:** As a user, I want to run PodKnow as a command-line tool on Python 3.13, so that I can integrate it into my workflow and automation scripts.

#### Acceptance Criteria

1. THE PodKnow SHALL execute as a Python 3.13 command-line application
2. THE PodKnow SHALL provide clear command-line interface with help documentation
3. THE PodKnow SHALL support batch processing of multiple episodes
4. THE PodKnow SHALL provide progress indicators for long-running operations
5. THE PodKnow SHALL handle errors gracefully with informative error messages