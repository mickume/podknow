"""
Main CLI interface for PodKnow application.
"""

import click
import sys
import os
from typing import Optional
from datetime import datetime

from ..exceptions import PodKnowError, NetworkError
from ..services.workflow import WorkflowOrchestrator


@click.group()
@click.version_option(version="0.1.0", prog_name="podknow")
@click.option(
    "--verbose", "-v", 
    is_flag=True, 
    help="Enable verbose output for debugging"
)
@click.option(
    "--log-file",
    type=click.Path(exists=False, dir_okay=False),
    help="Log file path for detailed logging"
)
@click.pass_context
def cli(ctx: click.Context, verbose: bool, log_file: Optional[str]):
    """
    PodKnow - Command-line podcast transcription and analysis tool.
    
    PodKnow helps you discover podcasts, download episodes, and generate 
    AI-powered transcriptions with content analysis. It's optimized for 
    Apple Silicon using MLX-Whisper and integrates with Claude AI for 
    intelligent content processing.
    
    Examples:
    
        # Search for podcasts
        podknow search "artificial intelligence"
        
        # List recent episodes from a podcast
        podknow list https://feeds.example.com/podcast.xml --count 5
        
        # Transcribe and analyze an episode
        podknow transcribe abc123def456
        
    For more help on specific commands, use: podknow COMMAND --help
    """
    # Ensure context object exists
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    ctx.obj['log_file'] = log_file
    
    # Initialize workflow orchestrator
    ctx.obj['workflow'] = WorkflowOrchestrator(
        verbose=verbose,
        log_file=log_file
    )
    
    # Set up error handling
    def handle_exception(exc_type, exc_value, exc_traceback):
        if isinstance(exc_value, PodKnowError):
            click.echo(f"Error: {exc_value}", err=True)
            sys.exit(1)
        elif isinstance(exc_value, KeyboardInterrupt):
            click.echo("\nOperation cancelled by user.", err=True)
            sys.exit(130)
        else:
            # Re-raise unexpected exceptions in verbose mode
            if verbose:
                sys.__excepthook__(exc_type, exc_value, exc_traceback)
            else:
                click.echo(f"Unexpected error: {exc_value}", err=True)
                click.echo("Use --verbose for detailed error information.", err=True)
                sys.exit(1)
    
    sys.excepthook = handle_exception


@cli.command()
@click.argument("keywords", required=True)
@click.option(
    "--platform", "-p",
    type=click.Choice(['itunes', 'spotify', 'all'], case_sensitive=False),
    default='all',
    help="Search platform (default: all)"
)
@click.option(
    "--limit", "-l",
    type=click.IntRange(1, 100),
    default=20,
    help="Maximum number of results to return (default: 20)"
)
@click.pass_context
def search(ctx: click.Context, keywords: str, platform: str, limit: int):
    """
    Search for podcasts by keywords across multiple platforms.
    
    KEYWORDS can be podcast titles, author names, or topic keywords.
    Results include podcast titles, authors, and RSS feed URLs.
    
    Examples:
    
        podknow search "machine learning"
        podknow search "Joe Rogan" --platform itunes
        podknow search "startup stories" --limit 10
    """
    if not keywords.strip():
        raise click.BadParameter("Keywords cannot be empty")
    
    try:
        from ..exceptions import NetworkError
        
        verbose_echo(ctx, f"Using workflow orchestrator for platform: {platform}")
        
        # Use workflow orchestrator for enhanced error handling
        workflow = ctx.obj['workflow']
        results = workflow.execute_search_workflow(
            keywords=keywords,
            platform=platform,
            limit=limit
        )
        
        # Display results
        if not results:
            click.echo("No podcasts found matching your search criteria.")
            click.echo("\nTips:")
            click.echo("- Try different keywords or broader search terms")
            click.echo("- Check spelling and try alternative terms")
            if platform.lower() == 'spotify':
                click.echo("- Note: Spotify results may not include RSS feeds")
            return
        
        # Format and display results
        click.echo(f"\nFound {len(results)} podcast(s):\n")
        
        for i, podcast in enumerate(results, 1):
            click.echo(f"{i:2d}. {podcast.title}")
            click.echo(f"    Author: {podcast.author}")
            click.echo(f"    Platform: {podcast.platform}")
            
            # Handle RSS URL display
            if podcast.platform == 'Spotify':
                click.echo(f"    Spotify URL: {podcast.rss_url}")
                click.echo("    Note: Use iTunes search to find RSS feed for transcription")
            else:
                click.echo(f"    RSS Feed: {podcast.rss_url}")
            
            # Show description if available and not too long
            if podcast.description:
                desc = podcast.description[:150] + "..." if len(podcast.description) > 150 else podcast.description
                click.echo(f"    Description: {desc}")
            
            click.echo()  # Empty line between results
        
        # Show usage tip
        if any(p.platform == 'iTunes' for p in results):
            click.echo("To list episodes from a podcast, use:")
            click.echo("  podknow list <RSS_FEED_URL>")
        
    except KeyboardInterrupt:
        # Let KeyboardInterrupt bubble up to global handler
        raise
    except NetworkError as e:
        error_echo(f"Search failed: {e}")
        click.echo("\nTroubleshooting:")
        click.echo("- Check your internet connection")
        click.echo("- Try again in a few moments")
        if 'spotify' in str(e).lower():
            click.echo("- For Spotify: ensure SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET are set")
        raise click.ClickException(str(e))
    except Exception as e:
        verbose_echo(ctx, f"Unexpected error during search: {e}")
        error_echo("An unexpected error occurred during search")
        if ctx.obj.get('verbose', False):
            raise
        raise click.ClickException("An unexpected error occurred during search")


@cli.command("list")
@click.argument("rss_url", required=True)
@click.option(
    "--count", "-c",
    type=click.IntRange(1, 100),
    default=10,
    help="Number of episodes to list (default: 10)"
)
@click.option(
    "--show-descriptions", "-d",
    is_flag=True,
    help="Include episode descriptions in output"
)
@click.pass_context
def list_episodes(ctx: click.Context, rss_url: str, count: int, show_descriptions: bool):
    """
    List recent episodes from an RSS feed.
    
    RSS_URL should be a valid podcast RSS feed URL. Episodes are listed
    with unique identifiers that can be used with the transcribe command.
    
    Examples:
    
        podknow list https://feeds.example.com/podcast.xml
        podknow list https://feeds.example.com/podcast.xml --count 5
        podknow list https://feeds.example.com/podcast.xml --show-descriptions
    """
    if not rss_url.strip():
        raise click.BadParameter("RSS URL cannot be empty")
    
    # Basic URL validation
    if not (rss_url.startswith('http://') or rss_url.startswith('https://')):
        raise click.BadParameter("RSS URL must start with http:// or https://")
    
    try:
        from ..services.episode import EpisodeManagementError
        
        verbose_echo(ctx, f"Using workflow orchestrator for episode listing")
        
        # Use workflow orchestrator for enhanced error handling
        workflow = ctx.obj['workflow']
        podcast_info, episodes = workflow.execute_episode_listing_workflow(
            rss_url=rss_url,
            count=count
        )
        
        # Display podcast information
        click.echo(f"\nPodcast: {podcast_info.title}")
        click.echo(f"Author: {podcast_info.author}")
        click.echo(f"Total Episodes: {podcast_info.episode_count}")
        click.echo(f"Last Updated: {podcast_info.last_updated.strftime('%Y-%m-%d %H:%M')}")
        
        if podcast_info.description:
            desc = podcast_info.description[:200] + "..." if len(podcast_info.description) > 200 else podcast_info.description
            click.echo(f"Description: {desc}")
        
        click.echo(f"\nRSS Feed: {rss_url}")
        click.echo("=" * 60)
        
        # Display episodes
        if not episodes:
            click.echo("\nNo episodes found in this feed.")
            return
        
        click.echo(f"\nShowing {len(episodes)} most recent episode(s):\n")
        
        for i, episode in enumerate(episodes, 1):
            # Format publication date
            date_str = episode.publication_date.strftime("%Y-%m-%d")
            
            # Display episode info
            click.echo(f"{i:2d}. [{episode.id}] {episode.title}")
            click.echo(f"    Published: {date_str} | Duration: {episode.duration}")
            
            # Show description if requested
            if show_descriptions and episode.description:
                desc = episode.description[:300] + "..." if len(episode.description) > 300 else episode.description
                # Clean up description (remove HTML tags and extra whitespace)
                import re
                desc = re.sub(r'<[^>]+>', '', desc)  # Remove HTML tags
                desc = ' '.join(desc.split())  # Normalize whitespace
                click.echo(f"    Description: {desc}")
            
            click.echo()  # Empty line between episodes
        
        # Show usage tip
        click.echo("To transcribe an episode, use:")
        click.echo(f"  podknow transcribe <EPISODE_ID> --rss-url {rss_url}")
        click.echo("\nExample:")
        if episodes:
            click.echo(f"  podknow transcribe {episodes[0].id} --rss-url {rss_url}")
        
    except NetworkError as e:
        error_echo(f"Episode listing failed: {e}")
        click.echo("\nTroubleshooting:")
        click.echo("- Verify the RSS URL is correct and accessible")
        click.echo("- Check your internet connection")
        click.echo("- Ensure the feed contains valid episode data")
        raise click.ClickException(str(e))
    except Exception as e:
        verbose_echo(ctx, f"Unexpected error during episode listing: {e}")
        error_echo("An unexpected error occurred while listing episodes")
        if ctx.obj.get('verbose', False):
            raise
        raise click.ClickException("An unexpected error occurred while listing episodes")


@cli.command()
@click.argument("episode_id", required=True)
@click.option(
    "--rss-url", "-r",
    required=True,
    help="RSS feed URL where the episode can be found"
)
@click.option(
    "--output-dir", "-o",
    type=click.Path(exists=False, file_okay=False, dir_okay=True),
    help="Output directory for transcription file (default: ~/Documents/PodKnow)"
)
@click.option(
    "--skip-analysis",
    is_flag=True,
    help="Skip AI analysis and generate transcription only"
)
@click.option(
    "--claude-api-key",
    envvar="CLAUDE_API_KEY",
    help="Claude API key for analysis (can also be set via CLAUDE_API_KEY env var)"
)
@click.option(
    "--skip-language-detection",
    is_flag=True,
    help="Skip language detection and assume English content"
)
@click.option(
    "--language-detection-skip-minutes",
    type=float,
    default=2.0,
    help="Minutes to skip from beginning for language detection (default: 2.0)"
)
@click.pass_context
def transcribe(
    ctx: click.Context, 
    episode_id: str, 
    rss_url: str, 
    output_dir: Optional[str],
    skip_analysis: bool,
    claude_api_key: Optional[str],
    skip_language_detection: bool,
    language_detection_skip_minutes: float
):
    """
    Download and transcribe a podcast episode with optional AI analysis.
    
    EPISODE_ID should be obtained from the 'list' command output.
    The episode will be downloaded, transcribed using MLX-Whisper, and
    optionally analyzed using Claude AI for content insights.
    
    Examples:
    
        podknow transcribe abc123def456 --rss-url https://feeds.example.com/podcast.xml
        podknow transcribe abc123def456 --rss-url https://feeds.example.com/podcast.xml --skip-analysis
        podknow transcribe abc123def456 --rss-url https://feeds.example.com/podcast.xml --skip-language-detection
        podknow transcribe abc123def456 --rss-url https://feeds.example.com/podcast.xml --language-detection-skip-minutes 3.0
        podknow transcribe abc123def456 --rss-url https://feeds.example.com/podcast.xml --output-dir ./transcripts
    """
    if not episode_id.strip():
        raise click.BadParameter("Episode ID cannot be empty")
    
    if not rss_url.strip():
        raise click.BadParameter("RSS URL cannot be empty")
    
    # Basic URL validation
    if not (rss_url.startswith('http://') or rss_url.startswith('https://')):
        raise click.BadParameter("RSS URL must start with http:// or https://")
    
    # Validate Claude API key if analysis is requested
    if not skip_analysis and not claude_api_key:
        raise click.BadParameter(
            "Claude API key is required for analysis. "
            "Use --claude-api-key option or set CLAUDE_API_KEY environment variable. "
            "Alternatively, use --skip-analysis to generate transcription only."
        )
    
    try:
        verbose_echo(ctx, f"Starting transcription workflow for episode {episode_id}")
        
        # Use workflow orchestrator for comprehensive error handling and recovery
        workflow = ctx.obj['workflow']
        output_path = workflow.execute_transcription_workflow(
            episode_id=episode_id,
            rss_url=rss_url,
            output_dir=output_dir,
            claude_api_key=claude_api_key,
            skip_analysis=skip_analysis,
            skip_language_detection=skip_language_detection,
            language_detection_skip_minutes=language_detection_skip_minutes
        )
        
        # Success message
        click.echo(f"\n✅ Transcription completed successfully!")
        click.echo(f"📄 Output file: {output_path}")
        
    except KeyboardInterrupt:
        progress_echo("Transcription cancelled by user")
        sys.exit(130)
    except NetworkError as e:
        error_echo(f"Transcription failed: {e}")
        click.echo("\nTroubleshooting:")
        click.echo("- Verify the RSS URL and episode ID are correct")
        click.echo("- Check your internet connection")
        click.echo("- Ensure the episode audio is accessible")
        raise click.ClickException(str(e))
    except Exception as e:
        verbose_echo(ctx, f"Unexpected error during transcription: {e}")
        error_echo("An unexpected error occurred during transcription")
        if ctx.obj.get('verbose', False):
            raise
        raise click.ClickException("An unexpected error occurred during transcription")


@cli.command()
@click.argument("transcription_file", type=click.Path(exists=True, readable=True))
@click.option(
    "--claude-api-key",
    envvar="CLAUDE_API_KEY",
    required=True,
    help="Claude API key for analysis (can also be set via CLAUDE_API_KEY env var)"
)
@click.option(
    "--output-file", "-o",
    type=click.Path(exists=False),
    help="Output file for analyzed transcription (default: overwrite input file)"
)
@click.pass_context
def analyze(
    ctx: click.Context, 
    transcription_file: str, 
    claude_api_key: str,
    output_file: Optional[str]
):
    """
    Analyze an existing transcription file using Claude AI.
    
    TRANSCRIPTION_FILE should be a markdown file with episode metadata
    and transcription content. The analysis will add summary, topics,
    keywords, and sponsor detection to the file.
    
    Examples:
    
        podknow analyze episode_transcript.md
        podknow analyze episode_transcript.md --output-file analyzed_transcript.md
    """
    if not os.path.isfile(transcription_file):
        raise click.BadParameter(f"Transcription file not found: {transcription_file}")
    
    try:
        verbose_echo(ctx, f"Starting analysis of {transcription_file}")
        
        # Use workflow orchestrator for enhanced error handling
        workflow = ctx.obj['workflow']
        output_path = workflow.execute_analysis_workflow(
            transcription_file=transcription_file,
            claude_api_key=claude_api_key,
            output_file=output_file
        )
        
        # Success message
        click.echo(f"\n✅ Analysis completed successfully!")
        click.echo(f"📄 Output file: {output_path}")
        return
        
    except AnalysisError as e:
        error_echo(f"Analysis failed: {e}")
        click.echo("\nTroubleshooting:")
        click.echo("- Verify Claude API key is valid")
        click.echo("- Check internet connection")
        click.echo("- Ensure transcription text is readable")
        raise click.ClickException(str(e))
    except Exception as e:
        verbose_echo(ctx, f"Unexpected error during analysis: {e}")
        error_echo("An unexpected error occurred during analysis")
        if ctx.obj.get('verbose', False):
            raise
        raise click.ClickException("An unexpected error occurred during analysis")


@cli.command()
@click.option(
    "--force", "-f",
    is_flag=True,
    help="Overwrite existing configuration file"
)
@click.pass_context
def setup(ctx: click.Context, force: bool):
    """
    Set up PodKnow configuration for first-time use.
    
    This command creates a default configuration file with example prompts
    and settings. You can then edit the file to customize PodKnow for your needs.
    
    Examples:
    
        podknow setup
        podknow setup --force  # Overwrite existing config
    """
    try:
        from ..config.manager import ConfigManager
        from ..exceptions import ConfigurationError
        
        verbose_echo(ctx, "Starting configuration setup")
        
        # Initialize config manager
        config_manager = ConfigManager()
        
        # Check if config already exists
        if config_manager.config_exists() and not force:
            click.echo("Configuration file already exists.")
            click.echo(f"Location: {config_manager.config_path}")
            click.echo("\nTo overwrite the existing configuration, use:")
            click.echo("  podknow setup --force")
            click.echo("\nTo check configuration status, use:")
            click.echo("  podknow config-status")
            return
        
        # Create default configuration
        progress_echo("Creating default configuration file...")
        
        try:
            config_path = config_manager.generate_config_for_first_time_setup()
            verbose_echo(ctx, f"Configuration created at: {config_path}")
        except Exception as e:
            error_echo(f"Failed to create configuration: {e}")
            sys.exit(1)
        
        # Provide setup instructions
        click.echo(f"\n✅ Configuration file created successfully!")
        click.echo(f"📄 Location: {config_path}")
        click.echo("\n📋 Next steps:")
        click.echo("1. Edit the configuration file to add your Claude API key:")
        click.echo(f"   nano {config_path}")
        click.echo("\n2. Get a Claude API key from: https://console.anthropic.com/")
        click.echo("\n3. Optionally add Spotify credentials for enhanced podcast discovery")
        click.echo("\n4. Customize the analysis prompts to match your needs")
        click.echo("\n5. Test your setup with:")
        click.echo("   podknow config-status")
        
    except Exception as e:
        verbose_echo(ctx, f"Unexpected error during setup: {e}")
        error_echo("An unexpected error occurred during setup")
        if ctx.obj.get('verbose', False):
            raise
        sys.exit(1)


@cli.command("config-status")
@click.pass_context
def config_status(ctx: click.Context):
    """
    Check configuration status and validate settings.
    
    This command checks if the configuration file exists, validates the
    settings, and reports any issues that need to be addressed.
    
    Examples:
    
        podknow config-status
    """
    try:
        from ..config.manager import ConfigManager
        from ..exceptions import ConfigurationError
        
        verbose_echo(ctx, "Checking configuration status")
        
        # Initialize config manager
        config_manager = ConfigManager()
        
        # Get configuration status
        status = config_manager.get_config_status()
        
        # Display status information
        click.echo("📋 Configuration Status")
        click.echo("=" * 50)
        
        if status['config_exists']:
            click.echo(f"✅ Configuration file exists: {status['config_path']}")
        else:
            click.echo(f"❌ Configuration file not found: {status['config_path']}")
            click.echo("\nTo create a configuration file, run:")
            click.echo("  podknow setup")
            return
        
        if status['is_valid']:
            click.echo("✅ Configuration is valid")
        else:
            click.echo("❌ Configuration has issues")
        
        # Show missing keys
        if status['missing_keys']:
            click.echo(f"\n⚠️  Missing API keys:")
            for key in status['missing_keys']:
                click.echo(f"   - {key}")
        
        # Show validation errors
        if status['validation_errors']:
            click.echo(f"\n❌ Validation errors:")
            for error in status['validation_errors']:
                click.echo(f"   - {error}")
        
        # Show environment variables
        click.echo(f"\n🌍 Environment Variables:")
        env_vars = {
            'CLAUDE_API_KEY': bool(os.getenv('CLAUDE_API_KEY')),
            'SPOTIFY_CLIENT_ID': bool(os.getenv('SPOTIFY_CLIENT_ID')),
            'SPOTIFY_CLIENT_SECRET': bool(os.getenv('SPOTIFY_CLIENT_SECRET')),
        }
        
        for var, is_set in env_vars.items():
            status_icon = "✅" if is_set else "❌"
            click.echo(f"   {status_icon} {var}: {'Set' if is_set else 'Not set'}")
        
        # Show workflow status if available
        if ctx.obj.get('workflow'):
            workflow = ctx.obj['workflow']
            workflow_status = workflow.get_workflow_status()
            
            click.echo(f"\n🔧 System Status:")
            
            # Dependencies
            deps = workflow_status.get('dependencies', {})
            for dep, available in deps.items():
                status_icon = "✅" if available else "❌"
                click.echo(f"   {status_icon} {dep}: {'Available' if available else 'Missing'}")
        
        # Provide recommendations
        if not status['is_valid'] or status['missing_keys'] or status['validation_errors']:
            click.echo(f"\n💡 Recommendations:")
            
            if 'claude_api_key' in status['missing_keys']:
                click.echo("   - Add your Claude API key to the configuration file")
                click.echo("   - Get an API key from: https://console.anthropic.com/")
            
            if status['validation_errors']:
                click.echo("   - Fix the validation errors listed above")
                click.echo("   - Check the configuration file syntax")
            
            click.echo(f"   - Edit configuration: nano {status['config_path']}")
        else:
            click.echo(f"\n🎉 Your PodKnow setup is ready to use!")
        
    except Exception as e:
        verbose_echo(ctx, f"Unexpected error checking config status: {e}")
        error_echo("An unexpected error occurred while checking configuration")
        if ctx.obj.get('verbose', False):
            raise
        sys.exit(1)


# Helper functions for CLI utilities
def verbose_echo(ctx: click.Context, message: str):
    """Echo message only if verbose mode is enabled."""
    if ctx.obj and ctx.obj.get('verbose', False):
        click.echo(f"[DEBUG] {message}", err=True)


def progress_echo(message: str, nl: bool = True):
    """Echo progress message to stderr."""
    click.echo(f"[INFO] {message}", err=True, nl=nl)


def error_echo(message: str):
    """Echo error message to stderr."""
    click.echo(f"[ERROR] {message}", err=True)


if __name__ == "__main__":
    cli()