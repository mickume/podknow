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
from pathlib import Path
from typing import Dict, List, Optional
import feedparser
import requests
from urllib.parse import urljoin, urlparse
import json
import whisper


class PodcastProcessor:
    def __init__(self, output_dir: str = "./output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
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
                    # If not found by iTunes episode, try searching by title/description
                    print(f"Episode {episode_number} not found by iTunes episode number. Checking titles...")
                    for entry in feed.entries:
                        if str(episode_number) in entry.title:
                            target_episode = entry
                            print(f"Found episode by title match: {entry.title}")
                            break
                    
                    if not target_episode:
                        raise ValueError(f"Episode {episode_number} not found in RSS feed")
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
    
    def transcribe_with_whisper(self, media_file_path: str) -> str:
        """Transcribe media file using OpenAI Whisper."""
        print(f"Transcribing media file: {media_file_path}")
        print("Loading Whisper model (this may take a moment on first run)...")
        
        try:
            # Load the Whisper model
            # Using 'base' model as a good balance between speed and accuracy
            # Other options: tiny, small, medium, large
            model = whisper.load_model("base")
            
            print("Model loaded. Starting transcription...")
            
            # Transcribe the audio file
            result = model.transcribe(media_file_path)
            
            # Extract the transcription text
            transcription = result["text"].strip()
            
            # Add some metadata about the transcription
            detected_language = result.get("language", "unknown")
            
            formatted_transcription = f"""**Transcription Language:** {detected_language}

**Transcription:**

{transcription}

---
*Transcribed using OpenAI Whisper (base model)*"""
            
            print(f"Transcription completed! Language detected: {detected_language}")
            print(f"Transcription length: {len(transcription)} characters")
            
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
    
    def create_markdown_file(self, episode_data: Dict, transcription: str) -> str:
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
        content.append(f"# {episode_data['title']}")
        content.append("")
        
        if episode_data['published']:
            content.append(f"**Published:** {episode_data['published']}")
            content.append("")
        
        if episode_data['duration']:
            content.append(f"**Duration:** {episode_data['duration']}")
            content.append("")
        
        if episode_data['link']:
            content.append(f"**Episode Link:** {episode_data['link']}")
            content.append("")
        
        # Description
        if episode_data['description']:
            content.append("## Description")
            content.append("")
            content.append(episode_data['description'])
            content.append("")
        
        # Summary if different from description
        if episode_data['summary'] and episode_data['summary'] != episode_data['description']:
            content.append("## Summary")
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
                
                # Create markdown file
                markdown_file = self.create_markdown_file(episode_data, transcription)
                
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
        help="Specific episode number to process (by iTunes episode number). If not provided, uses latest episode."
    )
    
    args = parser.parse_args()
    
    processor = PodcastProcessor(args.output)
    result = processor.process_podcast(args.rss_url, args.episode)
    
    if result:
        print(f"\nSuccess! Markdown file created: {result}")
    else:
        print("\nFailed to process podcast.")
        sys.exit(1)


if __name__ == "__main__":
    main() 