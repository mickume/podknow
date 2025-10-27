"""
Standardized error handling for CLI commands.

This module provides a decorator that applies consistent error handling
across all CLI commands, ensuring uniform error messages and exit codes.
"""

import click
import sys
from functools import wraps
from typing import Callable

from ..exceptions import (
    PodKnowError,
    NetworkError,
    AnalysisError,
    TranscriptionError,
    AudioProcessingError,
    LanguageDetectionError,
    ConfigurationError,
    RSSParsingError,
    EpisodeManagementError,
    FileOperationError
)


def handle_cli_errors(func: Callable) -> Callable:
    """
    Decorator that provides standardized error handling for CLI commands.

    This decorator catches and handles exceptions consistently across all CLI
    commands, providing appropriate error messages and exit codes.

    Features:
    - Catches KeyboardInterrupt and exits with code 130
    - Catches specific PodKnow exceptions with contextual messages
    - Catches generic exceptions with troubleshooting info
    - Shows full stack traces in verbose mode
    - Ensures proper exit codes for automation/CI/CD

    Usage:
        @cli.command()
        @click.pass_context
        @handle_cli_errors
        def my_command(ctx: click.Context, ...):
            # Command implementation
            pass

    Args:
        func: The CLI command function to wrap

    Returns:
        Wrapped function with error handling
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        # Extract context if present (usually first arg for CLI commands)
        ctx = None
        if args and isinstance(args[0], click.Context):
            ctx = args[0]

        try:
            return func(*args, **kwargs)

        except KeyboardInterrupt:
            # Handle KeyboardInterrupt with proper exit code
            click.echo("\nOperation cancelled by user.", err=True)
            sys.exit(130)

        except click.ClickException:
            # Click exceptions are already formatted, let them through
            raise

        except click.BadParameter as e:
            # Parameter validation errors - let Click handle them
            raise

        # Specific PodKnow exceptions with contextual help
        except LanguageDetectionError as e:
            _error_echo("Language detection failed", str(e))
            _show_troubleshooting([
                "Ensure the audio file is in a supported format",
                "Check that MLX-Whisper is properly installed",
                "Try using --skip-language-detection to bypass this step"
            ])
            _exit_with_verbose(ctx, e, 1)

        except AudioProcessingError as e:
            _error_echo("Audio processing failed", str(e))
            _show_troubleshooting([
                "Verify the audio file is not corrupted",
                "Ensure the audio file format is supported (MP3, WAV, M4A)",
                "Check available disk space"
            ])
            _exit_with_verbose(ctx, e, 1)

        except TranscriptionError as e:
            _error_echo("Transcription failed", str(e))
            _show_troubleshooting([
                "Check that MLX-Whisper is properly installed",
                "Ensure the audio file is complete and not corrupted",
                "Verify sufficient system resources are available"
            ])
            _exit_with_verbose(ctx, e, 1)

        except AnalysisError as e:
            _error_echo("Analysis failed", str(e))
            _show_troubleshooting([
                "Verify your Claude API key is correct",
                "Check that the API key has sufficient credits",
                "Ensure your internet connection is stable",
                "Try again in a few moments if rate limited"
            ])
            _exit_with_verbose(ctx, e, 1)

        except NetworkError as e:
            _error_echo("Network operation failed", str(e))
            _show_troubleshooting([
                "Check your internet connection",
                "Verify the URL is correct and accessible",
                "Try again in a few moments"
            ])
            _exit_with_verbose(ctx, e, 1)

        except ConfigurationError as e:
            _error_echo("Configuration error", str(e))
            _show_troubleshooting([
                "Run 'podknow setup' to create a default configuration",
                "Check ~/.podknow/config.md for syntax errors",
                "Ensure all required fields are filled in"
            ])
            _exit_with_verbose(ctx, e, 1)

        except FileOperationError as e:
            _error_echo("File operation failed", str(e))
            _show_troubleshooting([
                "Check file permissions",
                "Verify the file path exists",
                "Ensure sufficient disk space is available"
            ])
            _exit_with_verbose(ctx, e, 1)

        except PodKnowError as e:
            # Generic PodKnow error
            _error_echo("Operation failed", str(e))
            _exit_with_verbose(ctx, e, 1)

        except Exception as e:
            # Unexpected error
            _error_echo("An unexpected error occurred", str(e))
            _show_troubleshooting([
                "This may be a bug in PodKnow",
                "Try running with --verbose for more details",
                "Report this issue at: https://github.com/your-repo/podknow/issues"
            ])
            _exit_with_verbose(ctx, e, 1)

    return wrapper


def _error_echo(title: str, message: str = None):
    """Display error message in consistent format."""
    click.echo(f"[ERROR] {title}", err=True)
    if message:
        click.echo(f"  {message}", err=True)


def _show_troubleshooting(tips: list):
    """Display troubleshooting tips."""
    if tips:
        click.echo("\nTroubleshooting:", err=True)
        for tip in tips:
            click.echo(f"  • {tip}", err=True)


def _verbose_echo(ctx: click.Context, message: str):
    """Echo message only if verbose mode is enabled."""
    if ctx and ctx.obj.get('verbose', False):
        click.echo(f"[DEBUG] {message}", err=True)


def _exit_with_verbose(ctx: click.Context, exception: Exception, exit_code: int):
    """Exit with proper code, showing traceback if verbose."""
    if ctx and ctx.obj.get('verbose', False):
        click.echo("\n[DEBUG] Full traceback:", err=True)
        raise exception
    sys.exit(exit_code)
