# Project Structure & Architecture

## Directory Organization

```
podknow/
├── __init__.py              # Package initialization and version info
├── __main__.py              # Module entry point for python -m podknow
├── cli/                     # Command-line interface layer
│   ├── __init__.py
│   └── main.py             # Click-based CLI commands and entry point
├── models/                  # Data models and type definitions
│   ├── __init__.py         # Exports all model classes
│   ├── analysis.py         # AnalysisResult, SponsorSegment
│   ├── episode.py          # Episode, EpisodeMetadata
│   ├── output.py           # OutputDocument
│   ├── podcast.py          # PodcastResult, PodcastMetadata
│   └── transcription.py    # TranscriptionResult, TranscriptionSegment
├── services/                # Business logic services
│   ├── __init__.py         # Exports all service classes
│   ├── analysis.py         # Claude AI integration for content analysis
│   ├── config.py           # Configuration service (legacy)
│   ├── discovery.py        # iTunes/Spotify podcast search
│   ├── episode.py          # Episode management and listing
│   ├── rss.py              # RSS feed parsing
│   ├── transcription.py    # MLX-Whisper/OpenAI Whisper integration
│   └── workflow.py         # WorkflowOrchestrator for complex operations
├── config/                  # Configuration management
│   ├── __init__.py
│   ├── default_config.md   # Default configuration template
│   ├── manager.py          # ConfigManager class
│   └── models.py           # Configuration data models
├── utils/                   # Utility modules
│   ├── __init__.py
│   ├── cli_errors.py       # CLI error handling decorators
│   └── progress.py         # Progress bar utilities and context
├── constants.py             # Application constants
└── exceptions.py           # Custom exception hierarchy
```

## Architecture Patterns

### Layered Architecture
- **CLI Layer**: Click-based commands in `cli/main.py`
- **Service Layer**: Business logic in `services/` modules
- **Model Layer**: Pydantic data models in `models/` modules
- **Configuration Layer**: Markdown-based config in `config/` modules

### Service Pattern
Each service class handles a specific domain:
- `PodcastDiscoveryService`: iTunes/Spotify API integration
- `TranscriptionService`: Audio processing and MLX-Whisper integration
- `AnalysisService`: Claude AI content analysis
- `EpisodeListingService`: RSS feed parsing and episode management
- `WorkflowOrchestrator`: Coordinates complex multi-step operations with error recovery

### Orchestration Pattern
The `WorkflowOrchestrator` implements the orchestration pattern:
- Coordinates multiple services in complex workflows
- Manages workflow state and intermediate results
- Provides error recovery and resource cleanup
- Lazy-loads services for better performance
- Implements unified progress reporting across workflow steps

### Data Models
All data structures use Pydantic for validation and serialization:
- Type hints required for all fields
- Validation rules for external API data
- Consistent serialization to JSON/YAML

## File Naming Conventions

### Python Files
- **Snake case**: `episode_service.py`, `podcast_discovery.py`
- **Descriptive names**: Reflect the primary class or functionality
- **Service suffix**: Business logic classes end with `Service`

### Test Files
- **Prefix**: All test files start with `test_`
- **Mirror structure**: Test files mirror the source structure
- **Integration tests**: Use `test_*_integration.py` pattern

### Configuration Files
- **Markdown format**: `.md` extension for user-editable configs
- **YAML sections**: Embedded YAML blocks for structured data
- **Template suffix**: `default_config.md` for templates

## Import Patterns

### Module Imports
```python
# Preferred: Import specific classes
from ..models.episode import Episode, EpisodeMetadata
from ..services.transcription import TranscriptionService

# Avoid: Wildcard imports
from ..models import *  # Don't do this
```

### Relative Imports
- Use relative imports within the package: `from ..models import Episode`
- Use absolute imports for external packages: `import click`

## Error Handling

### Custom Exceptions
- Base class: `PodKnowError` in `exceptions.py`
- Domain-specific: `NetworkError`, `ConfigurationError`, `AnalysisError`
- Service-specific: `TranscriptionError`, `EpisodeManagementError`
- Processing errors: `AudioProcessingError`, `LanguageDetectionError`, `FileOperationError`

### Error Propagation
- Services raise domain-specific exceptions
- WorkflowOrchestrator catches errors, tracks state, and attempts recovery
- CLI layer catches and formats user-friendly messages with troubleshooting tips
- Utils module provides decorators for consistent error handling across CLI commands

## Configuration Management

### File Locations
- User config: `~/.podknow/config.md`
- Default template: `podknow/config/default_config.md`

### Structure
- Markdown format with embedded YAML blocks
- API keys in dedicated sections
- Customizable AI prompts as markdown sections
- Platform-specific settings handled automatically

## Testing Strategy

### Test Categories
- **Unit tests**: Individual service and model testing
- **Integration tests**: End-to-end workflow testing
- **Platform tests**: Apple Silicon vs standard platform testing
- **Installation tests**: Package installation verification

### Fixtures
- Platform mocking for cross-platform testing
- Temporary configuration directories
- Mock external API responses
- Clean import cache management