import imaplib
import email
from email.header import decode_header
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmailProcessor:
    """Handles connection to Yahoo Mail and processing of newsletter emails."""

    def __init__(self, email_address: str, password: str, imap_server: str, imap_port: int):
        self.email_address = email_address
        self.password = password
        self.imap_server = imap_server
        self.imap_port = imap_port
        self.mail = None

    def connect(self) -> bool:
        """Connect to the IMAP server."""
        try:
            self.mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            self.mail.login(self.email_address, self.password)
            logger.info("Successfully connected to email server")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to email server: {e}")
            return False

    def disconnect(self):
        """Disconnect from the IMAP server."""
        if self.mail:
            try:
                self.mail.logout()
            except:
                pass

    def is_newsletter(self, sender: str, subject: str, body_text: str) -> bool:
        """
        Determine if an email is likely a newsletter.
        Uses heuristics to identify newsletter patterns.
        """
        # Common newsletter indicators
        newsletter_keywords = [
            'newsletter', 'digest', 'daily brief', 'morning brief',
            'weekly roundup', 'today in', 'this week', 'breaking news',
            'daily update', 'news roundup', 'top stories'
        ]

        # Common newsletter domains
        news_domains = [
            'nytimes.com', 'wsj.com', 'washingtonpost.com', 'axios.com',
            'politico.com', 'bloomberg.com', 'reuters.com', 'cnn.com',
            'bbc.com', 'theguardian.com', 'forbes.com', 'economist.com',
            'substack.com', 'medium.com', 'news', 'newsletter'
        ]

        # Check subject line
        subject_lower = subject.lower()
        for keyword in newsletter_keywords:
            if keyword in subject_lower:
                return True

        # Check sender domain
        sender_lower = sender.lower()
        for domain in news_domains:
            if domain in sender_lower:
                return True

        # Check for unsubscribe links (common in newsletters)
        if body_text and 'unsubscribe' in body_text.lower():
            return True

        return False

    def decode_subject(self, subject: str) -> str:
        """Decode email subject that may be encoded."""
        try:
            decoded_parts = decode_header(subject)
            decoded_subject = ""
            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    decoded_subject += part.decode(encoding or 'utf-8', errors='ignore')
                else:
                    decoded_subject += part
            return decoded_subject
        except:
            return subject

    def extract_text_from_email(self, msg) -> str:
        """Extract plain text content from email message."""
        text_content = ""

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    try:
                        text_content = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        break
                    except:
                        pass
                elif content_type == "text/html" and not text_content:
                    try:
                        html_content = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        text_content = html_content
                    except:
                        pass
        else:
            try:
                text_content = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
            except:
                pass

        return text_content

    def extract_urls(self, text: str) -> List[str]:
        """Extract URLs from text/HTML content."""
        from bs4 import BeautifulSoup
        from urllib.parse import unquote, urlparse, parse_qs

        urls = set()

        # Method 1: Parse HTML and extract href attributes
        try:
            soup = BeautifulSoup(text, 'html.parser')
            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href']
                if href.startswith('http'):
                    urls.add(href)
        except:
            pass

        # Method 2: Regex fallback for any URLs in text
        url_pattern = r'https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&/=]*)'
        regex_urls = re.findall(url_pattern, text)
        urls.update(regex_urls)

        # Method 3: Decode URL-encoded URLs and extract wrapped URLs from redirects
        decoded_urls = set()
        for url in urls:
            # Decode URL-encoded characters
            decoded = unquote(url)
            decoded_urls.add(decoded)

            # Check if this is a redirect URL wrapping another URL
            try:
                parsed = urlparse(decoded)
                query_params = parse_qs(parsed.query)
                # Common redirect parameter names
                for param in ['url', 'u', 'redirect', 'link', 'target', 'destination', 'goto']:
                    if param in query_params:
                        wrapped_url = query_params[param][0]
                        if wrapped_url.startswith('http'):
                            decoded_urls.add(unquote(wrapped_url))
            except:
                pass

        urls = decoded_urls

        # Comprehensive filter for junk URLs
        filtered_urls = []
        exclude_patterns = [
            'unsubscribe', 'tracking', 'pixel', 'beacon', 'email-open',
            'facebook.com', 'instagram.com', 'twitter.com', 'x.com',
            'linkedin.com/login', 'linkedin.com/in/', 'linkedin.com/company',
            'youtube.com', 'tiktok.com', 'pinterest.com', 'spotify.com',
            '/contact', '/privacy', '/terms', '/signin', '/login', '/signup',
            '/unsubscribe', '/preferences', '/settings', '/account',
            'app-store', 'play.google', 'itunes.apple',
            'schema.org', 'mailto:', 'tel:', 'sms:',
            '/feed', '/rss', '/sitemap'
        ]

        # Exclude URLs that are just domain homepages
        exclude_domains = [
            'facebook.com', 'instagram.com', 'linkedin.com', 'twitter.com',
            'youtube.com', 'tiktok.com', 'pinterest.com'
        ]

        for url in urls:
            url_lower = url.lower()

            # Skip if matches exclude patterns
            if any(pattern in url_lower for pattern in exclude_patterns):
                continue

            # Skip if it's just a social media homepage
            skip = False
            for domain in exclude_domains:
                if url_lower == f'https://{domain}' or url_lower == f'https://{domain}/' or url_lower == f'http://{domain}' or url_lower == f'http://{domain}/':
                    skip = True
                    break

            if not skip:
                filtered_urls.append(url)

        logger.info(f"Extracted {len(filtered_urls)} URLs from content")
        return filtered_urls

    def fetch_newsletters(self, days_back: int = 1, specific_senders: Optional[List[str]] = None) -> List[Dict]:
        """
        Fetch newsletter emails from the inbox.

        Args:
            days_back: Number of days to look back
            specific_senders: Optional list of specific sender email addresses to filter

        Returns:
            List of newsletter dictionaries with metadata
        """
        newsletters = []

        if not self.mail:
            if not self.connect():
                return newsletters

        try:
            # Select inbox
            self.mail.select('INBOX')

            # Calculate date for search
            since_date = (datetime.now() - timedelta(days=days_back)).strftime("%d-%b-%Y")

            # Search for emails
            search_criteria = f'(SINCE {since_date})'
            _, message_numbers = self.mail.search(None, search_criteria)

            for num in message_numbers[0].split():
                try:
                    _, msg_data = self.mail.fetch(num, '(RFC822)')
                    email_body = msg_data[0][1]
                    msg = email.message_from_bytes(email_body)

                    # Extract email metadata
                    sender = msg.get('From', '')
                    subject = self.decode_subject(msg.get('Subject', ''))
                    date = msg.get('Date', '')

                    # Filter by specific senders if provided
                    if specific_senders:
                        if not any(sender_email.lower() in sender.lower() for sender_email in specific_senders):
                            continue

                    # Extract body text
                    body_text = self.extract_text_from_email(msg)

                    # Check if it's a newsletter
                    if self.is_newsletter(sender, subject, body_text) or specific_senders:
                        urls = self.extract_urls(body_text)

                        newsletter_data = {
                            'sender': sender,
                            'subject': subject,
                            'date': date,
                            'body': body_text[:5000],  # Limit body size
                            'urls': urls,
                            'message_id': msg.get('Message-ID', '')
                        }

                        newsletters.append(newsletter_data)
                        logger.info(f"Found newsletter: {subject} from {sender}")

                except Exception as e:
                    logger.error(f"Error processing email: {e}")
                    continue

            logger.info(f"Found {len(newsletters)} newsletters")

        except Exception as e:
            logger.error(f"Error fetching newsletters: {e}")

        return newsletters
