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
    'error': None,
    'step': 0,
    'total_steps': 10
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

        if not supabase_url or not supabase_key:
            logger.warning("Supabase credentials not configured")
            return None

        return SupabaseDB(supabase_url, supabase_key)
    except Exception as e:
        logger.error(f"Failed to initialize Supabase: {e}")
        return None

def update_status(status: str, step: int = 0):
    """Update the current run status with step progress."""
    global last_run_data
    last_run_data['status'] = status
    last_run_data['step'] = step
    logger.info(f"Status: {status} (step {step}/9)")


def process_and_send_digest(days_back=1):
    """
    Main function to process newsletters and send digest.
    This is called by the scheduler and can also be triggered manually.
    """
    global last_run_data

    logger.info("Starting digest generation process...")
    last_run_data['timestamp'] = datetime.now().isoformat()
    last_run_data['total_steps'] = 9
    update_status("Warming up... ☕", 1)

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
        update_status("Vibing with your inbox... 📬", 2)

        # Get senders from both env var and database
        all_senders = list(config['newsletter_senders']) if config['newsletter_senders'] else []
        db = get_supabase_db()
        if db:
            db_senders = db.get_newsletter_senders()
            for sender in db_senders:
                if sender['email'] not in all_senders:
                    all_senders.append(sender['email'])

        logger.info(f"Using {len(all_senders)} newsletter senders")

        newsletters = email_processor.fetch_newsletters(
            days_back=days_back,
            specific_senders=all_senders if all_senders else None
        )

        if not newsletters:
            logger.warning("No newsletters found")
            last_run_data['status'] = 'No newsletters found 📭'
            last_run_data['step'] = 0
            last_run_data['newsletter_count'] = 0
            last_run_data['article_count'] = 0
            return False

        last_run_data['newsletter_count'] = len(newsletters)
        logger.info(f"Found {len(newsletters)} newsletters")

        # Step 2: Extract articles from newsletters
        update_status(f"Extracting the good stuff... 🔍 ({len(newsletters)} newsletters)", 3)
        articles = article_processor.extract_articles_from_newsletters(newsletters)

        # Step 2.5: Filter out read articles
        update_status("Filtering out old news... 📰", 4)
        db = get_supabase_db()
        if db:
            read_urls = db.get_read_article_urls()
            if read_urls:
                logger.info(f"Filtering out {len(read_urls)} read articles")
                articles = [a for a in articles if a['url'] not in read_urls]
                logger.info(f"After filtering: {len(articles)} articles remaining")

        if not articles:
            logger.warning("No articles extracted")
            last_run_data['status'] = 'No articles extracted 📄'
            last_run_data['step'] = 0
            last_run_data['article_count'] = 0
            return False
        logger.info(f"Extracted {len(articles)} articles")

        # Step 3: Deduplicate articles
        update_status(f"Removing duplicates... 🧹 ({len(articles)} articles)", 5)
        unique_articles = article_processor.deduplicate_articles(articles)
        logger.info(f"After deduplication: {len(unique_articles)} unique articles")

        if not unique_articles:
            logger.warning("No unique articles after deduplication")
            last_run_data['status'] = 'No unique articles 🔄'
            last_run_data['step'] = 0
            last_run_data['article_count'] = 0
            return False

        # Step 3.5: Filter out junk articles
        update_status("Taking out the trash... 🗑️", 6)
        if db:
            junk_filters = db.get_junk_filters_with_type()

            if junk_filters:
                logger.info(f"Found {len(junk_filters)} junk filters")
                filtered_articles = []
                from urllib.parse import urlparse

                for article in unique_articles:
                    title_lower = article.get('title', '').lower()
                    article_url = article.get('url', '')

                    # Extract domain from article URL
                    parsed = urlparse(article_url)
                    article_domain = parsed.netloc.lower()
                    if article_domain.startswith('www.'):
                        article_domain = article_domain[4:]

                    is_junk = False
                    for jf in junk_filters:
                        pattern = jf['pattern']
                        pattern_type = jf.get('pattern_type', 'title')

                        if pattern_type == 'domain':
                            # Check if article URL matches blocked domain
                            if pattern in article_domain:
                                is_junk = True
                                break
                        else:
                            # Check if pattern is in title
                            if pattern in title_lower:
                                is_junk = True
                                break

                    if not is_junk:
                        filtered_articles.append(article)
                    else:
                        logger.info(f"Filtered out junk article: {article.get('title', 'Unknown')}")

                unique_articles = filtered_articles
                logger.info(f"After junk filtering: {len(unique_articles)} articles remain")

        if not unique_articles:
            logger.warning("No articles after junk filtering")
            last_run_data['status'] = 'No articles after filtering 🗑️'
            last_run_data['step'] = 0
            last_run_data['article_count'] = 0
            return False

        # Step 3.6: Apply learning from votes
        if db:
            source_scores = db.get_source_scores()
            if source_scores:
                logger.info(f"Applying vote-based learning from {len(source_scores)} scored sources")

                # Filter out heavily downvoted sources (score <= -3)
                before_count = len(unique_articles)
                unique_articles = [
                    a for a in unique_articles
                    if source_scores.get(a.get('newsletter_sender', '').lower().strip(), 0) > -3
                ]
                filtered_count = before_count - len(unique_articles)
                if filtered_count > 0:
                    logger.info(f"Filtered out {filtered_count} articles from heavily downvoted sources")

                # Sort articles: upvoted sources first, then neutral, then slightly downvoted
                def get_source_score(article):
                    source = article.get('newsletter_sender', '').lower().strip()
                    return source_scores.get(source, 0)

                unique_articles.sort(key=get_source_score, reverse=True)
                logger.info("Articles sorted by source preference")

        last_run_data['article_count'] = len(unique_articles)

        # Step 4: Generate summaries
        update_status(f"AI magic happening... ✨ ({len(unique_articles)} articles)", 7)
        unique_articles = summarizer.summarize_all_articles(unique_articles)

        # Step 5: Categorize articles
        update_status("Organizing by topic... 📂", 8)
        categorized_articles = article_processor.categorize_articles(unique_articles)

        # Step 6: Generate digest summary
        digest_summary = summarizer.generate_digest_summary(categorized_articles)

        # Step 6.5: Save digest HTML to file
        update_status("Making it pretty... 💅", 9)
        html_content = digest_generator.generate_html_digest(categorized_articles, digest_summary)
        digest_file_path = '/tmp/last_digest.html'
        with open(digest_file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        logger.info(f"Digest saved to {digest_file_path}")

        # Step 7: Send digest email (silently in background)
        current_date = datetime.now().strftime("%B %d, %Y")
        subject = f"Your Daily News Digest - {current_date}"
        success = digest_generator.send_digest(config['digest_recipient'], subject, html_content)

        # Always show success if we got this far (digest is saved)
        last_run_data['status'] = 'Success! 🎉'
        last_run_data['step'] = 9
        last_run_data['error'] = None
        logger.info("Digest generated successfully!")

        if not success:
            logger.warning("Email sending failed, but digest is available in app")

        return True

    except Exception as e:
        logger.error(f"Error processing digest: {e}", exc_info=True)
        last_run_data['status'] = 'Error 💥'
        last_run_data['step'] = 0
        last_run_data['error'] = str(e)
        return False

    finally:
        # Disconnect from email
        try:
            if 'email_processor' in dir():
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
        return """
        <div style="text-align: center; padding: 40px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
            <img src="https://cataas.com/cat/cute?width=300&height=200" style="border-radius: 12px; margin-bottom: 20px; max-width: 300px;">
            <h2 style="color: #667eea;">No digest yet!</h2>
            <p style="color: #666;">Click "Generate Digest Now" above to create your first digest.</p>
        </div>
        """

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
    """Mark an article as junk and add domain to filter list."""
    try:
        data = request.json
        article_url = data.get('url')
        article_title = data.get('title', '')

        if not article_url:
            return jsonify({
                'success': False,
                'message': 'Article URL is required'
            }), 400

        # Initialize Supabase DB
        db = get_supabase_db()
        if not db:
            return jsonify({
                'success': False,
                'message': 'Supabase not configured'
            }), 500

        # Extract domain from URL
        from urllib.parse import urlparse
        parsed = urlparse(article_url)
        domain = parsed.netloc.lower()

        # Remove www. prefix if present
        if domain.startswith('www.'):
            domain = domain[4:]

        if not domain:
            return jsonify({
                'success': False,
                'message': 'Could not extract domain from URL'
            }), 400

        # Add domain to junk filters
        success = db.add_junk_filter(
            pattern=domain,
            article_url=article_url,
            article_title=article_title,
            pattern_type='domain'
        )

        if success:
            return jsonify({
                'success': True,
                'message': f'Blocked domain: {domain}',
                'pattern': domain
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

@app.route('/api/newsletters', methods=['GET'])
def api_get_newsletters():
    """Get list of newsletter senders."""
    try:
        db = get_supabase_db()
        if not db:
            return jsonify({
                'success': False,
                'message': 'Supabase not configured',
                'newsletters': []
            }), 500

        newsletters = db.get_newsletter_senders()
        return jsonify({
            'success': True,
            'newsletters': newsletters
        })

    except Exception as e:
        logger.error(f"Error getting newsletters: {e}")
        return jsonify({
            'success': False,
            'message': str(e),
            'newsletters': []
        }), 500

@app.route('/api/newsletters', methods=['POST'])
def api_add_newsletter():
    """Add a newsletter sender."""
    try:
        data = request.json
        email = data.get('email', '').strip()
        name = data.get('name', '').strip()

        if not email:
            return jsonify({
                'success': False,
                'message': 'Email is required'
            }), 400

        db = get_supabase_db()
        if not db:
            return jsonify({
                'success': False,
                'message': 'Supabase not configured'
            }), 500

        success = db.add_newsletter_sender(email, name if name else None)

        if success:
            return jsonify({
                'success': True,
                'message': f'Added newsletter: {email}'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to add newsletter'
            }), 500

    except Exception as e:
        logger.error(f"Error adding newsletter: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/newsletters', methods=['DELETE'])
def api_remove_newsletter():
    """Remove a newsletter sender."""
    try:
        data = request.json
        email = data.get('email', '').strip()

        if not email:
            return jsonify({
                'success': False,
                'message': 'Email is required'
            }), 400

        db = get_supabase_db()
        if not db:
            return jsonify({
                'success': False,
                'message': 'Supabase not configured'
            }), 500

        success = db.remove_newsletter_sender(email)

        if success:
            return jsonify({
                'success': True,
                'message': f'Removed newsletter: {email}'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to remove newsletter'
            }), 500

    except Exception as e:
        logger.error(f"Error removing newsletter: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/status')
def api_status():
    """API endpoint to get current status."""
    config = get_config()
    return jsonify({
        'last_run': {
            **last_run_data,
            'step': last_run_data.get('step', 0),
            'total_steps': last_run_data.get('total_steps', 10)
        },
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


# Start scheduler when app loads (works with gunicorn)
# Only start if not already running
try:
    start_scheduler()
except Exception as e:
    logger.error(f"Failed to start scheduler: {e}")


if __name__ == '__main__':
    # Run Flask app
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('DEBUG', 'False').lower() == 'true'

    logger.info(f"Starting Newsletter Digest App on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)

