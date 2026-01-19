import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import List, Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DigestGenerator:
    """Generates and sends email digests."""

    def __init__(self, smtp_server: str, smtp_port: int, email_address: str, password: str):
        """
        Initialize the digest generator.

        Args:
            smtp_server: SMTP server address
            smtp_port: SMTP server port
            email_address: Sender email address
            password: Email password/app password
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.email_address = email_address
        self.password = password

    def generate_html_digest(self, categorized_articles: Dict[str, List[Dict]],
                            digest_summary: str = "") -> str:
        """
        Generate HTML email content for the digest.

        Args:
            categorized_articles: Dictionary of categories -> articles
            digest_summary: Overall summary text

        Returns:
            HTML string
        """
        current_date = datetime.now().strftime("%B %d, %Y")
        total_articles = sum(len(articles) for articles in categorized_articles.values())

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 700px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: white;
            border-radius: 8px;
            padding: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .header {{
            border-bottom: 3px solid #2c5aa0;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        h1 {{
            color: #2c5aa0;
            margin: 0 0 10px 0;
            font-size: 28px;
        }}
        .date {{
            color: #666;
            font-size: 14px;
        }}
        .summary {{
            background-color: #f8f9fa;
            padding: 15px;
            border-left: 4px solid #2c5aa0;
            margin-bottom: 30px;
            font-style: italic;
            color: #555;
        }}
        .category {{
            margin-bottom: 40px;
        }}
        .category-title {{
            color: #2c5aa0;
            font-size: 22px;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e0e0e0;
        }}
        .article {{
            margin-bottom: 25px;
            padding-bottom: 25px;
            border-bottom: 1px solid #e0e0e0;
        }}
        .article:last-child {{
            border-bottom: none;
        }}
        .article-title {{
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 10px;
        }}
        .article-title a {{
            color: #1a1a1a;
            text-decoration: none;
        }}
        .article-title a:hover {{
            color: #2c5aa0;
        }}
        .article-meta {{
            font-size: 12px;
            color: #888;
            margin-bottom: 10px;
        }}
        .article-summary {{
            color: #444;
            font-size: 15px;
            line-height: 1.7;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 2px solid #e0e0e0;
            text-align: center;
            color: #888;
            font-size: 13px;
        }}
        .stats {{
            background-color: #e8f4f8;
            padding: 10px 15px;
            border-radius: 5px;
            margin-bottom: 20px;
            font-size: 14px;
            color: #2c5aa0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📰 Your Daily News Digest</h1>
            <div class="date">{current_date}</div>
        </div>

        <div class="stats">
            <strong>{total_articles}</strong> unique articles from your newsletters
        </div>
"""

        if digest_summary:
            html += f"""
        <div class="summary">
            {digest_summary}
        </div>
"""

        # Add articles by category
        for category, articles in categorized_articles.items():
            html += f"""
        <div class="category">
            <h2 class="category-title">{category} ({len(articles)})</h2>
"""

            for article in articles:
                source = article.get('newsletter_sender', 'Unknown Source')
                # Extract just the source name from email
                if '<' in source:
                    source = source.split('<')[0].strip()
                
                # Escape single quotes in title for JavaScript
                safe_title = article['title'].replace("'", "\\'").replace('"', '\\"')
                
                html += f"""
            <div class="article">
                <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 10px;">
                    <div class="article-title" style="flex: 1;">
                        <a href="{article['url']}" target="_blank">{article['title']}</a>
                    </div>
                    <div style="display: flex; gap: 8px; margin-left: 16px;">
                        <button onclick="voteArticle('{article['url']}', '{safe_title}', '{source}', 1)" 
                                style="background: #48bb78; color: white; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-size: 14px;">
                            👍
                        </button>
                        <button onclick="voteArticle('{article['url']}', '{safe_title}', '{source}', -1)" 
                                style="background: #f56565; color: white; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-size: 14px;">
                            👎
                        </button>
                        <button onclick="markAsRead('{article['url']}', '{safe_title}', '{source}')" 
                                style="background: #4299e1; color: white; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-size: 14px;">
                            ✓ Read
                        </button>
                    </div>
                </div>
                <div class="article-meta">
                    Source: {source}
                </div>
                <div class="article-summary">
                    {article.get('summary', article['text'][:300] + '...')}
                </div>
            </div>
"""

            html += """
        </div>
"""

       html += f"""
        <div class="footer">
            <p>This digest was automatically generated from your newsletter subscriptions.</p>
            <p style="margin-top: 10px; font-size: 12px;">
                Generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
            </p>
        </div>
    </div>
    
    <script>
        function voteArticle(url, title, source, vote) {{
            fetch('/api/vote', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{
                    article_url: url,
                    article_title: title,
                    article_source: source,
                    vote: vote
                }})
            }})
            .then(response => response.json())
            .then(data => {{
                if (data.success) {{
                    alert(vote === 1 ? '👍 Upvoted!' : '👎 Downvoted!');
                }} else {{
                    alert('Error: ' + data.message);
                }}
            }})
            .catch(error => alert('Error: ' + error));
        }}
        
        function markAsRead(url, title, source) {{
            fetch('/api/mark-read', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{
                    article_url: url,
                    article_title: title,
                    article_source: source
                }})
            }})
            .then(response => response.json())
            .then(data => {{
                if (data.success) {{
                    alert('✓ Marked as read!');
                }} else {{
                    alert('Error: ' + data.message);
                }}
            }})
            .catch(error => alert('Error: ' + error));
        }}
    </script>
</body>
</html>
"""

        return html

    def send_digest(self, recipient: str, subject: str, html_content: str) -> bool:
        """
        Send the digest email.

        Args:
            recipient: Recipient email address
            subject: Email subject line
            html_content: HTML content of the email

        Returns:
            True if successful, False otherwise
        """
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.email_address
            msg['To'] = recipient

            # Attach HTML content
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)

            # Connect and send
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_address, self.password)
                server.send_message(msg)

            logger.info(f"Digest sent successfully to {recipient}")
            return True

        except Exception as e:
            logger.error(f"Failed to send digest: {e}")
            return False

    def create_and_send_digest(self, categorized_articles: Dict[str, List[Dict]],
                               recipient: str, digest_summary: str = "") -> bool:
        """
        Generate and send a complete digest.

        Args:
            categorized_articles: Dictionary of categories -> articles
            recipient: Email address to send digest to
            digest_summary: Optional overall summary

        Returns:
            True if successful
        """
        current_date = datetime.now().strftime("%B %d, %Y")
        subject = f"Your Daily News Digest - {current_date}"

        html_content = self.generate_html_digest(categorized_articles, digest_summary)

        return self.send_digest(recipient, subject, html_content)
