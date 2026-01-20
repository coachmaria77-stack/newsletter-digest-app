from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import os
from dotenv import load_dotenv
import logging
from datetime import datetime
import json

from email_processor import EmailProcessor
from article_processor import ArticleProcessor
from summarizer import ArticleSummarizer
from digest_generator import DigestGenerator
from supabase_db import SupabaseDB

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-this')
CORS(app)

# Global scheduler
scheduler = BackgroundScheduler()

# Store last run information
last_run_data = {
    'timestamp': None,
    'status': 'Not run yet',
    'article_count': 0,
    'newsletter_count': 0,
    'error': None
}


def get_config():
    """Load configuration from environment variables."""
    return {
        'email_address': os.getenv('EMAIL_ADDRESS'),
        'email_password': os.getenv('EMAIL_PASSWORD'),
        'imap_server': os.getenv('IMAP_SERVER', 'imap.mail.yahoo.com'),
        'imap_port': int(os.getenv('IMAP_PORT', '993')),
        'smtp_server': os.getenv('SMTP_SERVER', 'smtp.mail.yahoo.com'),
        'smtp_port': int(os.getenv('SMTP_PORT', '587')),
        'digest_recipient': os.getenv('DIGEST_RECIPIENT'),
        'openai_api_key': os.getenv('OPENAI_API_KEY'),
        'newsletter_senders': os.getenv('NEWSLETTER_SENDERS', '').split(',') if os.getenv('NEWSLETTER_SENDERS') else None,
        'digest_hour': int(os.getenv('DIGEST_HOUR', '8')),
        'digest_minute': int(os.getenv('DIGEST_MINUTE', '0'))
    }


def get_supabase_db():
    """Get Supabase database instance."""
    try:
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY')

        logger.info(f"SUPABASE_URL set: {bool(supabase_url)}, length: {len(supabase_url) if supabase_url else 0}")
        logger.info(f"SUPABASE_KEY set: {bool(supabase_key)}, length: {len(supabase_key) if supabase_key else 0}")

        if not supabase_url or not supabase_key:
            logger.warning("Supabase credentials not configured")
            return None

        return SupabaseDB(supabase_url, supabase_key)
    except Exception as e:
        logger.error(f"Failed to initialize Supabase: {e}")
        return None

def process_and_send_digest(days_back=1):
    """
    Main function to process newsletters and send digest.
    This is called by the scheduler and can also be triggered manually.
    """
    global last_run_data

    logger.info("Starting digest generation process...")
    last_run_data['timestamp'] = datetime.now().isoformat()
    last_run_data['status'] = 'Running'

    try:
        config = get_config()

        # Validate configuration
        if not config['email_address'] or not config['email_password']:
            raise ValueError("Email credentials not configured")

        if not config['digest_recipient']:
            config['digest_recipient'] = config['email_address']

        # Initialize processors
        email_processor = EmailProcessor(
            config['email_address'],
            config['email_password'],
            config['imap_server'],
            config['imap_port']
        )

        article_processor = ArticleProcessor(similarity_threshold=0.7)
        summarizer = ArticleSummarizer(api_key=config['openai_api_key'])
        digest_generator = DigestGenerator(
            config['smtp_server'],
            config['smtp_port'],
            config['email_address'],
            config['email_password']
        )

        # Step 1: Fetch newsletters
        logger.info("Fetching newsletters...")
        newsletters = email_processor.fetch_newsletters(
            days_back=days_back,
            specific_senders=config['newsletter_senders']
        )

        if not newsletters:
            logger.warning("No newsletters found")
            last_run_data['status'] = 'No newsletters found'
            last_run_data['newsletter_count'] = 0
            last_run_data['article_count'] = 0
            return False

        last_run_data['newsletter_count'] = len(newsletters)
        logger.info(f"Found {len(newsletters)} newsletters")

        # Step 2: Extract articles from newsletters
        logger.info("Extracting articles...")
        articles = article_processor.extract_articles_from_newsletters(newsletters)

        # Step 2.5: Filter out read articles
        db = get_supabase_db()
        if db:
            read_urls = db.get_read_article_urls()
            if read_urls:
                logger.info(f"Filtering out {len(read_urls)} read articles")
                articles = [a for a in articles if a['url'] not in read_urls]
                logger.info(f"After filtering: {len(articles)} articles remaining")

        if not articles:
            logger.warning("No articles extracted")
            last_run_data['status'] = 'No articles extracted'
            last_run_data['article_count'] = 0
            return False
        logger.info(f"Extracted {len(articles)} articles")

        # Step 3: Deduplicate articles
        logger.info("Deduplicating articles...")
        unique_articles = article_processor.deduplicate_articles(articles)
        logger.info(f"After deduplication: {len(unique_articles)} unique articles")

        if not unique_articles:
            logger.warning("No unique articles after deduplication")
            last_run_data['status'] = 'No unique articles'
            last_run_data['article_count'] = 0
            return False

        # Step 3.5: Filter out junk articles
        logger.info("Filtering junk articles...")
        if db:
            junk_patterns = db.get_junk_filters()

            if junk_patterns:
                logger.info(f"Found {len(junk_patterns)} junk filter patterns")
                filtered_articles = []
                for article in unique_articles:
                    title_lower = article.get('title', '').lower()
                    is_junk = any(pattern in title_lower for pattern in junk_patterns)

                    if not is_junk:
                        filtered_articles.append(article)
                    else:
                        logger.info(f"Filtered out junk article: {article.get('title', 'Unknown')}")

                unique_articles = filtered_articles
                logger.info(f"After junk filtering: {len(unique_articles)} articles remain")

        if not unique_articles:
            logger.warning("No articles after junk filtering")
            last_run_data['status'] = 'No articles after filtering'
            last_run_data['article_count'] = 0
            return False

        last_run_data['article_count'] = len(unique_articles)

        # Step 4: Generate summaries
        logger.info("Generating summaries...")
        unique_articles = summarizer.summarize_all_articles(unique_articles)

        # Step 5: Categorize articles
        logger.info("Categorizing articles...")
        categorized_articles = article_processor.categorize_articles(unique_articles)

        # Step 6: Generate digest summary
        digest_summary = summarizer.generate_digest_summary(categorized_articles)

        # Step 6.5: Save digest HTML to file
        logger.info("Generating digest HTML...")
        html_content = digest_generator.generate_html_digest(categorized_articles, digest_summary)
        digest_file_path = '/tmp/last_digest.html'
        with open(digest_file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        logger.info(f"Digest saved to {digest_file_path}")

        # Step 7: Send digest email
        logger.info("Sending digest email...")
        current_date = datetime.now().strftime("%B %d, %Y")
        subject = f"Your Daily News Digest - {current_date}"
        success = digest_generator.send_digest(config['digest_recipient'], subject, html_content)

        if success:
            last_run_data['status'] = 'Success'
            last_run_data['error'] = None
            logger.info("Digest sent successfully!")
            return True
        else:
            last_run_data['status'] = 'Failed to send email'
            logger.error("Failed to send digest email")
            return False

    except Exception as e:
        logger.error(f"Error processing digest: {e}", exc_info=True)
        last_run_data['status'] = 'Error'
        last_run_data['error'] = str(e)
        return False

    finally:
        # Disconnect from email
        try:
            email_processor.disconnect()
        except:
            pass


# Flask routes
@app.route('/')
def index():
    """Main dashboard page."""
    config = get_config()
    return render_template('index.html',
                         config=config,
                         last_run=last_run_data,
                         scheduler_running=scheduler.running)

@app.route('/view-digest')
def view_digest():
    """View the last generated digest."""
    try:
        digest_file_path = '/tmp/last_digest.html'
        with open(digest_file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        return html_content
    except FileNotFoundError:
        return "<h1>No digest available yet</h1><p>Generate a digest first, then come back to view it.</p><p><a href='/'>Go back to dashboard</a></p>"

@app.route('/api/vote', methods=['POST'])
def api_vote():
    """API endpoint to save article vote."""
    try:
        data = request.json
        article_url = data.get('article_url')
        article_title = data.get('article_title')
        article_source = data.get('article_source')
        vote = data.get('vote')

        if not article_url or vote not in [-1, 0, 1]:
            return jsonify({
                'success': False,
                'message': 'Invalid request data'
            }), 400

        db = get_supabase_db()
        if not db:
            return jsonify({
                'success': False,
                'message': 'Supabase not configured'
            }), 500

        existing = db.get_interaction(article_url)

        if existing:
            success = db.update_vote(article_url, vote)
        else:
            success = db.save_interaction(
                article_url,
                article_title,
                article_source,
                vote=vote
            )

        if success:
            return jsonify({
                'success': True,
                'message': 'Vote saved'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to save vote'
            }), 500

    except Exception as e:
        logger.error(f"Error in api_vote: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/mark-read', methods=['POST'])
def api_mark_read():
    """API endpoint to mark article as read."""
    try:
        data = request.json
        article_url = data.get('article_url')
        article_title = data.get('article_title')
        article_source = data.get('article_source')

        if not article_url:
            return jsonify({
                'success': False,
                'message': 'Missing article_url'
            }), 400

        db = get_supabase_db()
        if not db:
            return jsonify({
                'success': False,
                'message': 'Supabase not configured'
            }), 500

        existing = db.get_interaction(article_url)

        if existing:
            success = db.mark_as_read(article_url)
        else:
            success = db.save_interaction(
                article_url,
                article_title,
                article_source,
                is_read=True
            )

        if success:
            return jsonify({
                'success': True,
                'message': 'Marked as read'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to mark as read'
            }), 500

    except Exception as e:
        logger.error(f"Error in api_mark_read: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/mark-junk', methods=['POST'])
def api_mark_junk():
    """Mark an article as junk and add pattern to filter list."""
    try:
        data = request.json
        article_url = data.get('url')
        article_title = data.get('title', '')

        if not article_title:
            return jsonify({
                'success': False,
                'message': 'Article title is required'
            }), 400

        # Initialize Supabase DB
        db = get_supabase_db()
        if not db:
            return jsonify({
                'success': False,
                'message': 'Supabase not configured'
            }), 500

        # Extract key terms from title (remove common words, keep significant ones)
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during', 'before', 'after', 'above', 'below', 'between', 'under', 'again', 'further', 'then', 'once'}

        # Clean and split title
        words = article_title.lower().split()
        # Keep words that are longer than 3 chars and not stop words
        significant_words = [w for w in words if len(w) > 3 and w not in stop_words]

        # Take first 2-3 significant words as the pattern
        if len(significant_words) >= 2:
            pattern = ' '.join(significant_words[:2])
        elif len(significant_words) == 1:
            pattern = significant_words[0]
        else:
            # Fallback to first few words of title
            pattern = ' '.join(words[:2])

        # Add to junk filters
        success = db.add_junk_filter(
            pattern=pattern,
            article_url=article_url,
            article_title=article_title,
            pattern_type='title'
        )

        if success:
            return jsonify({
                'success': True,
                'message': f'Added junk filter: "{pattern}"',
                'pattern': pattern
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to add junk filter'
            }), 500

    except Exception as e:
        logger.error(f"Error marking article as junk: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/history')
def history():
    """View article interaction history."""
    db = get_supabase_db()

    if not db:
        return render_template('history.html',
                             interactions=[],
                             error="Supabase not configured")

    interactions = db.get_all_interactions(limit=200)

    return render_template('history.html',
                         interactions=interactions,
                         error=None)

@app.route('/api/status')
def api_status():
    """API endpoint to get current status."""
    config = get_config()
    return jsonify({
        'last_run': last_run_data,
        'scheduler_running': scheduler.running,
        'config': {
            'email_configured': bool(config['email_address']),
            'openai_configured': bool(config['openai_api_key']),
            'schedule': f"{config['digest_hour']:02d}:{config['digest_minute']:02d}"
        }
    })


@app.route('/api/trigger', methods=['POST'])
def api_trigger():
    """API endpoint to manually trigger digest generation."""
    try:
        days_back = request.json.get('days_back', 1) if request.json else 1

        # Run in background to avoid timeout
        import threading
        thread = threading.Thread(target=process_and_send_digest, args=(days_back,))
        thread.start()

        return jsonify({
            'success': True,
            'message': 'Digest generation started'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/api/test-connection', methods=['POST'])
def api_test_connection():
    """Test email connection."""
    try:
        config = get_config()
        email_processor = EmailProcessor(
            config['email_address'],
            config['email_password'],
            config['imap_server'],
            config['imap_port']
        )

        if email_processor.connect():
            email_processor.disconnect()
            return jsonify({
                'success': True,
                'message': 'Successfully connected to email server'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to connect to email server'
            }), 400

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


def start_scheduler():
    """Start the background scheduler for daily digest."""
    if scheduler.running:
        return

    config = get_config()

    # Schedule daily digest
    scheduler.add_job(
        func=process_and_send_digest,
        trigger=CronTrigger(
            hour=config['digest_hour'],
            minute=config['digest_minute']
        ),
        id='daily_digest',
        name='Daily Newsletter Digest',
        replace_existing=True
    )

    scheduler.start()
    logger.info(f"Scheduler started. Daily digest scheduled for {config['digest_hour']:02d}:{config['digest_minute']:02d}")


if __name__ == '__main__':
    # Start scheduler
    start_scheduler()

    # Run Flask app
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('DEBUG', 'False').lower() == 'true'

    logger.info(f"Starting Newsletter Digest App on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)

