# Requirements Document

## Introduction

PodKnow is a command-line tool that enables users to discover, download, and transcribe podcast episodes from RSS feeds, with AI-powered analysis capabilities. The system leverages MLX-Whisper for Apple Silicon optimization and Claude AI for content analysis and processing.

## Glossary

- **PodKnow**: The command-line podcast transcription and analysis tool
- **MLX-Whisper**: Apple Silicon optimized speech-to-text transcription engine
- **Claude_API**: Anthropic's Claude AI API service for content analysis
- **RSS_Feed**: Really Simple Syndication feed containing podcast episode metadata
- **iTunes_API**: Apple's public API for podcast discovery
- **Spotify_API**: Spotify's public API for podcast discovery
- **Episode_Identifier**: Unique identifier for a specific podcast episode
- **Transcription_Engine**: The MLX-Whisper component that converts audio to text
- **Analysis_Engine**: The Claude AI component that processes transcriptions
- **Metadata_File**: Local markdown configuration file for LLM prompts and API settings

## Requirements

### Requirement 1

**User Story:** As a podcast researcher, I want to discover podcasts by searching across multiple platforms, so that I can find relevant content for transcription and analysis.

#### Acceptance Criteria

1. WHEN a user provides search keywords, THE PodKnow SHALL query the iTunes_API for matching podcasts
2. WHEN a user provides search keywords, THE PodKnow SHALL query the Spotify_API for matching podcasts
3. WHEN search results are returned, THE PodKnow SHALL display podcast titles, authors, and RSS_Feed URLs
4. WHERE search parameters include title keywords, THE PodKnow SHALL match against podcast titles
5. WHERE search parameters include author names, THE PodKnow SHALL match against podcast creators

### Requirement 2

**User Story:** As a content analyst, I want to list recent episodes from a podcast feed, so that I can select specific episodes for transcription.

#### Acceptance Criteria

1. WHEN a user provides an RSS_Feed URL, THE PodKnow SHALL parse the feed and extract episode metadata
2. WHEN episode listing is requested, THE PodKnow SHALL display the last n episodes with Episode_Identifiers
3. THE PodKnow SHALL display episode titles, publication dates, and durations for each episode
4. WHERE a user specifies episode count, THE PodKnow SHALL limit results to that number
5. THE PodKnow SHALL assign unique Episode_Identifiers for subsequent processing commands

### Requirement 3

**User Story:** As a researcher, I want to download and transcribe English podcast episodes, so that I can analyze the spoken content in text format.

#### Acceptance Criteria

1. WHEN a user specifies an Episode_Identifier, THE PodKnow SHALL download the corresponding audio file
2. WHEN audio language is detected as English, THE Transcription_Engine SHALL process the file using MLX-Whisper
3. IF audio language is not English, THEN THE PodKnow SHALL reject the transcription request with an error message
4. WHEN transcription is complete, THE Transcription_Engine SHALL detect paragraph boundaries using Whisper's built-in functionality
5. THE PodKnow SHALL generate a markdown file containing episode metadata as frontmatter and formatted transcription text

### Requirement 4

**User Story:** As a content curator, I want AI-powered analysis of transcriptions, so that I can quickly understand episode content and identify key information.

#### Acceptance Criteria

1. WHEN transcription is complete, THE Analysis_Engine SHALL generate a content summary using Claude_API
2. WHEN analysis is requested, THE Analysis_Engine SHALL extract a list of topics covered in single sentences
3. WHEN content processing occurs, THE Analysis_Engine SHALL identify relevant keywords for content labeling
4. WHEN sponsor content is detected, THE Analysis_Engine SHALL mark sponsored segments within the transcription, or discard it with a note
5. THE PodKnow SHALL incorporate all analysis results into the final markdown output file

### Requirement 5

**User Story:** As a system administrator, I want a properly configured Python environment, so that the tool runs reliably with all dependencies.

#### Acceptance Criteria

1. THE PodKnow SHALL operate using Python 3.13 runtime environment
2. WHEN installation occurs, THE PodKnow SHALL create a dedicated virtual environment for dependency isolation
3. THE PodKnow SHALL support installation via pip package manager
4. THE PodKnow SHALL support installation via uv package manager
5. WHERE MLX-Whisper is required, THE PodKnow SHALL install Apple Silicon optimized dependencies

### Requirement 6

**User Story:** As a power user, I want configurable AI prompts and API settings, so that I can customize analysis behavior without modifying code.

#### Acceptance Criteria

1. THE PodKnow SHALL read LLM prompts and directives from a local Metadata_File
2. WHEN API configuration changes, THE PodKnow SHALL load updated settings from the Metadata_File without code modification
3. THE Metadata_File SHALL be formatted as markdown for easy editing
4. WHEN Claude_API calls are made, THE Analysis_Engine SHALL use prompts defined in the Metadata_File
5. THE PodKnow SHALL validate Metadata_File format and provide clear error messages for invalid configurations