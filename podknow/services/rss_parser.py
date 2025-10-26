"""RSS feed parsing and monitoring service."""

import re
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Optional, Dict, Any, Set
from urllib.parse import urljoin, urlparse

import requests
from pydantic import ValidationError, HttpUrl

from ..models.podcast import Episode, PodcastMetadata
from ..exceptions import PodKnowError


class RSSParsingError(PodKnowError):
    """Raised when RSS feed parsing fails."""
    pass


class RSSFeedParser:
    """Parses RSS feeds and extracts episode information."""
    
    def __init__(self, timeout: int = 30, user_agent: str = None):
        """Initialize RSS feed parser.
        
        Args:
            timeout: Request timeout in seconds
            user_agent: User agent string for requests
        """
        self.timeout = timeout
        self.user_agent = user_agent or "PodKnow/1.0 (Podcast Transcription Tool)"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.user_agent,
            'Accept': 'application/rss+xml, application/xml, text/xml, */*'
        })
    
    def fetch_feed(self, rss_url: str) -> str:
        """Fetch RSS feed content from URL.
        
        Args:
            rss_url: RSS feed URL
            
        Returns:
            Raw RSS feed content
            
        Raises:
            RSSParsingError: If feed cannot be fetched
        """
        try:
            response = self.session.get(rss_url, timeout=self.timeout)
            response.raise_for_status()
            
            # Check content type
            content_type = response.headers.get('content-type', '').lower()
            if not any(ct in content_type for ct in ['xml', 'rss']):
                # Still try to parse, some feeds have incorrect content-type
                pass
            
            return response.text
            
        except requests.RequestException as e:
            raise RSSParsingError(f"Failed to fetch RSS feed from {rss_url}: {e}")
    
    def parse_feed(self, rss_content: str, podcast_id: str) -> tuple[PodcastMetadata, List[Episode]]:
        """Parse RSS feed content and extract podcast metadata and episodes.
        
        Args:
            rss_content: Raw RSS feed content
            podcast_id: Subscription ID for the podcast
            
        Returns:
            Tuple of (podcast_metadata, episodes_list)
            
        Raises:
            RSSParsingError: If feed parsing fails
        """
        try:
            # Parse XML
            root = ET.fromstring(rss_content)
            
            # Find channel element
            channel = root.find('.//channel')
            if channel is None:
                raise RSSParsingError("No channel element found in RSS feed")
            
            # Extract podcast metadata
            metadata = self._extract_podcast_metadata(channel)
            
            # Extract episodes
            episodes = self._extract_episodes(channel, podcast_id)
            
            return metadata, episodes
            
        except ET.ParseError as e:
            raise RSSParsingError(f"Invalid XML in RSS feed: {e}")
        except Exception as e:
            raise RSSParsingError(f"Failed to parse RSS feed: {e}")
    
    def _extract_podcast_metadata(self, channel: ET.Element) -> PodcastMetadata:
        """Extract podcast metadata from channel element.
        
        Args:
            channel: RSS channel element
            
        Returns:
            PodcastMetadata object
        """
        def get_text(element_name: str, default: str = "") -> str:
            elem = channel.find(element_name)
            return elem.text.strip() if elem is not None and elem.text else default
        
        def get_url(element_name: str) -> Optional[HttpUrl]:
            elem = channel.find(element_name)
            if elem is not None and elem.text:
                try:
                    return HttpUrl(elem.text.strip())
                except ValidationError:
                    pass
            return None
        
        # Extract basic metadata
        title = get_text('title')
        description = get_text('description')
        
        # Try to get author from various possible elements
        author = (
            get_text('itunes:author') or
            get_text('author') or
            get_text('managingEditor') or
            get_text('webMaster') or
            "Unknown"
        )
        
        # Extract category
        category_elem = channel.find('.//itunes:category')
        category = "General"
        if category_elem is not None:
            category = category_elem.get('text', 'General')
        else:
            # Try regular category
            category_elem = channel.find('category')
            if category_elem is not None and category_elem.text:
                category = category_elem.text.strip()
        
        # Extract language
        language = get_text('language', 'en')
        
        # Extract artwork URL
        artwork_url = None
        # Try iTunes image first
        itunes_image = channel.find('.//itunes:image')
        if itunes_image is not None:
            artwork_url = get_url_from_attr(itunes_image, 'href')
        
        # Try regular image
        if not artwork_url:
            image_elem = channel.find('.//image/url')
            if image_elem is not None and image_elem.text:
                try:
                    artwork_url = HttpUrl(image_elem.text.strip())
                except ValidationError:
                    pass
        
        # Extract website URL
        website_url = get_url('link')
        
        # Extract last build date
        last_build_date = None
        build_date_text = get_text('lastBuildDate')
        if build_date_text:
            last_build_date = self._parse_date(build_date_text)
        
        return PodcastMetadata(
            title=title,
            author=author,
            description=description,
            category=category,
            language=language,
            artwork_url=artwork_url,
            website_url=website_url,
            last_build_date=last_build_date
        )
    
    def _extract_episodes(self, channel: ET.Element, podcast_id: str) -> List[Episode]:
        """Extract episodes from RSS channel.
        
        Args:
            channel: RSS channel element
            podcast_id: Subscription ID for the podcast
            
        Returns:
            List of Episode objects
        """
        episodes = []
        
        for item in channel.findall('.//item'):
            try:
                episode = self._parse_episode(item, podcast_id)
                if episode:
                    episodes.append(episode)
            except Exception as e:
                # Log warning but continue processing other episodes
                print(f"Warning: Failed to parse episode: {e}")
                continue
        
        return episodes
    
    def _parse_episode(self, item: ET.Element, podcast_id: str) -> Optional[Episode]:
        """Parse a single episode from RSS item.
        
        Args:
            item: RSS item element
            podcast_id: Subscription ID for the podcast
            
        Returns:
            Episode object or None if parsing fails
        """
        def get_text(element_name: str, default: str = "") -> str:
            elem = item.find(element_name)
            return elem.text.strip() if elem is not None and elem.text else default
        
        # Extract basic episode info
        title = get_text('title')
        description = get_text('description')
        
        if not title:
            return None  # Skip episodes without titles
        
        # Extract media URL
        media_url = None
        media_type = None
        file_size = None
        
        # Look for enclosure (most common)
        enclosure = item.find('enclosure')
        if enclosure is not None:
            media_url = enclosure.get('url')
            media_type = enclosure.get('type')
            try:
                file_size = int(enclosure.get('length', 0))
            except (ValueError, TypeError):
                file_size = None
        
        # If no enclosure, try other elements
        if not media_url:
            # Try iTunes or other media elements
            for media_elem in item.findall('.//*[@url]'):
                url = media_elem.get('url')
                if url and self._is_audio_video_url(url):
                    media_url = url
                    break
        
        if not media_url:
            return None  # Skip episodes without media
        
        try:
            validated_media_url = HttpUrl(media_url)
        except ValidationError:
            return None  # Skip episodes with invalid URLs
        
        # Extract publication date
        pub_date_text = get_text('pubDate')
        publication_date = self._parse_date(pub_date_text) or datetime.now()
        
        # Extract duration
        duration = 0
        duration_text = get_text('itunes:duration')
        if duration_text:
            duration = self._parse_duration(duration_text)
        
        # Extract language (fallback to English)
        language = get_text('language', 'en')
        
        # Generate episode ID from URL or title
        episode_id = self._generate_episode_id(media_url, title, publication_date)
        
        return Episode(
            title=title,
            description=description,
            media_url=validated_media_url,
            publication_date=publication_date,
            duration=duration,
            language=language,
            podcast_id=podcast_id,
            episode_id=episode_id,
            file_size=file_size,
            media_type=media_type
        )
    
    def _parse_date(self, date_string: str) -> Optional[datetime]:
        """Parse various date formats commonly found in RSS feeds.
        
        Args:
            date_string: Date string to parse
            
        Returns:
            Parsed datetime or None if parsing fails
        """
        if not date_string:
            return None
        
        # Common RSS date formats
        formats = [
            '%a, %d %b %Y %H:%M:%S %z',  # RFC 2822
            '%a, %d %b %Y %H:%M:%S %Z',  # RFC 2822 with timezone name
            '%a, %d %b %Y %H:%M:%S',     # RFC 2822 without timezone
            '%Y-%m-%dT%H:%M:%S%z',       # ISO 8601 with timezone
            '%Y-%m-%dT%H:%M:%S',         # ISO 8601 without timezone
            '%Y-%m-%d %H:%M:%S',         # Simple format
            '%Y-%m-%d',                  # Date only
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_string.strip(), fmt)
            except ValueError:
                continue
        
        return None
    
    def _parse_duration(self, duration_string: str) -> int:
        """Parse duration string to seconds.
        
        Args:
            duration_string: Duration in various formats (HH:MM:SS, MM:SS, seconds)
            
        Returns:
            Duration in seconds
        """
        if not duration_string:
            return 0
        
        duration_string = duration_string.strip()
        
        # Try parsing as seconds first
        try:
            return int(float(duration_string))
        except ValueError:
            pass
        
        # Try parsing as time format (HH:MM:SS or MM:SS)
        time_parts = duration_string.split(':')
        if len(time_parts) == 2:  # MM:SS
            try:
                minutes, seconds = map(int, time_parts)
                return minutes * 60 + seconds
            except ValueError:
                pass
        elif len(time_parts) == 3:  # HH:MM:SS
            try:
                hours, minutes, seconds = map(int, time_parts)
                return hours * 3600 + minutes * 60 + seconds
            except ValueError:
                pass
        
        return 0
    
    def _generate_episode_id(self, media_url: str, title: str, pub_date: datetime) -> str:
        """Generate a unique episode ID.
        
        Args:
            media_url: Episode media URL
            title: Episode title
            pub_date: Publication date
            
        Returns:
            Unique episode identifier
        """
        import hashlib
        
        # Create a hash from URL, title, and date
        content = f"{media_url}|{title}|{pub_date.isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def _is_audio_video_url(self, url: str) -> bool:
        """Check if URL appears to be audio or video content.
        
        Args:
            url: URL to check
            
        Returns:
            True if URL appears to be media content
        """
        audio_video_extensions = {
            '.mp3', '.m4a', '.wav', '.ogg', '.aac', '.flac',
            '.mp4', '.m4v', '.avi', '.mov', '.wmv', '.webm'
        }
        
        parsed = urlparse(url.lower())
        path = parsed.path
        
        return any(path.endswith(ext) for ext in audio_video_extensions)
    
    def detect_new_episodes(self, current_episodes: List[Episode], stored_episode_ids: Set[str]) -> List[Episode]:
        """Detect new episodes by comparing against stored episode IDs.
        
        Args:
            current_episodes: Episodes from current RSS feed parse
            stored_episode_ids: Set of previously processed episode IDs
            
        Returns:
            List of new episodes
        """
        new_episodes = []
        
        for episode in current_episodes:
            if episode.episode_id not in stored_episode_ids:
                new_episodes.append(episode)
        
        return new_episodes
    
    def validate_feed(self, rss_content: str) -> Dict[str, Any]:
        """Validate RSS feed and return validation results.
        
        Args:
            rss_content: Raw RSS feed content
            
        Returns:
            Dictionary with validation results
        """
        validation_result = {
            'valid': False,
            'errors': [],
            'warnings': [],
            'episode_count': 0,
            'has_media': False
        }
        
        try:
            root = ET.fromstring(rss_content)
            channel = root.find('.//channel')
            
            if channel is None:
                validation_result['errors'].append("No channel element found")
                return validation_result
            
            # Check required elements
            if not channel.find('title'):
                validation_result['errors'].append("Missing podcast title")
            
            if not channel.find('description'):
                validation_result['errors'].append("Missing podcast description")
            
            # Count episodes and check for media
            items = channel.findall('.//item')
            validation_result['episode_count'] = len(items)
            
            media_count = 0
            for item in items:
                if item.find('enclosure') is not None:
                    media_count += 1
            
            validation_result['has_media'] = media_count > 0
            
            if media_count == 0:
                validation_result['warnings'].append("No episodes with media enclosures found")
            elif media_count < len(items):
                validation_result['warnings'].append(f"Only {media_count}/{len(items)} episodes have media")
            
            # If we got here, basic structure is valid
            validation_result['valid'] = len(validation_result['errors']) == 0
            
        except ET.ParseError as e:
            validation_result['errors'].append(f"Invalid XML: {e}")
        except Exception as e:
            validation_result['errors'].append(f"Validation error: {e}")
        
        return validation_result


def get_url_from_attr(element: ET.Element, attr_name: str) -> Optional[HttpUrl]:
    """Helper function to get URL from element attribute.
    
    Args:
        element: XML element
        attr_name: Attribute name
        
    Returns:
        HttpUrl if valid, None otherwise
    """
    url = element.get(attr_name)
    if url:
        try:
            return HttpUrl(url.strip())
        except ValidationError:
            pass
    return None