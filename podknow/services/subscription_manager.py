"""Subscription management service for local podcast subscriptions."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set
from uuid import uuid4

from pydantic import ValidationError, HttpUrl

from ..models.podcast import Subscription, PodcastMetadata, Episode
from ..exceptions import PodKnowError


class SubscriptionError(PodKnowError):
    """Raised when subscription operations fail."""
    pass


class SubscriptionManager:
    """Manages local podcast subscriptions with JSON file persistence."""
    
    def __init__(self, storage_path: Optional[str] = None):
        """Initialize subscription manager.
        
        Args:
            storage_path: Path to subscriptions JSON file. Defaults to ~/.podknow/subscriptions.json
        """
        if storage_path is None:
            storage_path = os.path.expanduser("~/.podknow/subscriptions.json")
        
        self.storage_path = Path(storage_path)
        self._subscriptions: Dict[str, Subscription] = {}
        self._ensure_storage_directory()
        self._load_subscriptions()
    
    def _ensure_storage_directory(self) -> None:
        """Ensure the storage directory exists."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
    
    def _load_subscriptions(self) -> None:
        """Load subscriptions from JSON file."""
        if not self.storage_path.exists():
            self._subscriptions = {}
            return
        
        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Validate and migrate data if needed
            self._subscriptions = self._validate_and_migrate_data(data)
            
        except (json.JSONDecodeError, FileNotFoundError) as e:
            raise SubscriptionError(f"Failed to load subscriptions: {e}")
        except Exception as e:
            raise SubscriptionError(f"Unexpected error loading subscriptions: {e}")
    
    def _validate_and_migrate_data(self, data: Dict) -> Dict[str, Subscription]:
        """Validate and migrate subscription data.
        
        Args:
            data: Raw data from JSON file
            
        Returns:
            Dictionary of validated subscriptions
            
        Raises:
            SubscriptionError: If data validation fails
        """
        subscriptions = {}
        
        # Handle different data formats for migration
        if isinstance(data, dict):
            if "subscriptions" in data:
                # New format: {"subscriptions": {...}, "version": "1.0"}
                subscription_data = data["subscriptions"]
            else:
                # Legacy format: direct subscription dictionary
                subscription_data = data
        else:
            raise SubscriptionError("Invalid subscription data format")
        
        for sub_id, sub_data in subscription_data.items():
            try:
                # Convert datetime strings back to datetime objects
                if isinstance(sub_data.get("last_checked"), str):
                    sub_data["last_checked"] = datetime.fromisoformat(sub_data["last_checked"])
                
                # Validate subscription data
                subscription = Subscription(**sub_data)
                subscriptions[sub_id] = subscription
                
            except ValidationError as e:
                raise SubscriptionError(f"Invalid subscription data for {sub_id}: {e}")
            except ValueError as e:
                raise SubscriptionError(f"Invalid datetime format for {sub_id}: {e}")
        
        return subscriptions
    
    def _save_subscriptions(self) -> None:
        """Save subscriptions to JSON file."""
        try:
            # Prepare data for JSON serialization
            data = {
                "version": "1.0",
                "subscriptions": {
                    sub_id: sub.dict() for sub_id, sub in self._subscriptions.items()
                }
            }
            
            # Write atomically by writing to temp file first
            temp_path = self.storage_path.with_suffix('.tmp')
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            
            # Atomic move
            temp_path.replace(self.storage_path)
            
        except Exception as e:
            raise SubscriptionError(f"Failed to save subscriptions: {e}")
    
    def add_subscription(self, rss_url: str, metadata: PodcastMetadata) -> str:
        """Add a new podcast subscription.
        
        Args:
            rss_url: RSS feed URL
            metadata: Podcast metadata
            
        Returns:
            Subscription ID
            
        Raises:
            SubscriptionError: If subscription already exists or validation fails
        """
        try:
            # Validate RSS URL
            validated_url = HttpUrl(rss_url)
            
            # Check if subscription already exists
            for sub in self._subscriptions.values():
                if sub.rss_url == validated_url:
                    raise SubscriptionError(f"Subscription already exists for {rss_url}")
            
            # Generate unique ID
            subscription_id = str(uuid4())
            
            # Create subscription
            subscription = Subscription(
                id=subscription_id,
                title=metadata.title,
                rss_url=validated_url,
                last_checked=datetime.now(),
                episode_count=0,
                metadata=metadata
            )
            
            # Store and save
            self._subscriptions[subscription_id] = subscription
            self._save_subscriptions()
            
            return subscription_id
            
        except ValidationError as e:
            raise SubscriptionError(f"Invalid subscription data: {e}")
        except Exception as e:
            raise SubscriptionError(f"Failed to add subscription: {e}")
    
    def remove_subscription(self, subscription_id: str) -> bool:
        """Remove a podcast subscription.
        
        Args:
            subscription_id: Subscription ID to remove
            
        Returns:
            True if subscription was removed, False if not found
            
        Raises:
            SubscriptionError: If removal fails
        """
        if subscription_id not in self._subscriptions:
            return False
        
        try:
            del self._subscriptions[subscription_id]
            self._save_subscriptions()
            return True
            
        except Exception as e:
            raise SubscriptionError(f"Failed to remove subscription: {e}")
    
    def get_subscription(self, subscription_id: str) -> Optional[Subscription]:
        """Get a subscription by ID.
        
        Args:
            subscription_id: Subscription ID
            
        Returns:
            Subscription if found, None otherwise
        """
        return self._subscriptions.get(subscription_id)
    
    def get_subscriptions(self) -> List[Subscription]:
        """Get all subscriptions.
        
        Returns:
            List of all subscriptions
        """
        return list(self._subscriptions.values())
    
    def update_subscription(self, subscription_id: str, **updates) -> bool:
        """Update subscription fields.
        
        Args:
            subscription_id: Subscription ID
            **updates: Fields to update
            
        Returns:
            True if updated, False if subscription not found
            
        Raises:
            SubscriptionError: If update fails
        """
        if subscription_id not in self._subscriptions:
            return False
        
        try:
            subscription = self._subscriptions[subscription_id]
            
            # Create updated subscription
            updated_data = subscription.dict()
            updated_data.update(updates)
            
            # Validate updated data
            updated_subscription = Subscription(**updated_data)
            
            # Store and save
            self._subscriptions[subscription_id] = updated_subscription
            self._save_subscriptions()
            
            return True
            
        except ValidationError as e:
            raise SubscriptionError(f"Invalid update data: {e}")
        except Exception as e:
            raise SubscriptionError(f"Failed to update subscription: {e}")
    
    def update_last_checked(self, subscription_id: str, timestamp: Optional[datetime] = None) -> bool:
        """Update the last checked timestamp for a subscription.
        
        Args:
            subscription_id: Subscription ID
            timestamp: Timestamp to set, defaults to now
            
        Returns:
            True if updated, False if subscription not found
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        return self.update_subscription(subscription_id, last_checked=timestamp)
    
    def increment_episode_count(self, subscription_id: str, count: int = 1) -> bool:
        """Increment the episode count for a subscription.
        
        Args:
            subscription_id: Subscription ID
            count: Number to increment by
            
        Returns:
            True if updated, False if subscription not found
        """
        subscription = self.get_subscription(subscription_id)
        if not subscription:
            return False
        
        new_count = subscription.episode_count + count
        return self.update_subscription(subscription_id, episode_count=new_count)
    
    def find_by_rss_url(self, rss_url: str) -> Optional[Subscription]:
        """Find subscription by RSS URL.
        
        Args:
            rss_url: RSS feed URL to search for
            
        Returns:
            Subscription if found, None otherwise
        """
        try:
            validated_url = HttpUrl(rss_url)
            for subscription in self._subscriptions.values():
                if subscription.rss_url == validated_url:
                    return subscription
        except ValidationError:
            pass
        
        return None
    
    def get_subscription_count(self) -> int:
        """Get total number of subscriptions.
        
        Returns:
            Number of subscriptions
        """
        return len(self._subscriptions)
    
    def get_subscriptions_by_category(self, category: str) -> List[Subscription]:
        """Get subscriptions filtered by category.
        
        Args:
            category: Category to filter by
            
        Returns:
            List of subscriptions in the specified category
        """
        return [
            sub for sub in self._subscriptions.values()
            if sub.metadata.category.lower() == category.lower()
        ]
    
    def get_stale_subscriptions(self, hours: int = 24) -> List[Subscription]:
        """Get subscriptions that haven't been checked recently.
        
        Args:
            hours: Number of hours to consider stale
            
        Returns:
            List of stale subscriptions
        """
        from datetime import timedelta
        
        cutoff = datetime.now() - timedelta(hours=hours)
        return [
            sub for sub in self._subscriptions.values()
            if sub.last_checked < cutoff
        ]