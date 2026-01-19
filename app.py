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

        last_run_data['article_count'] = len(unique_articles)

        # Step 4: Generate summaries
        logger.info("Generating summaries...")
        unique_articles = summarizer.summarize_all_articles(unique_articles)

        # Step 5: Categorize articles
        logger.info("Categorizing articles...")
        categorized_articles = article_processor.categorize_articles(unique_articles)

        # Step 6: Generate digest summary
        digest_summary = summarizer.generate_digest_summary(categorized_articles)

        # Step 7: Send digest email
        logger.info("Sending digest email...")
        success = digest_generator.create_and_send_digest(
            categorized_articles,
            config['digest_recipient'],
            digest_summary
        )

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
