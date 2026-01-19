"""Supabase database module for article interactions."""
import os
from typing import Dict, List, Optional
import logging
from supabase import create_client, Client

logger = logging.getLogger(__name__)


class SupabaseDB:
    """Handle all Supabase database operations."""

    def __init__(self, url: str, key: str):
        """Initialize Supabase client."""
        self.url = url
        self.key = key
        self.client: Optional[Client] = None
        self._connect()

    def _connect(self):
        """Connect to Supabase."""
        try:
            self.client = create_client(self.url, self.key)
            logger.info("Successfully connected to Supabase")
        except Exception as e:
            logger.error(f"Failed to connect to Supabase: {e}")
            raise

    def save_interaction(self, article_url: str, article_title: str,
                        article_source: str, vote: int = 0,
                        is_read: bool = False) -> bool:
        """
        Save or update article interaction.

        Args:
            article_url: URL of the article
            article_title: Title of the article
            article_source: Newsletter source
            vote: -1 (downvote), 0 (no vote), 1 (upvote)
            is_read: Whether article has been read

        Returns:
            True if successful, False otherwise
        """
        try:
            data = {
                'article_url': article_url,
                'article_title': article_title,
                'article_source': article_source,
                'vote': vote,
                'is_read': is_read
            }

            # Upsert (insert or update if exists)
            result = self.client.table('article_interactions').upsert(
                data,
                on_conflict='article_url'
            ).execute()

            logger.info(f"Saved interaction for: {article_title}")
            return True

        except Exception as e:
            logger.error(f"Failed to save interaction: {e}")
            return False

    def update_vote(self, article_url: str, vote: int) -> bool:
        """Update vote for an article."""
        try:
            result = self.client.table('article_interactions').update({
                'vote': vote
            }).eq('article_url', article_url).execute()

            logger.info(f"Updated vote to {vote} for: {article_url}")
            return True

        except Exception as e:
            logger.error(f"Failed to update vote: {e}")
            return False

    def mark_as_read(self, article_url: str) -> bool:
        """Mark an article as read."""
        try:
            result = self.client.table('article_interactions').update({
                'is_read': True
            }).eq('article_url', article_url).execute()

            logger.info(f"Marked as read: {article_url}")
            return True

        except Exception as e:
            logger.error(f"Failed to mark as read: {e}")
            return False

    def get_read_article_urls(self) -> List[str]:
        """Get list of all article URLs that have been marked as read."""
        try:
            result = self.client.table('article_interactions').select(
                'article_url'
            ).eq('is_read', True).execute()

            urls = [row['article_url'] for row in result.data]
            logger.info(f"Found {len(urls)} read articles")
            return urls

        except Exception as e:
            logger.error(f"Failed to get read articles: {e}")
            return []

    def get_all_interactions(self, limit: int = 100) -> List[Dict]:
        """
        Get all article interactions, ordered by most recent first.

        Args:
            limit: Maximum number of records to return

        Returns:
            List of interaction records
        """
        try:
            result = self.client.table('article_interactions').select(
                '*'
            ).order('created_at', desc=True).limit(limit).execute()

            logger.info(f"Retrieved {len(result.data)} interactions")
            return result.data

        except Exception as e:
            logger.error(f"Failed to get interactions: {e}")
            return []

    def get_interaction(self, article_url: str) -> Optional[Dict]:
        """Get interaction for a specific article."""
        try:
            result = self.client.table('article_interactions').select(
                '*'
            ).eq('article_url', article_url).execute()

            if result.data:
                return result.data[0]
            return None

        except Exception as e:
            logger.error(f"Failed to get interaction: {e}")
            return None

    def add_junk_filter(self, pattern: str, article_url: str = None, article_title: str = None, pattern_type: str = 'title') -> bool:
        """Add a junk filter pattern."""
        try:
            data = {
                'pattern': pattern.lower(),
                'pattern_type': pattern_type,
                'article_url': article_url,
                'article_title': article_title
            }
            
            result = self.client.table('junk_filters').upsert(
                data,
                on_conflict='pattern'
            ).execute()
            
            logger.info(f"Added junk filter: {pattern}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add junk filter: {e}")
            return False
    
    def get_junk_filters(self) -> List[str]:
        """Get list of all junk filter patterns."""
        try:
            result = self.client.table('junk_filters').select('pattern').execute()
            
            patterns = [row['pattern'] for row in result.data]
            logger.info(f"Retrieved {len(patterns)} junk filters")
            return patterns
            
        except Exception as e:
            logger.error(f"Failed to get junk filters: {e}")
            return []
