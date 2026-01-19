import requests
from bs4 import BeautifulSoup
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from typing import List, Dict, Set
import logging
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ArticleProcessor:
    """Handles article extraction, processing, and deduplication."""

    def __init__(self, similarity_threshold: float = 0.7):
        """
        Initialize the article processor.

        Args:
            similarity_threshold: Threshold for considering articles as duplicates (0-1)
        """
        self.similarity_threshold = similarity_threshold

    def extract_article_content(self, url: str) -> Dict:
        """
        Extract article content from a URL using BeautifulSoup.

        Returns:
            Dictionary with title, text, authors, publish_date, top_image
        """
        article_data = {
            'url': url,
            'title': '',
            'text': '',
            'authors': [],
            'publish_date': None,
            'top_image': '',
            'extraction_success': False
        }

        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract title
            title_tag = soup.find('title')
            if title_tag:
                article_data['title'] = title_tag.get_text().strip()

            # Extract main content
            article_tags = soup.find_all(['article', 'main', 'div'],
                                        class_=re.compile(r'article|content|post|story', re.I))

            text_content = ""
            if article_tags:
                for tag in article_tags:
                    paragraphs = tag.find_all('p')
                    text_content += ' '.join([p.get_text() for p in paragraphs])
                    if len(text_content) > 200:
                        break

            article_data['text'] = text_content.strip()
            article_data['extraction_success'] = bool(text_content)

            logger.info(f"Extracted article: {article_data['title']}")

        except Exception as e:
            logger.error(f"Extraction failed for {url}: {e}")

        return article_data

    

    def extract_articles_from_newsletters(self, newsletters: List[Dict]) -> List[Dict]:
        """
        Extract articles from newsletter URLs.

        Args:
            newsletters: List of newsletter dictionaries with URLs

        Returns:
            List of extracted article dictionaries
        """
        articles = []
        seen_urls = set()

        for newsletter in newsletters:
            urls = newsletter.get('urls', [])

            for url in urls:
                # Skip if we've already processed this URL
                if url in seen_urls:
                    continue

                seen_urls.add(url)

                # Extract article content
                article_data = self.extract_article_content(url)

                if article_data['extraction_success']:
                    # Filter out junk pages by title
                    title_lower = article_data['title'].lower()
                    
                    junk_title_patterns = [
                        'contact us', 'privacy policy', 'cookie notice', 'cookie policy',
                        'sign in', 'log in', 'login', 'register', 'registration',
                        'linkedin', 'facebook', 'instagram', 'twitter', 'youtube',
                        'app store', 'google play', 'terms of use', 'terms and conditions',
                        'subscribe', 'unsubscribe', 'join now', 'newsletter',
                        'explore hbr', 'about hbr', 'follow hbr', 'manage my account',
                        'view all', 'see all', 'browse', 'home page',
                        'advertising', 'partnerships', 'solutions for', 'data & visuals'
                    ]
                    
                    # Skip if title matches junk patterns
                    if any(pattern in title_lower for pattern in junk_title_patterns):
                        continue
                    
                    # Skip if title is too short (likely navigation)
                    if len(article_data['title']) < 15:
                        continue
                    
                    # Add newsletter metadata
                    article_data['newsletter_sender'] = newsletter.get('sender', '')
                    article_data['newsletter_subject'] = newsletter.get('subject', '')

                    articles.append(article_data)

        logger.info(f"Extracted {len(articles)} articles from newsletters")
        return articles

    def calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate cosine similarity between two text strings.

        Returns:
            Similarity score between 0 and 1
        """
        if not text1 or not text2:
            return 0.0

        try:
            vectorizer = TfidfVectorizer(stop_words='english', max_features=1000)
            tfidf_matrix = vectorizer.fit_transform([text1, text2])
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            return similarity
        except:
            return 0.0

    def title_similarity(self, title1: str, title2: str) -> float:
        """
        Calculate similarity between two titles using simple word overlap.
        """
        if not title1 or not title2:
            return 0.0

        # Normalize and tokenize
        words1 = set(title1.lower().split())
        words2 = set(title2.lower().split())

        # Remove common words
        stop_words = {'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 'of', 'and', 'or', 'but'}
        words1 = words1 - stop_words
        words2 = words2 - stop_words

        if not words1 or not words2:
            return 0.0

        # Calculate Jaccard similarity
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))

        return intersection / union if union > 0 else 0.0

    def deduplicate_articles(self, articles: List[Dict]) -> List[Dict]:
        """
        Remove duplicate articles based on content similarity.

        Returns:
            List of unique articles
        """
        if not articles:
            return []

        unique_articles = []
        duplicate_groups = []  # Track which articles are duplicates

        for i, article in enumerate(articles):
            is_duplicate = False

            for j, unique_article in enumerate(unique_articles):
                # Check title similarity first (faster)
                title_sim = self.title_similarity(article['title'], unique_article['title'])

                if title_sim > 0.6:  # High title similarity
                    is_duplicate = True
                    logger.info(f"Duplicate found (title): '{article['title']}' ~ '{unique_article['title']}'")
                    break

                # Check content similarity if titles are somewhat similar
                if title_sim > 0.3:
                    content_sim = self.calculate_similarity(article['text'], unique_article['text'])

                    if content_sim > self.similarity_threshold:
                        is_duplicate = True
                        logger.info(f"Duplicate found (content sim: {content_sim:.2f}): '{article['title']}'")
                        break

            if not is_duplicate:
                unique_articles.append(article)

        logger.info(f"Deduplication: {len(articles)} -> {len(unique_articles)} articles")
        return unique_articles

    def categorize_articles(self, articles: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Categorize articles by topic using simple keyword matching.

        Returns:
            Dictionary mapping category names to lists of articles
        """
        categories = {
            'Politics': [],
            'Business & Economy': [],
            'Technology': [],
            'Science & Health': [],
            'World News': [],
            'Sports': [],
            'Culture & Entertainment': [],
            'Other': []
        }

        category_keywords = {
            'Politics': ['election', 'congress', 'senate', 'president', 'governor', 'political', 'vote', 'campaign', 'democrat', 'republican'],
            'Business & Economy': ['market', 'stock', 'economy', 'business', 'financial', 'company', 'revenue', 'profit', 'trade', 'economic'],
            'Technology': ['tech', 'ai', 'software', 'app', 'digital', 'cyber', 'computer', 'startup', 'innovation', 'data'],
            'Science & Health': ['study', 'research', 'health', 'medical', 'science', 'climate', 'disease', 'vaccine', 'treatment', 'environment'],
            'World News': ['international', 'global', 'country', 'nation', 'foreign', 'embassy', 'war', 'conflict', 'treaty'],
            'Sports': ['game', 'team', 'player', 'sport', 'championship', 'league', 'score', 'match', 'tournament'],
            'Culture & Entertainment': ['film', 'movie', 'music', 'art', 'book', 'culture', 'entertainment', 'celebrity', 'show', 'theater']
        }

        for article in articles:
            text_to_check = (article['title'] + ' ' + article['text'][:500]).lower()

            categorized = False
            max_score = 0
            best_category = 'Other'

            for category, keywords in category_keywords.items():
                score = sum(1 for keyword in keywords if keyword in text_to_check)
                if score > max_score:
                    max_score = score
                    best_category = category

            if max_score > 0:
                categories[best_category].append(article)
            else:
                categories['Other'].append(article)

        # Remove empty categories
        categories = {k: v for k, v in categories.items() if v}

        return categories
