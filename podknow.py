#!/usr/bin/env python3
"""
PodKnow - Podcast RSS Feed Processor and Transcriber
A command line utility that processes podcast RSS feeds, extracts episode metadata,
downloads media files, and generates transcriptions using Ollama.
"""

import argparse
import sys
import os
import tempfile
import re
import warnings
import logging
from pathlib import Path
from typing import Dict, List, Optional
import feedparser
import requests
from urllib.parse import urljoin, urlparse
import json

try:
    import mlx_whisper
    WHISPER_BACKEND = "mlx"
    print("Using MLX-Whisper (optimized for Apple Silicon)")
except ImportError:
    import whisper
    WHISPER_BACKEND = "openai"
    print("Warning: MLX-Whisper not found. Using standard OpenAI Whisper (slower on Apple Silicon)")


class PodcastProcessor:
    def __init__(self, output_dir: str = "./output", paragraph_threshold: float = 2.0,
                 llm_provider: str = "none", llm_model: str = "llama3.2:3b",
                 ollama_url: str = "http://localhost:11434"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.paragraph_threshold = paragraph_threshold
        self.llm_provider = llm_provider
        self.llm_model = llm_model
        self.ollama_url = ollama_url
    
    def parse_rss_feed(self, rss_url: str, episode_number: Optional[str] = None) -> Dict:
        """Parse RSS feed and extract episode data (latest or specific episode)."""
        print(f"Fetching RSS feed from: {rss_url}")
        
        try:
            feed = feedparser.parse(rss_url)
            if feed.bozo:
                print(f"Warning: RSS feed parsing had issues: {feed.bozo_exception}")
            
            if not feed.entries:
                raise ValueError("No episodes found in RSS feed")
            
            # Find the target episode
            target_episode = None
            
            if episode_number:
                print(f"Looking for episode number: {episode_number}")
                # Search for specific episode by iTunes episode number
                for entry in feed.entries:
                    # Check for iTunes episode number
                    itunes_episode = None
                    if hasattr(entry, 'itunes_episode'):
                        itunes_episode = entry.itunes_episode
                    elif hasattr(entry, 'tags'):
                        # Look through tags for itunes:episode
                        for tag in entry.tags:
                            if tag.term.lower() in ['itunes:episode', 'episode']:
                                itunes_episode = tag.label or getattr(tag, 'value', None)
                                break
                    
                    # Also check in the raw entry data
                    if not itunes_episode and hasattr(entry, 'itunes_episode'):
                        itunes_episode = str(entry.itunes_episode)
                    
                    # Convert to string for comparison
                    if itunes_episode and str(itunes_episode).strip() == str(episode_number).strip():
                        target_episode = entry
                        print(f"Found episode {episode_number}: {entry.title}")
                        break
                
                if not target_episode:
                    # If not found by iTunes episode, try treating as position (1-based index) first
                    print(f"Episode {episode_number} not found by iTunes episode number.")
                    try:
                        position = int(episode_number)
                        if 1 <= position <= len(feed.entries):
                            target_episode = feed.entries[position - 1]
                            print(f"Using feed position {position}: {target_episode.title}")
                        else:
                            raise ValueError(f"Position {position} out of range (feed has {len(feed.entries)} episodes)")
                    except ValueError as ve:
                        if "out of range" in str(ve):
                            raise ve
                        # Not a valid integer, try searching by title as last resort
                        print(f"Not a valid position number. Checking titles...")
                        for entry in feed.entries:
                            if str(episode_number) in entry.title:
                                target_episode = entry
                                print(f"Found episode by title match: {entry.title}")
                                break

                        if not target_episode:
                            raise ValueError(f"Episode '{episode_number}' not found in RSS feed (tried episode number, position, and title search)")
            else:
                # Get the latest episode (first entry)
                target_episode = feed.entries[0]
                print(f"Using latest episode: {target_episode.title}")
            
            latest_episode = target_episode
            
            # Extract episode metadata
            episode_data = {
                'title': getattr(latest_episode, 'title', 'Unknown Title'),
                'description': getattr(latest_episode, 'description', ''),
                'summary': getattr(latest_episode, 'summary', ''),
                'published': getattr(latest_episode, 'published', ''),
                'link': getattr(latest_episode, 'link', ''),
                'duration': '',
                'chapters': [],
                'links': [],
                'enclosures': []
            }
            
            # Extract duration if available
            if hasattr(latest_episode, 'itunes_duration'):
                episode_data['duration'] = latest_episode.itunes_duration
            
            # Extract chapter marks if available
            if hasattr(latest_episode, 'podcast_chapters'):
                episode_data['chapters'] = latest_episode.podcast_chapters
            
            # Extract enclosures (media files)
            if hasattr(latest_episode, 'enclosures'):
                episode_data['enclosures'] = latest_episode.enclosures
            elif hasattr(latest_episode, 'links'):
                for link in latest_episode.links:
                    if link.get('type', '').startswith('audio/') or link.get('type', '').startswith('video/'):
                        episode_data['enclosures'].append(link)
            
            # Extract links from description and summary
            episode_data['links'] = self.extract_links_from_text(
                episode_data['description'] + ' ' + episode_data['summary']
            )
            
            return episode_data
            
        except Exception as e:
            raise RuntimeError(f"Failed to parse RSS feed: {e}")

    def list_episodes(self, rss_url: str, limit: int = 10) -> None:
        """List recent episodes from the RSS feed."""
        print(f"Fetching episodes from: {rss_url}\n")

        try:
            feed = feedparser.parse(rss_url)
            if feed.bozo:
                print(f"Warning: RSS feed parsing had issues: {feed.bozo_exception}\n")

            if not feed.entries:
                print("No episodes found in RSS feed.")
                return

            total_episodes = len(feed.entries)
            episodes_to_show = min(limit, total_episodes)

            print(f"Found {total_episodes} episode(s) in feed. Showing last {episodes_to_show}:\n")

            # Display episodes
            for idx, entry in enumerate(feed.entries[:episodes_to_show], 1):
                title = getattr(entry, 'title', 'Unknown Title')
                published = getattr(entry, 'published', 'Unknown date')

                # Try to extract iTunes episode number
                itunes_episode = None
                if hasattr(entry, 'itunes_episode'):
                    itunes_episode = entry.itunes_episode
                elif hasattr(entry, 'tags'):
                    for tag in entry.tags:
                        if tag.term.lower() in ['itunes:episode', 'episode']:
                            itunes_episode = tag.label or getattr(tag, 'value', None)
                            break

                # Format episode identifier and usage instruction
                if itunes_episode:
                    episode_id = f"Episode #{itunes_episode} (use: -e {itunes_episode})"
                else:
                    episode_id = f"Use: -e {idx}"

                # Extract duration if available
                duration = ""
                if hasattr(entry, 'itunes_duration'):
                    duration = f" - Duration: {entry.itunes_duration}"

                print(f"  {idx:2d}. [{episode_id}]")
                print(f"      \"{title}\"")
                print(f"      Published: {published}{duration}")
                print()

            if total_episodes > episodes_to_show:
                print(f"... and {total_episodes - episodes_to_show} more episode(s).")
                print(f"Use --limit to show more episodes.\n")

        except Exception as e:
            print(f"Error fetching episodes: {e}")
            sys.exit(1)

    def extract_links_from_text(self, text: str) -> List[str]:
        """Extract URLs from text content."""
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        return list(set(re.findall(url_pattern, text)))
    
    def find_media_url(self, episode_data: Dict) -> Optional[str]:
        """Find the best media file URL (mp3 or mp4)."""
        media_url = None
        
        for enclosure in episode_data['enclosures']:
            media_type = enclosure.get('type', '').lower()
            if 'audio/mpeg' in media_type or 'audio/mp3' in media_type:
                media_url = enclosure.get('href') or enclosure.get('url')
                break
            elif 'video/mp4' in media_type:
                media_url = enclosure.get('href') or enclosure.get('url')
        
        return media_url
    
    def download_media_file(self, url: str) -> str:
        """Download media file to temporary location."""
        print(f"Downloading media file from: {url}")
        
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            # Determine file extension from URL or content type
            parsed_url = urlparse(url)
            file_ext = os.path.splitext(parsed_url.path)[1]
            if not file_ext:
                content_type = response.headers.get('content-type', '')
                if 'audio/mpeg' in content_type:
                    file_ext = '.mp3'
                elif 'video/mp4' in content_type:
                    file_ext = '.mp4'
                else:
                    file_ext = '.mp3'  # default
            
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(suffix=file_ext, delete=False)
            
            # Download with progress indication
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with temp_file as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            print(f"\rDownload progress: {progress:.1f}%", end='', flush=True)
            
            print(f"\nMedia file downloaded to: {temp_file.name}")
            return temp_file.name
            
        except Exception as e:
            raise RuntimeError(f"Failed to download media file: {e}")
    
    def format_segments_to_paragraphs(self, segments: List[Dict], pause_threshold: float = 2.0,
                                      include_timestamps: bool = True) -> str:
        """
        Format Whisper segments into readable paragraphs based on pause duration.

        Args:
            segments: List of segment dictionaries from Whisper
            pause_threshold: Minimum pause in seconds to start a new paragraph (default: 2.0)
            include_timestamps: Whether to include timestamps before each paragraph

        Returns:
            Formatted text with paragraph breaks
        """
        if not segments:
            return ""

        paragraphs = []
        current_paragraph = []
        last_end_time = 0

        for segment in segments:
            start_time = segment.get('start', 0)
            end_time = segment.get('end', 0)
            text = segment.get('text', '').strip()

            if not text:
                continue

            # Check if there's a significant pause since the last segment
            pause_duration = start_time - last_end_time

            if pause_duration >= pause_threshold and current_paragraph:
                # Finish current paragraph and start a new one
                paragraph_text = ' '.join(current_paragraph)

                if include_timestamps:
                    # Format timestamp as [MM:SS]
                    minutes = int(last_end_time // 60)
                    seconds = int(last_end_time % 60)
                    timestamp = f"[{minutes:02d}:{seconds:02d}]"
                    paragraphs.append(f"{timestamp} {paragraph_text}")
                else:
                    paragraphs.append(paragraph_text)

                current_paragraph = []

            current_paragraph.append(text)
            last_end_time = end_time

        # Add the final paragraph
        if current_paragraph:
            paragraph_text = ' '.join(current_paragraph)

            if include_timestamps:
                minutes = int(last_end_time // 60)
                seconds = int(last_end_time % 60)
                timestamp = f"[{minutes:02d}:{seconds:02d}]"
                paragraphs.append(f"{timestamp} {paragraph_text}")
            else:
                paragraphs.append(paragraph_text)

        return '\n\n'.join(paragraphs)

    def transcribe_with_whisper(self, media_file_path: str) -> str:
        """Transcribe media file using Whisper (MLX or OpenAI backend)."""
        print(f"Transcribing media file: {media_file_path}")
        print(f"Loading Whisper model (backend: {WHISPER_BACKEND})...")

        try:
            # Suppress warnings and info messages from Whisper, PyTorch, and other libraries
            warnings.filterwarnings("ignore")

            # Suppress logging output from various libraries
            logging.getLogger("whisper").setLevel(logging.ERROR)
            logging.getLogger("torch").setLevel(logging.ERROR)
            logging.getLogger("numba").setLevel(logging.ERROR)

            if WHISPER_BACKEND == "mlx":
                # MLX-Whisper: Optimized for Apple Silicon (Metal + Neural Engine)
                print("Using Apple Silicon acceleration (Metal + Neural Engine)...")
                result = mlx_whisper.transcribe(
                    media_file_path,
                    path_or_hf_repo="mlx-community/whisper-small-mlx",
                    verbose=False
                )
            else:
                # OpenAI Whisper: Standard PyTorch backend
                print("Using standard PyTorch backend...")
                model = whisper.load_model("small")
                result = model.transcribe(media_file_path, verbose=False)

            print("Transcription completed!")

            # Extract segments and format into paragraphs
            segments = result.get("segments", [])
            detected_language = result.get("language", "unknown")

            if segments:
                # Format segments into readable paragraphs with timestamps
                transcription = self.format_segments_to_paragraphs(
                    segments,
                    pause_threshold=self.paragraph_threshold,
                    include_timestamps=True
                )
                print(f"Transcription completed! Created {len(transcription.split(chr(10) + chr(10)))} paragraphs.")
            else:
                # Fallback to raw text if no segments available
                transcription = result["text"].strip()
                print("Transcription completed! (No segments available, using raw text)")

            # Add some metadata about the transcription
            backend_info = "MLX-Whisper (Apple Silicon optimized)" if WHISPER_BACKEND == "mlx" else "OpenAI Whisper"
            formatted_transcription = f"""**Transcription Language:** {detected_language}

**Transcription:**

{transcription}

---
*Transcribed using {backend_info} (small model) with paragraph segmentation based on speech pauses*"""

            print(f"Language detected: {detected_language}")
            print(f"Total characters: {len(transcription)}")

            return formatted_transcription
            
        except Exception as e:
            error_msg = f"Whisper transcription failed: {e}"
            print(error_msg)
            
            # Provide fallback information
            fallback = f"""# Transcription Error

{error_msg}

## Media File Information
- File: {media_file_path}
- Size: {os.path.getsize(media_file_path) if os.path.exists(media_file_path) else 'Unknown'} bytes

## Troubleshooting
1. Ensure the media file is a valid audio/video format
2. Check that you have enough disk space and memory
3. Try with a smaller audio file first
4. Consider using a smaller Whisper model (tiny/small) if you have limited resources

## Manual Transcription
You can also transcribe manually using:
```bash
whisper "{media_file_path}" --output_format txt
```
"""
            return fallback

    def _call_ollama(self, transcript: str, model: str, url: str) -> Dict:
        """Call Ollama API for transcript analysis."""
        try:
            import ollama

            # Truncate if transcript too long (keep first 100K chars)
            if len(transcript) > 100000:
                print(f"Transcript is long ({len(transcript)} chars), truncating to 100K for analysis...")
                transcript = transcript[:100000] + "\n\n[... transcript truncated ...]"

            prompt = f"""Analyze this podcast transcript and provide:

1. SUMMARY: Write a concise 2-3 paragraph summary of the episode
2. TOP TOPICS: List the 5 most important topics discussed (one sentence each)
3. KEYWORDS: List 10-15 relevant keywords

Transcript:
{transcript}

Respond in this EXACT format:

SUMMARY:
[Your summary here]

TOPICS:
1. [First topic]
2. [Second topic]
3. [Third topic]
4. [Fourth topic]
5. [Fifth topic]

KEYWORDS:
keyword1, keyword2, keyword3, ..."""

            client = ollama.Client(host=url)
            response = client.chat(
                model=model,
                messages=[{
                    'role': 'user',
                    'content': prompt
                }]
            )

            # Parse response
            content = response['message']['content']
            return self._parse_llm_response(content)

        except Exception as e:
            print(f"Ollama analysis failed: {e}")
            print(f"  Make sure Ollama is running: ollama serve")
            print(f"  And model is pulled: ollama pull {model}")
            return None

    def _call_claude(self, transcript: str) -> Dict:
        """Call Claude API for transcript analysis."""
        try:
            import anthropic

            # Truncate if transcript too long
            if len(transcript) > 100000:
                print(f"Transcript is long ({len(transcript)} chars), truncating to 100K for analysis...")
                transcript = transcript[:100000] + "\n\n[... transcript truncated ...]"

            prompt = f"""Analyze this podcast transcript and provide:

1. SUMMARY: Write a concise 2-3 paragraph summary of the episode
2. TOP TOPICS: List the 5 most important topics discussed (one sentence each)
3. KEYWORDS: List 10-15 relevant keywords

Transcript:
{transcript}

Respond in this EXACT format:

SUMMARY:
[Your summary here]

TOPICS:
1. [First topic]
2. [Second topic]
3. [Third topic]
4. [Fourth topic]
5. [Fifth topic]

KEYWORDS:
keyword1, keyword2, keyword3, ..."""

            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                print("ERROR: ANTHROPIC_API_KEY environment variable not set")
                print("  Set it with: export ANTHROPIC_API_KEY=sk-ant-...")
                return None

            client = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2000,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            # Parse response
            content = response.content[0].text
            return self._parse_llm_response(content)

        except Exception as e:
            print(f"Claude analysis failed: {e}")
            return None

    def _parse_llm_response(self, content: str) -> Dict:
        """Parse structured LLM response into dictionary."""
        try:
            result = {
                "summary": "",
                "topics": [],
                "keywords": []
            }

            # Split by sections
            sections = content.split("\n\n")
            current_section = None

            for section in sections:
                section = section.strip()

                if section.startswith("SUMMARY:"):
                    current_section = "summary"
                    summary_text = section.replace("SUMMARY:", "").strip()
                    if summary_text:
                        result["summary"] = summary_text
                elif section.startswith("TOPICS:"):
                    current_section = "topics"
                elif section.startswith("KEYWORDS:"):
                    current_section = "keywords"
                    keywords_text = section.replace("KEYWORDS:", "").strip()
                    if keywords_text:
                        result["keywords"] = [k.strip() for k in keywords_text.split(",")]
                elif current_section == "summary" and section:
                    result["summary"] += "\n\n" + section
                elif current_section == "topics" and section:
                    # Extract topic lines
                    lines = section.split("\n")
                    for line in lines:
                        line = line.strip()
                        if line and (line[0].isdigit() or line.startswith("-")):
                            # Remove numbering
                            topic = re.sub(r'^[\d\-\.\)]+\s*', '', line)
                            if topic:
                                result["topics"].append(topic)

            # Limit topics to 5
            result["topics"] = result["topics"][:5]

            return result

        except Exception as e:
            print(f"Failed to parse LLM response: {e}")
            return None

    def analyze_transcript_with_llm(self, transcript: str) -> Optional[Dict]:
        """
        Analyze transcript using configured LLM provider.

        Returns:
            Dictionary with 'summary', 'topics', and 'keywords' keys, or None if analysis fails
        """
        if self.llm_provider == "none":
            return None

        print(f"\nAnalyzing transcript with {self.llm_provider}...")

        if self.llm_provider == "ollama":
            return self._call_ollama(transcript, self.llm_model, self.ollama_url)
        elif self.llm_provider == "claude":
            return self._call_claude(transcript)
        else:
            print(f"Unknown LLM provider: {self.llm_provider}")
            return None

    def create_markdown_file(self, episode_data: Dict, transcription: str, media_url: str,
                            llm_analysis: Optional[Dict] = None) -> str:
        """Create markdown file with episode metadata and transcription."""
        # Create safe filename from episode title
        safe_title = re.sub(r'[^\w\s-]', '', episode_data['title'])
        safe_title = re.sub(r'[-\s]+', '-', safe_title)
        
        # Truncate filename if too long (max 100 chars for the title part)
        max_title_length = 100
        if len(safe_title) > max_title_length:
            # Try to truncate at word boundary
            truncated = safe_title[:max_title_length]
            last_dash = truncated.rfind('-')
            if last_dash > max_title_length * 0.7:  # If we can find a dash in the last 30%
                safe_title = truncated[:last_dash]
            else:
                safe_title = truncated
            print(f"Filename truncated due to length: {safe_title}...")
        
        filename = f"{safe_title}.md"
        filepath = self.output_dir / filename
        
        print(f"Creating markdown file: {filepath}")
        
        content = []
        
        # Add YAML front matter
        content.append("---")
        content.append(f"title: \"{episode_data['title']}\"")
        if episode_data['duration']:
            content.append(f"duration: \"{episode_data['duration']}\"")
        if episode_data['link']:
            content.append(f"episode_link: \"{episode_data['link']}\"")
        if media_url:
            content.append(f"media_url: \"{media_url}\"")
        if episode_data['published']:
            content.append(f"published: \"{episode_data['published']}\"")
        content.append("---")
        content.append("")
        
        content.append(f"# {episode_data['title']}")
        content.append("")

        # LLM Analysis (if available)
        if llm_analysis:
            # Summary
            if llm_analysis.get('summary'):
                content.append("## Summary")
                content.append("")
                content.append(llm_analysis['summary'])
                content.append("")

            # Key Topics
            if llm_analysis.get('topics'):
                content.append("## Key Topics")
                content.append("")
                for idx, topic in enumerate(llm_analysis['topics'], 1):
                    content.append(f"{idx}. {topic}")
                content.append("")

            # Keywords
            if llm_analysis.get('keywords'):
                content.append("## Keywords")
                content.append("")
                content.append(", ".join(llm_analysis['keywords']))
                content.append("")

        # Description
        if episode_data['description']:
            content.append("## Description")
            content.append("")
            content.append(episode_data['description'])
            content.append("")
        
        # Episode Notes (from RSS) if different from description
        if episode_data['summary'] and episode_data['summary'] != episode_data['description']:
            content.append("## Episode Notes")
            content.append("")
            content.append(episode_data['summary'])
            content.append("")
        
        # Chapter marks
        if episode_data['chapters']:
            content.append("## Chapters")
            content.append("")
            for chapter in episode_data['chapters']:
                content.append(f"- {chapter}")
            content.append("")
        
        # Links
        if episode_data['links']:
            content.append("## Links")
            content.append("")
            for link in episode_data['links']:
                content.append(f"- {link}")
            content.append("")
        
        # Transcription
        content.append("## Transcription")
        content.append("")
        content.append(transcription)
        
        # Write to file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(content))
        
        return str(filepath)
    
    def process_podcast(self, rss_url: str, episode_number: Optional[str] = None) -> str:
        """Main processing function."""
        try:
            # Parse RSS feed
            episode_data = self.parse_rss_feed(rss_url, episode_number)
            
            # Find media URL
            media_url = self.find_media_url(episode_data)
            if not media_url:
                raise ValueError("No suitable media file found in episode")
            
            # Download media file
            media_file = self.download_media_file(media_url)
            
            try:
                # Transcribe media file
                transcription = self.transcribe_with_whisper(media_file)

                # Analyze transcript with LLM (if configured)
                llm_analysis = None
                if self.llm_provider != "none":
                    llm_analysis = self.analyze_transcript_with_llm(transcription)

                    if llm_analysis:
                        print(f"✓ LLM analysis completed successfully")
                    else:
                        print(f"⚠ LLM analysis failed or was skipped")

                # Create markdown file
                markdown_file = self.create_markdown_file(episode_data, transcription, media_url, llm_analysis)

                return markdown_file
                
            finally:
                # Clean up temporary media file
                if os.path.exists(media_file):
                    os.unlink(media_file)
                    print(f"Cleaned up temporary file: {media_file}")
            
        except Exception as e:
            print(f"Error processing podcast: {e}")
            return None


def main():
    parser = argparse.ArgumentParser(
        description="Process podcast RSS feed and generate transcribed markdown"
    )
    parser.add_argument(
        "rss_url",
        help="URL to the podcast RSS feed"
    )
    parser.add_argument(
        "-o", "--output",
        default="./output",
        help="Output directory for markdown files (default: ./output)"
    )
    parser.add_argument(
        "-e", "--episode",
        help="Specific episode to process (iTunes episode number or feed position). Use --list to see available episodes and their identifiers."
    )
    parser.add_argument(
        "-l", "--list",
        action="store_true",
        help="List recent episodes from the RSS feed without processing"
    )
    parser.add_argument(
        "-n", "--limit",
        type=int,
        default=10,
        help="Number of episodes to list when using --list (default: 10)"
    )
    parser.add_argument(
        "-p", "--paragraph-threshold",
        type=float,
        default=2.0,
        help="Minimum pause in seconds to create a new paragraph in transcription (default: 2.0)"
    )
    parser.add_argument(
        "--llm-provider",
        choices=["ollama", "claude", "none"],
        default="none",
        help="LLM provider for post-processing analysis (default: none)"
    )
    parser.add_argument(
        "--llm-model",
        default="llama3.2:3b",
        help="Ollama model name for analysis (default: llama3.2:3b)"
    )
    parser.add_argument(
        "--ollama-url",
        default="http://localhost:11434",
        help="Ollama API URL (default: http://localhost:11434)"
    )

    args = parser.parse_args()

    processor = PodcastProcessor(
        args.output,
        args.paragraph_threshold,
        args.llm_provider,
        args.llm_model,
        args.ollama_url
    )

    # If list mode is enabled, just list episodes and exit
    if args.list:
        processor.list_episodes(args.rss_url, args.limit)
        sys.exit(0)

    # Otherwise, proceed with normal processing
    result = processor.process_podcast(args.rss_url, args.episode)

    if result:
        print(f"\nSuccess! Markdown file created: {result}")
    else:
        print("\nFailed to process podcast.")
        sys.exit(1)


if __name__ == "__main__":
    main() 