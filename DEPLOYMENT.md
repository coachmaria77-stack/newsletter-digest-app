# Deployment Guide

This guide covers deploying your Newsletter Digest App to various hosting platforms.

## Prerequisites

Before deploying, ensure you have:
- Yahoo Mail account with app password
- (Optional) OpenAI API key
- GitHub account (for most deployment options)

## Option 1: Railway.app (Easiest - Recommended)

Railway is the easiest platform for deployment with excellent free tier.

### Steps:

1. **Push code to GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin your-github-repo-url
   git push -u origin main
   ```

2. **Sign up for Railway**
   - Go to [railway.app](https://railway.app)
   - Sign up with GitHub

3. **Create New Project**
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your newsletter-digest-app repository
   - Railway will auto-detect Python and deploy

4. **Add Environment Variables**
   - Go to your project → Variables
   - Add all variables from `.env.example`:
     ```
     EMAIL_ADDRESS=your-email@yahoo.com
     EMAIL_PASSWORD=your-yahoo-app-password
     DIGEST_RECIPIENT=your-email@yahoo.com
     OPENAI_API_KEY=your-openai-key (optional)
     NEWSLETTER_SENDERS=sender1@domain.com,sender2@domain.com (optional)
     DIGEST_HOUR=8
     DIGEST_MINUTE=0
     FLASK_SECRET_KEY=generate-random-string-here
     PORT=5000
     ```

5. **Deploy**
   - Railway will automatically deploy
   - You'll get a public URL (e.g., `your-app.railway.app`)
   - Visit the URL to access your dashboard

### Railway Advantages:
- Free tier available (500 hours/month)
- Automatic deployments on git push
- Built-in environment variables
- Simple interface

---

## Option 2: Render.com

Render offers a generous free tier with automatic deployments.

### Steps:

1. **Push to GitHub** (same as Railway above)

2. **Sign up for Render**
   - Go to [render.com](https://render.com)
   - Sign up with GitHub

3. **Create New Web Service**
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Configure:
     - **Name**: newsletter-digest-app
     - **Environment**: Python 3
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `python app.py`

4. **Add Environment Variables**
   - In "Environment" section, add all variables from `.env.example`

5. **Deploy**
   - Click "Create Web Service"
   - Render will build and deploy
   - You'll get a URL like `https://newsletter-digest-app.onrender.com`

### Render Advantages:
- Free tier (with limitations)
- Auto-SSL certificates
- Auto-deploy from GitHub
- Background workers supported

### Render Notes:
- Free tier apps sleep after 15 minutes of inactivity
- First request after sleep takes ~30 seconds to wake up
- Consider upgrading to paid tier for always-on service

---

## Option 3: PythonAnywhere

Good for beginners with Python experience.

### Steps:

1. **Sign up**
   - Go to [pythonanywhere.com](https://www.pythonanywhere.com)
   - Create free account

2. **Upload Files**
   - Go to "Files" tab
   - Create directory: `/home/yourusername/newsletter-digest-app`
   - Upload all project files

3. **Install Dependencies**
   - Go to "Consoles" tab
   - Start Bash console
   ```bash
   cd newsletter-digest-app
   pip3 install --user -r requirements.txt
   ```

4. **Create Web App**
   - Go to "Web" tab → "Add a new web app"
   - Choose "Manual configuration" → Python 3.10
   - Configure WSGI file:

   Edit `/var/www/yourusername_pythonanywhere_com_wsgi.py`:
   ```python
   import sys
   import os

   path = '/home/yourusername/newsletter-digest-app'
   if path not in sys.path:
       sys.path.append(path)

   # Load environment variables
   from dotenv import load_dotenv
   load_dotenv(os.path.join(path, '.env'))

   from app import app as application
   ```

5. **Set Environment Variables**
   - Create `.env` file in project directory with your settings

6. **Set up Scheduled Task**
   - Go to "Tasks" tab
   - Add scheduled task (daily at your preferred time)
   - Command: `/home/yourusername/.local/bin/python3 /home/yourusername/newsletter-digest-app/run_digest.py`

   Create `run_digest.py`:
   ```python
   from app import process_and_send_digest
   process_and_send_digest()
   ```

7. **Reload Web App**
   - Go to "Web" tab
   - Click "Reload"

### PythonAnywhere Advantages:
- Simple Python-focused platform
- Built-in scheduled tasks
- Free tier available

### PythonAnywhere Notes:
- Free tier has some limitations (external internet access)
- Requires manual file uploads for updates
- Need to manually configure WSGI

---

## Option 4: Heroku

Heroku is a popular choice, though their free tier was discontinued.

### Steps:

1. **Install Heroku CLI**
   ```bash
   # macOS
   brew tap heroku/brew && brew install heroku

   # Other platforms: https://devcenter.heroku.com/articles/heroku-cli
   ```

2. **Login and Create App**
   ```bash
   heroku login
   heroku create your-newsletter-digest-app
   ```

3. **Set Environment Variables**
   ```bash
   heroku config:set EMAIL_ADDRESS=your-email@yahoo.com
   heroku config:set EMAIL_PASSWORD=your-app-password
   heroku config:set DIGEST_RECIPIENT=your-email@yahoo.com
   heroku config:set OPENAI_API_KEY=your-key
   heroku config:set DIGEST_HOUR=8
   heroku config:set DIGEST_MINUTE=0
   heroku config:set FLASK_SECRET_KEY=random-string
   ```

4. **Deploy**
   ```bash
   git push heroku main
   ```

5. **Open App**
   ```bash
   heroku open
   ```

### Heroku Notes:
- Requires paid plan ($5+/month minimum)
- Excellent documentation and tooling
- Easy scaling options

---

## Option 5: DigitalOcean App Platform

### Steps:

1. **Push to GitHub**

2. **Create App**
   - Go to [DigitalOcean App Platform](https://www.digitalocean.com/products/app-platform)
   - Click "Create App"
   - Connect GitHub repository

3. **Configure**
   - DigitalOcean will auto-detect Python
   - Add environment variables in the "Environment Variables" section

4. **Deploy**
   - Click "Next" through configuration
   - Review and deploy

### DigitalOcean Advantages:
- $5/month basic plan
- Good performance
- Integrated with other DO services

---

## Environment Variables Reference

Required for all platforms:

```bash
# Email Configuration
EMAIL_ADDRESS=your-email@yahoo.com
EMAIL_PASSWORD=your-yahoo-app-password

# Email Server Settings (Yahoo Mail defaults)
IMAP_SERVER=imap.mail.yahoo.com
IMAP_PORT=993
SMTP_SERVER=smtp.mail.yahoo.com
SMTP_PORT=587

# Digest Settings
DIGEST_RECIPIENT=your-email@yahoo.com
DIGEST_HOUR=8
DIGEST_MINUTE=0

# Optional: OpenAI for better summaries
OPENAI_API_KEY=sk-your-key-here

# Optional: Filter specific senders
NEWSLETTER_SENDERS=newsletter@nytimes.com,news@wsj.com

# Application Settings
FLASK_SECRET_KEY=generate-a-random-secret-key-here
DEBUG=False
PORT=5000
```

---

## Post-Deployment

### 1. Test Your Deployment

Visit your app URL and:
- Click "Test Email Connection" to verify Yahoo Mail access
- Click "Generate Digest Now" to test the full workflow
- Check your email for the digest

### 2. Verify Scheduled Runs

- Check that the scheduler is running in the dashboard
- Wait for the scheduled time and verify you receive the digest
- Check logs if issues occur

### 3. Monitor

Most platforms provide logs:
- **Railway**: Project → Deployments → View Logs
- **Render**: Dashboard → Logs tab
- **PythonAnywhere**: Files → Log files
- **Heroku**: `heroku logs --tail`

---

## Troubleshooting

### App Not Starting
- Check logs for error messages
- Verify all environment variables are set
- Ensure `requirements.txt` is correct

### Scheduler Not Running
- Verify scheduler starts in logs
- Check timezone settings on hosting platform
- For PythonAnywhere, ensure scheduled task is configured

### Email Connection Fails
- Double-check Yahoo app password (not regular password)
- Verify IMAP/SMTP settings
- Check Yahoo account security settings

### Out of Memory
- Reduce `days_back` parameter (fewer articles to process)
- Upgrade to paid tier with more RAM
- Optimize article extraction limits

---

## Cost Comparison

| Platform | Free Tier | Paid Starting | Best For |
|----------|-----------|---------------|----------|
| Railway | 500 hrs/mo | $5/mo | Ease of use |
| Render | Limited | $7/mo | Auto-scaling |
| PythonAnywhere | Limited | $5/mo | Python beginners |
| Heroku | None | $5/mo | Enterprise |
| DigitalOcean | None | $5/mo | Performance |

---

## Recommendations

**For Most Users**: Use **Railway.app**
- Easiest setup
- Good free tier
- Automatic deployments

**For Always-On Service**: Upgrade to paid tier on any platform
- Prevents sleeping/cold starts
- Better reliability
- More resources

**For Learning**: Use **PythonAnywhere**
- Simpler interface
- Direct file access
- Good for understanding deployment

---

## Security Best Practices

1. **Never commit `.env` file** - Always use environment variables
2. **Use strong secret keys** - Generate with: `python -c "import secrets; print(secrets.token_hex(32))"`
3. **Rotate passwords** - Change Yahoo app password periodically
4. **Monitor logs** - Check for unusual activity
5. **Limit API keys** - Use OpenAI API keys with usage limits

---

## Getting Help

If you encounter issues:
1. Check platform-specific documentation
2. Review application logs
3. Verify environment variables are set correctly
4. Test email connection locally first
5. Check Yahoo Mail and OpenAI account status
