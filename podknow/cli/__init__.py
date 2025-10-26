"""
Command-line interface for PodKnow application.

This module provides the Click-based CLI commands for podcast discovery,
episode listing, transcription, and analysis.
"""

from .main import cli

__all__ = ["cli"]