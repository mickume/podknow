"""Subscription monitoring service for detecting new episodes."""

from datetime import datetime
from typing import List, Dict, Set, Optional, Tuple
import json
import os
from pathlib import Path

from .subscription_manager import SubscriptionManager, SubscriptionError
from .rss_parser import RSSFeedParser, RSSParsingError
from ..models.podcast import Episode, Subscription
from ..exceptions import PodKnowError


class MonitoringError(PodKnowError):
    """Raised when subscription monitoring fails."""
    pass


class SubscriptionMonitor:
    """Monitors podcast subscriptions for new episodes."""
    
    def __init__(self, 
                 subscription_manager: SubscriptionManager,
                 rss_parser: Optional[RSSFeedParser] = None,
                 episode_cache_path: Optional[str] = None):
        """Initialize subscription monitor.
        
        Args:
            subscription_manager: SubscriptionManager instance
            rss_parser: RSSFeedParser instance, creates default if None
            episode_cache_path: Path to episode cache file
        """
        self.subscription_manager = subscription_manager
        self.rss_parser = rss_parser or RSSFeedParser()
        
        if episode_cache_path is None:
            episode_cache_path = os.path.expanduser("~/.podknow/episode_cache.json")
        
        self.episode_cache_path = Path(episode_cache_path)
        self._episode_cache: Dict[str, Set[str]] = {}  # podcast_id -> set of episode_ids
        self._ensure_cache_directory()
        self._load_episode_cache()
    
    def _ensure_cache_directory(self) -> None:
        """Ensure the cache directory exists."""
        self.episode_cache_path.parent.mkdir(parents=True, exist_ok=True)
    
    def _load_episode_cache(self) -> None:
        """Load episode cache from JSON file."""
        if not self.episode_cache_path.exists():
            self._episode_cache = {}
            return
        
        try:
            with open(self.episode_cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Convert lists back to sets
            self._episode_cache = {
                podcast_id: set(episode_ids) 
                for podcast_id, episode_ids in data.items()
            }
            
        except (json.JSONDecodeError, FileNotFoundError) as e:
            raise MonitoringError(f"Failed to load episode cache: {e}")
        except Exception as e:
            raise MonitoringError(f"Unexpected error loading episode cache: {e}")
    
    def _save_episode_cache(self) -> None:
        """Save episode cache to JSON file."""
        try:
            # Convert sets to lists for JSON serialization
            data = {
                podcast_id: list(episode_ids)
                for podcast_id, episode_ids in self._episode_cache.items()
            }
            
            # Write atomically
            temp_path = self.episode_cache_path.with_suffix('.tmp')
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            temp_path.replace(self.episode_cache_path)
            
        except Exception as e:
            raise MonitoringError(f"Failed to save episode cache: {e}")
    
    def check_subscription_for_new_episodes(self, subscription_id: str) -> List[Episode]:
        """Check a single subscription for new episodes.
        
        Args:
            subscription_id: Subscription ID to check
            
        Returns:
            List of new episodes
            
        Raises:
            MonitoringError: If checking fails
        """
        subscription = self.subscription_manager.get_subscription(subscription_id)
        if not subscription:
            raise MonitoringError(f"Subscription {subscription_id} not found")
        
        try:
            # Fetch and parse RSS feed
            rss_content = self.rss_parser.fetch_feed(str(subscription.rss_url))
            metadata, current_episodes = self.rss_parser.parse_feed(rss_content, subscription_id)
            
            # Get stored episode IDs for this subscription
            stored_episode_ids = self._episode_cache.get(subscription_id, set())
            
            # Detect new episodes
            new_episodes = self.rss_parser.detect_new_episodes(current_episodes, stored_episode_ids)
            
            # Update cache with all current episode IDs
            current_episode_ids = {ep.episode_id for ep in current_episodes if ep.episode_id}
            self._episode_cache[subscription_id] = current_episode_ids
            
            # Update subscription metadata
            self.subscription_manager.update_subscription(
                subscription_id,
                last_checked=datetime.now(),
                metadata=metadata
            )
            
            # Save cache
            self._save_episode_cache()
            
            return new_episodes
            
        except RSSParsingError as e:
            raise MonitoringError(f"Failed to parse RSS feed for {subscription.title}: {e}")
        except SubscriptionError as e:
            raise MonitoringError(f"Failed to update subscription {subscription.title}: {e}")
        except Exception as e:
            raise MonitoringError(f"Unexpected error checking {subscription.title}: {e}")
    
    def check_all_subscriptions_for_new_episodes(self) -> Dict[str, List[Episode]]:
        """Check all subscriptions for new episodes.
        
        Returns:
            Dictionary mapping subscription_id to list of new episodes
            
        Raises:
            MonitoringError: If checking fails for critical subscriptions
        """
        subscriptions = self.subscription_manager.get_subscriptions()
        results = {}
        errors = []
        
        for subscription in subscriptions:
            try:
                new_episodes = self.check_subscription_for_new_episodes(subscription.id)
                results[subscription.id] = new_episodes
                
                if new_episodes:
                    print(f"Found {len(new_episodes)} new episodes for {subscription.title}")
                
            except MonitoringError as e:
                error_msg = f"Failed to check {subscription.title}: {e}"
                errors.append(error_msg)
                print(f"Warning: {error_msg}")
                results[subscription.id] = []  # Empty list for failed checks
        
        if errors:
            # Log errors but don't fail completely unless all subscriptions failed
            if len(errors) == len(subscriptions):
                raise MonitoringError(f"All subscription checks failed: {'; '.join(errors)}")
        
        return results
    
    def get_cached_episode_ids(self, subscription_id: str) -> Set[str]:
        """Get cached episode IDs for a subscription.
        
        Args:
            subscription_id: Subscription ID
            
        Returns:
            Set of cached episode IDs
        """
        return self._episode_cache.get(subscription_id, set()).copy()
    
    def add_episodes_to_cache(self, subscription_id: str, episode_ids: List[str]) -> None:
        """Add episode IDs to cache for a subscription.
        
        Args:
            subscription_id: Subscription ID
            episode_ids: List of episode IDs to add
        """
        if subscription_id not in self._episode_cache:
            self._episode_cache[subscription_id] = set()
        
        self._episode_cache[subscription_id].update(episode_ids)
        self._save_episode_cache()
    
    def remove_subscription_from_cache(self, subscription_id: str) -> None:
        """Remove subscription from episode cache.
        
        Args:
            subscription_id: Subscription ID to remove
        """
        if subscription_id in self._episode_cache:
            del self._episode_cache[subscription_id]
            self._save_episode_cache()
    
    def validate_subscription_feed(self, subscription_id: str) -> Dict[str, any]:
        """Validate RSS feed for a subscription.
        
        Args:
            subscription_id: Subscription ID
            
        Returns:
            Validation results dictionary
            
        Raises:
            MonitoringError: If validation fails
        """
        subscription = self.subscription_manager.get_subscription(subscription_id)
        if not subscription:
            raise MonitoringError(f"Subscription {subscription_id} not found")
        
        try:
            rss_content = self.rss_parser.fetch_feed(str(subscription.rss_url))
            return self.rss_parser.validate_feed(rss_content)
            
        except RSSParsingError as e:
            raise MonitoringError(f"Failed to validate feed for {subscription.title}: {e}")
    
    def get_subscription_statistics(self) -> Dict[str, any]:
        """Get statistics about subscriptions and cached episodes.
        
        Returns:
            Statistics dictionary
        """
        subscriptions = self.subscription_manager.get_subscriptions()
        
        total_subscriptions = len(subscriptions)
        total_cached_episodes = sum(len(episodes) for episodes in self._episode_cache.values())
        
        # Calculate average episodes per subscription
        avg_episodes = total_cached_episodes / total_subscriptions if total_subscriptions > 0 else 0
        
        # Find subscription with most episodes
        max_episodes = 0
        max_subscription = None
        for subscription in subscriptions:
            episode_count = len(self._episode_cache.get(subscription.id, set()))
            if episode_count > max_episodes:
                max_episodes = episode_count
                max_subscription = subscription.title
        
        return {
            'total_subscriptions': total_subscriptions,
            'total_cached_episodes': total_cached_episodes,
            'average_episodes_per_subscription': round(avg_episodes, 1),
            'max_episodes': max_episodes,
            'subscription_with_most_episodes': max_subscription,
            'cache_file_size': self.episode_cache_path.stat().st_size if self.episode_cache_path.exists() else 0
        }
    
    def cleanup_stale_cache_entries(self) -> int:
        """Remove cache entries for subscriptions that no longer exist.
        
        Returns:
            Number of cache entries removed
        """
        current_subscription_ids = {sub.id for sub in self.subscription_manager.get_subscriptions()}
        cached_subscription_ids = set(self._episode_cache.keys())
        
        stale_ids = cached_subscription_ids - current_subscription_ids
        
        for stale_id in stale_ids:
            del self._episode_cache[stale_id]
        
        if stale_ids:
            self._save_episode_cache()
        
        return len(stale_ids)