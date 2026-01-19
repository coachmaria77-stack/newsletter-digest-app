# Newsletter Digest App

An automated newsletter aggregator that connects to your Yahoo Mail, extracts articles from various news organizations, deduplicates them, and sends you a beautifully formatted daily digest with AI-powered summaries.

## Features

- 🔄 **Automatic Newsletter Detection**: Intelligently identifies newsletter emails using heuristics
- 📧 **Yahoo Mail Integration**: Connects via IMAP to fetch newsletters
- 🔗 **Article Extraction**: Extracts article URLs and content from newsletters
- 🎯 **Smart Deduplication**: Uses text similarity algorithms to remove duplicate articles
- 🤖 **AI Summarization**: Generates concise summaries using OpenAI API (with fallback)
- 📊 **Categorization**: Automatically groups articles by topic
- 📮 **Email Delivery**: Sends beautifully formatted HTML digest to your inbox
- ⏰ **Scheduled Runs**: Automatically generates digests daily at your preferred time
- 🌐 **Web Dashboard**: Simple interface to monitor status and trigger manual runs

## Quick Start

### 1. Prerequisites

- Python 3.8 or higher
- Yahoo Mail account
- (Optional) OpenAI API key for better summaries

### 2. Get Yahoo App Password

1. Go to [Yahoo Account Security](https://login.yahoo.com/account/security)
2. Turn on 2-Step Verification if not already enabled
3. Click "Generate app password"
4. Select "Other App" and name it "Newsletter Digest"
5. Copy the generated password (you'll need this for configuration)

### 3. Installation

```bash
# Clone or download the repository
cd newsletter-digest-app

# Install dependencies
pip install -r requirements.txt --break-system-packages

# Copy environment template
cp .env.example .env
```

### 4. Configuration

Edit the `.env` file with your settings:

```env
# Yahoo Mail Configuration
EMAIL_ADDRESS=your-email@yahoo.com
EMAIL_PASSWORD=your-yahoo-app-password-here

# Recipient for digest (can be same as EMAIL_ADDRESS)
DIGEST_RECIPIENT=your-email@yahoo.com

# Optional: OpenAI API Key for better summaries
OPENAI_API_KEY=sk-your-api-key-here

# Optional: Specific newsletter senders (comma-separated)
# Leave empty to auto-detect all newsletters
NEWSLETTER_SENDERS=newsletter@nytimes.com,news@wsj.com

# Digest Schedule (24-hour format)
DIGEST_HOUR=8
DIGEST_MINUTE=0

# Application Settings
FLASK_SECRET_KEY=change-this-to-random-string
DEBUG=False
```

### 5. Run Locally

```bash
python app.py
```

Then open your browser to `http://localhost:5000`

## Usage

### Web Dashboard

The dashboard provides:
- Configuration status overview
- Last run statistics
- Manual trigger buttons
- Email connection testing
- Setup instructions

### Manual Trigger

Generate a digest immediately:
```bash
# Via dashboard: Click "Generate Digest Now"
# Or via API:
curl -X POST http://localhost:5000/api/trigger -H "Content-Type: application/json"
```

### Scheduled Runs

The app automatically runs daily at the time specified in your `.env` file (default: 8:00 AM).

## Deployment

### Option 1: Railway.app (Recommended)

1. Sign up at [Railway.app](https://railway.app)
2. Create new project from GitHub repo
3. Add environment variables from your `.env` file
4. Deploy!

### Option 2: Render.com

1. Sign up at [Render.com](https://render.com)
2. Create new Web Service
3. Connect your GitHub repository
4. Set environment variables
5. Deploy

### Option 3: PythonAnywhere

1. Sign up at [PythonAnywhere](https://www.pythonanywhere.com)
2. Upload your files
3. Create a web app with Flask
4. Configure environment variables
5. Set up scheduled task for daily runs

### Environment Variables for Deployment

Make sure to set these in your hosting platform:

```
EMAIL_ADDRESS
EMAIL_PASSWORD
DIGEST_RECIPIENT
OPENAI_API_KEY (optional)
NEWSLETTER_SENDERS (optional)
DIGEST_HOUR
DIGEST_MINUTE
FLASK_SECRET_KEY
```

## How It Works

1. **Email Fetching**: Connects to Yahoo Mail via IMAP and retrieves emails from the last 24 hours
2. **Newsletter Detection**: Uses heuristics (sender domains, keywords, unsubscribe links) to identify newsletters
3. **Article Extraction**: Extracts URLs from newsletters and fetches article content using newspaper3k
4. **Deduplication**: Calculates text similarity using TF-IDF and cosine similarity to remove duplicates
5. **Summarization**: Generates concise summaries using OpenAI GPT-3.5 (or extractive fallback)
6. **Categorization**: Groups articles by topic using keyword matching
7. **Email Generation**: Creates beautiful HTML email with categorized articles and summaries
8. **Delivery**: Sends digest via SMTP to your specified recipient

## Configuration Options

### Newsletter Sender Filtering

To only process specific newsletters, add sender emails to `.env`:

```env
NEWSLETTER_SENDERS=newsletter@nytimes.com,morning@axios.com,news@wsj.com
```

Leave empty to auto-detect all newsletters.

### Similarity Threshold

Edit `app.py` to adjust deduplication sensitivity:

```python
article_processor = ArticleProcessor(similarity_threshold=0.7)  # 0.0-1.0
```

Higher values = stricter deduplication (fewer duplicates allowed)

### Summary Length

Edit `summarizer.py` to change summary length:

```python
article['summary'] = self.summarize_article(article, max_words=80)  # Default: 80
```

## Troubleshooting

### "Failed to connect to email server"

- Verify your Yahoo app password is correct (not your regular password)
- Ensure 2-Step Verification is enabled on Yahoo
- Check that IMAP access is enabled in Yahoo settings

### "No newsletters found"

- Check that you have newsletters from the last 24 hours
- Try adding specific newsletter senders in NEWSLETTER_SENDERS
- Check the logs for detection patterns

### OpenAI API Errors

- Verify your API key is correct
- Check your OpenAI account has credits
- The app will fall back to extractive summaries if AI fails

### Digest not sending

- Verify SMTP credentials are correct
- Check that your Yahoo app password has email sending permissions
- Review logs for specific error messages

## API Endpoints

### Get Status
```
GET /api/status
```

Returns current status, configuration, and last run information.

### Trigger Digest
```
POST /api/trigger
Content-Type: application/json

{
  "days_back": 1
}
```

Manually trigger digest generation for specified number of days.

### Test Connection
```
POST /api/test-connection
```

Test email server connection without running full digest.

## Architecture

```
newsletter-digest-app/
├── app.py                  # Flask application & scheduler
├── email_processor.py      # IMAP email fetching & newsletter detection
├── article_processor.py    # Article extraction & deduplication
├── summarizer.py          # AI summarization
├── digest_generator.py    # HTML email generation & sending
├── requirements.txt       # Python dependencies
├── .env.example          # Configuration template
├── templates/
│   └── index.html        # Web dashboard
└── static/
    ├── css/
    │   └── style.css     # Dashboard styles
    └── js/
        └── app.js        # Dashboard JavaScript
```

## Advanced Features

### Custom Categorization

Edit `article_processor.py` to add/modify categories:

```python
category_keywords = {
    'Your Category': ['keyword1', 'keyword2', ...],
    ...
}
```

### Multiple Recipients

To send to multiple recipients, modify `digest_generator.py`:

```python
msg['To'] = ', '.join(['email1@example.com', 'email2@example.com'])
```

### Digest Frequency

Modify the scheduler in `app.py` for different schedules:

```python
# Weekly digest on Monday at 8 AM
scheduler.add_job(
    func=process_and_send_digest,
    trigger=CronTrigger(day_of_week='mon', hour=8, minute=0),
    args=[7],  # 7 days back
    ...
)
```

## License

MIT License - feel free to use and modify as needed!

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review logs in the console/dashboard
3. Verify all configuration settings

## Future Enhancements

- Support for other email providers (Gmail, Outlook)
- RSS feed integration
- Mobile app
- Machine learning-based categorization
- Sentiment analysis
- Reading time estimates
- Social media integration
