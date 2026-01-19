import openai
from typing import List, Dict, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ArticleSummarizer:
    """Handles article summarization using OpenAI API."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the summarizer.

        Args:
            api_key: OpenAI API key. If None, will use fallback methods.
        """
        self.api_key = api_key
        self.use_ai = bool(api_key)

        if self.use_ai:
            openai.api_key = api_key

    def summarize_article(self, article: Dict, max_words: int = 100) -> str:
        """
        Generate a summary of an article.

        Args:
            article: Article dictionary with 'title' and 'text'
            max_words: Maximum words in summary

        Returns:
            Summary string
        """
        if self.use_ai:
            return self._summarize_with_ai(article, max_words)
        else:
            return self._summarize_extractive(article, max_words)

    def _summarize_with_ai(self, article: Dict, max_words: int) -> str:
        """Generate summary using OpenAI API."""
        try:
            prompt = f"""Summarize the following news article in {max_words} words or less.
Focus on the key facts and main points.

Title: {article['title']}

Article:
{article['text'][:3000]}

Summary:"""

            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that summarizes news articles concisely."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_words * 2,  # Rough token estimate
                temperature=0.5
            )

            summary = response.choices[0].message.content.strip()
            logger.info(f"AI summary generated for: {article['title']}")
            return summary

        except Exception as e:
            logger.error(f"AI summarization failed: {e}")
            return self._summarize_extractive(article, max_words)

    def _summarize_extractive(self, article: Dict, max_words: int) -> str:
        """
        Generate summary using extractive method (first sentences).
        Fallback when AI is not available.
        """
        text = article.get('text', '')

        if not text:
            return article.get('title', 'No summary available')

        # Split into sentences (simple approach)
        sentences = text.replace('\n', ' ').split('. ')

        # Take first few sentences up to max_words
        summary = ""
        word_count = 0

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            sentence_words = len(sentence.split())

            if word_count + sentence_words <= max_words:
                summary += sentence + ". "
                word_count += sentence_words
            else:
                break

        if not summary:
            # If no sentences fit, just truncate
            words = text.split()[:max_words]
            summary = ' '.join(words) + "..."

        return summary.strip()

    def generate_digest_summary(self, categorized_articles: Dict[str, List[Dict]]) -> str:
        """
        Generate an overall summary of the digest.

        Returns:
            Summary text describing the digest contents
        """
        total_articles = sum(len(articles) for articles in categorized_articles.values())
        categories = list(categorized_articles.keys())

        summary = f"Your daily news digest contains {total_articles} unique articles "
        summary += f"across {len(categories)} categories: {', '.join(categories)}. "

        # Highlight top stories
        if self.use_ai:
            try:
                # Get top articles from first category
                first_category = categories[0]
                top_articles = categorized_articles[first_category][:3]

                titles = [article['title'] for article in top_articles]
                prompt = f"""Based on these top news headlines, write a one-sentence overview of today's key news themes:

{chr(10).join(f'- {title}' for title in titles)}

Overview:"""

                response = openai.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant that summarizes news trends."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=100,
                    temperature=0.5
                )

                overview = response.choices[0].message.content.strip()
                summary += overview

            except Exception as e:
                logger.error(f"Failed to generate overview: {e}")

        return summary

    def summarize_all_articles(self, articles: List[Dict], max_words_per_article: int = 80) -> List[Dict]:
        """
        Add summaries to all articles.

        Args:
            articles: List of article dictionaries
            max_words_per_article: Words per summary

        Returns:
            Articles with 'summary' field added
        """
        for article in articles:
            if 'summary' not in article:
                article['summary'] = self.summarize_article(article, max_words_per_article)

        logger.info(f"Generated summaries for {len(articles)} articles")
        return articles
