"""Template management system for LLM prompts with Jinja2 support."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from jinja2 import Environment, FileSystemLoader, Template, TemplateError, TemplateSyntaxError


class AnalysisTemplate:
    """Represents a single analysis template with metadata."""
    
    def __init__(self, name: str, content: str, template_path: Path):
        """Initialize template with name, content, and source path."""
        self.name = name
        self.content = content
        self.template_path = template_path
        self._jinja_template: Optional[Template] = None
    
    def render(self, **kwargs) -> str:
        """Render template with provided variables."""
        if self._jinja_template is None:
            env = Environment(
                trim_blocks=True,
                lstrip_blocks=True,
                keep_trailing_newline=True
            )
            try:
                self._jinja_template = env.from_string(self.content)
            except TemplateSyntaxError as e:
                raise TemplateValidationError(
                    f"Template syntax error in {self.name}: {e}"
                )
        
        try:
            return self._jinja_template.render(**kwargs)
        except TemplateError as e:
            raise TemplateRenderError(
                f"Failed to render template {self.name}: {e}"
            )
    
    def get_required_variables(self) -> List[str]:
        """Extract required template variables from Jinja2 template."""
        if self._jinja_template is None:
            env = Environment()
            try:
                self._jinja_template = env.from_string(self.content)
            except TemplateSyntaxError as e:
                raise TemplateValidationError(
                    f"Template syntax error in {self.name}: {e}"
                )
        
        # Get undeclared variables (required variables) using meta module
        from jinja2.meta import find_undeclared_variables
        ast = self._jinja_template.environment.parse(self.content)
        return list(find_undeclared_variables(ast))


class TemplateManager:
    """Manages loading, parsing, and rendering of markdown template files."""
    
    def __init__(self, template_directory: Optional[Path] = None):
        """Initialize TemplateManager with template directory path."""
        self.template_directory = template_directory or Path.home() / ".podknow" / "templates"
        self._templates: Dict[str, AnalysisTemplate] = {}
        self._jinja_env: Optional[Environment] = None
    
    def load_templates(self) -> Dict[str, AnalysisTemplate]:
        """Load all template files from the template directory."""
        if not self.template_directory.exists():
            self._create_default_templates()
        
        self._templates.clear()
        
        try:
            # Set up Jinja2 environment
            self._jinja_env = Environment(
                loader=FileSystemLoader(str(self.template_directory)),
                trim_blocks=True,
                lstrip_blocks=True,
                keep_trailing_newline=True
            )
            
            # Load all .md files as templates
            for template_file in self.template_directory.glob("*.md"):
                try:
                    with open(template_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    template_name = template_file.stem
                    template = AnalysisTemplate(template_name, content, template_file)
                    
                    # Validate template syntax
                    template.get_required_variables()  # This will raise if invalid
                    
                    self._templates[template_name] = template
                    
                except (OSError, UnicodeDecodeError) as e:
                    raise TemplateLoadError(
                        f"Failed to read template file {template_file}: {e}"
                    )
                except TemplateValidationError:
                    # Re-raise template validation errors
                    raise
                except Exception as e:
                    raise TemplateLoadError(
                        f"Unexpected error loading template {template_file}: {e}"
                    )
            
            if not self._templates:
                raise TemplateLoadError(
                    f"No valid template files found in {self.template_directory}"
                )
            
            return self._templates
            
        except Exception as e:
            if isinstance(e, (TemplateLoadError, TemplateValidationError)):
                raise
            raise TemplateLoadError(
                f"Failed to load templates from {self.template_directory}: {e}"
            )
    
    def get_template(self, name: str) -> AnalysisTemplate:
        """Get a specific template by name."""
        if not self._templates:
            self.load_templates()
        
        if name not in self._templates:
            available = ", ".join(self._templates.keys())
            raise TemplateNotFoundError(
                f"Template '{name}' not found. Available templates: {available}"
            )
        
        return self._templates[name]
    
    def render_template(self, name: str, **kwargs) -> str:
        """Render a template with provided variables."""
        template = self.get_template(name)
        return template.render(**kwargs)
    
    def list_templates(self) -> List[str]:
        """List all available template names."""
        if not self._templates:
            self.load_templates()
        return list(self._templates.keys())
    
    def validate_template(self, name: str) -> bool:
        """Validate a template's syntax and return True if valid."""
        try:
            template = self.get_template(name)
            template.get_required_variables()  # This validates syntax
            return True
        except (TemplateNotFoundError, TemplateValidationError):
            return False
    
    def reload_templates(self) -> Dict[str, AnalysisTemplate]:
        """Reload all templates from disk, discarding cached versions."""
        self._templates.clear()
        return self.load_templates()
    
    def _create_default_templates(self) -> None:
        """Create default template files if template directory doesn't exist."""
        self.template_directory.mkdir(parents=True, exist_ok=True)
        
        # Default summary template
        summary_template = """# Episode Summary Template

You are analyzing a podcast episode transcript. Generate a comprehensive summary following these guidelines:

## Instructions
- Create a 2-3 paragraph summary of the main content
- Focus on key insights, arguments, and conclusions
- Maintain the original tone and perspective
- Highlight actionable takeaways if present

## Episode Information
- **Title**: {{ episode_title }}
- **Podcast**: {{ podcast_title }}
- **Duration**: {{ duration }} minutes
- **Date**: {{ publication_date }}

## Transcript
{{ transcription }}

## Summary
[Provide your summary here]
"""
        
        # Default topics template
        topics_template = """# Topic Extraction Template

Extract the main topics discussed in this podcast episode transcript.

## Instructions
- Identify 5-8 main topics covered in the episode
- For each topic, provide a one-sentence description
- Focus on substantial topics, not brief mentions
- Order topics by prominence in the discussion

## Episode Information
- **Title**: {{ episode_title }}
- **Podcast**: {{ podcast_title }}

## Transcript
{{ transcription }}

## Topics
[List topics in this format:]
1. **Topic Name**: One-sentence description of what was discussed about this topic.
"""
        
        # Default keywords template
        keywords_template = """# Keyword Extraction Template

Extract relevant keywords and key phrases from this podcast episode transcript.

## Instructions
- Identify 10-15 important keywords and phrases
- Include proper nouns (people, companies, products, places)
- Include technical terms and industry jargon
- Include key concepts and themes
- Avoid common words and filler terms

## Episode Information
- **Title**: {{ episode_title }}
- **Podcast**: {{ podcast_title }}

## Transcript
{{ transcription }}

## Keywords
[List keywords separated by commas]
"""
        
        # Write default templates
        templates = {
            "summary": summary_template,
            "topics": topics_template,
            "keywords": keywords_template
        }
        
        for name, content in templates.items():
            template_path = self.template_directory / f"{name}.md"
            with open(template_path, 'w', encoding='utf-8') as f:
                f.write(content.strip() + '\n')


class TemplateError(Exception):
    """Base exception for template-related errors."""
    pass


class TemplateLoadError(TemplateError):
    """Raised when template files cannot be loaded."""
    pass


class TemplateNotFoundError(TemplateError):
    """Raised when a requested template is not found."""
    pass


class TemplateValidationError(TemplateError):
    """Raised when template syntax is invalid."""
    pass


class TemplateRenderError(TemplateError):
    """Raised when template rendering fails."""
    pass