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

    def get_junk_filters_with_type(self) -> List[Dict]:
        """Get list of all junk filters with their type."""
        try:
            result = self.client.table('junk_filters').select('pattern,pattern_type').execute()

            logger.info(f"Retrieved {len(result.data)} junk filters with type")
            return result.data

        except Exception as e:
            logger.error(f"Failed to get junk filters with type: {e}")
            return []

    def add_newsletter_sender(self, email: str, name: str = None) -> bool:
        """Add a newsletter sender to track."""
        try:
            data = {
                'email': email.lower().strip(),
                'name': name or email.split('@')[0]
            }

            result = self.client.table('newsletter_senders').upsert(
                data,
                on_conflict='email'
            ).execute()

            logger.info(f"Added newsletter sender: {email}")
            return True

        except Exception as e:
            logger.error(f"Failed to add newsletter sender: {e}")
            return False

    def remove_newsletter_sender(self, email: str) -> bool:
        """Remove a newsletter sender."""
        try:
            result = self.client.table('newsletter_senders').delete().eq(
                'email', email.lower().strip()
            ).execute()

            logger.info(f"Removed newsletter sender: {email}")
            return True

        except Exception as e:
            logger.error(f"Failed to remove newsletter sender: {e}")
            return False

    def get_newsletter_senders(self) -> List[Dict]:
        """Get list of all newsletter senders."""
        try:
            result = self.client.table('newsletter_senders').select('*').order('created_at', desc=True).execute()

            logger.info(f"Retrieved {len(result.data)} newsletter senders")
            return result.data

        except Exception as e:
            logger.error(f"Failed to get newsletter senders: {e}")
            return []

    def get_source_scores(self) -> Dict[str, int]:
        """
        Get aggregate vote scores by source.
        Returns dict of source -> net score (upvotes - downvotes).
        """
        try:
            result = self.client.table('article_interactions').select(
                'article_source, vote'
            ).neq('vote', 0).execute()

            scores = {}
            for row in result.data:
                source = row.get('article_source', '').lower().strip()
                if source:
                    vote = row.get('vote', 0)
                    scores[source] = scores.get(source, 0) + vote

            logger.info(f"Calculated scores for {len(scores)} sources")
            return scores

        except Exception as e:
            logger.error(f"Failed to get source scores: {e}")
            return {}

    def get_downvoted_sources(self, threshold: int = -2) -> List[str]:
        """
        Get list of sources with net negative votes below threshold.
        These sources will be deprioritized.
        """
        scores = self.get_source_scores()
        return [source for source, score in scores.items() if score <= threshold]

    def get_downvoted_keywords(self) -> List[str]:
        """
        Extract keywords from downvoted article titles.
        These will be used to filter similar articles.
        """
        try:
            result = self.client.table('article_interactions').select(
                'article_title'
            ).eq('vote', -1).execute()

            # Extract significant words from downvoted titles
            import re
            stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                         'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
                         'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
                         'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that',
                         'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they',
                         'what', 'which', 'who', 'whom', 'how', 'why', 'when', 'where',
                         'your', 'our', 'their', 'its', 'my', 'his', 'her', 'new', 'now'}

            word_counts = {}
            for row in result.data:
                title = row.get('article_title', '').lower()
                # Extract words (3+ chars, not numbers)
                words = re.findall(r'[a-z]{3,}', title)
                for word in words:
                    if word not in stop_words:
                        word_counts[word] = word_counts.get(word, 0) + 1

            # Return words that appear in 2+ downvoted articles (indicates pattern)
            keywords = [word for word, count in word_counts.items() if count >= 2]
            logger.info(f"Found {len(keywords)} downvoted keywords: {keywords[:10]}")
            return keywords

        except Exception as e:
            logger.error(f"Failed to get downvoted keywords: {e}")
            return []
