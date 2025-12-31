# Mini App Setup Guide

This guide will help you deploy the Raffle Bot with the Vue 3 Mini App frontend.

## Architecture Overview

The project now includes:
- **Frontend**: Vue 3 + TypeScript + Vite Mini App with TON Connect integration
- **Backend**: FastAPI REST API for the Mini App
- **Bot**: Aiogram 3.x Telegram Bot (existing)
- **Database**: PostgreSQL (shared between bot and backend)
- **Cache**: Redis (shared between bot and backend)

## Prerequisites

1. **Server Requirements**:
   - Linux VPS (Ubuntu 20.04+ recommended)
   - Docker and Docker Compose installed
   - Nginx installed
   - Domain name with SSL certificate (Let's Encrypt)
   - At least 2GB RAM, 2 CPU cores

2. **Accounts & API Keys**:
   - Telegram Bot Token (from @BotFather)
   - TON Wallet (mainnet or testnet)
   - TON Console API Key (from https://tonconsole.com)
   - Random.org API Key

## Step 1: Clone and Configure

```bash
# Clone the repository
cd /opt
git clone <your-repo-url> raffle-telegram-bot
cd raffle-telegram-bot

# Copy environment file
cp .env.example .env

# Edit .env with your values
nano .env
```

### Required Environment Variables

Edit `.env` and configure these variables:

```bash
# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
ADMIN_USER_IDS=your_telegram_user_id

# Database (for Docker deployment)
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/raffle_bot
REDIS_URL=redis://redis:6379/0

# TON Wallet
TON_WALLET_ADDRESS=UQxxx...  # Your bot's TON wallet address
TON_WALLET_MNEMONIC=word1 word2 ... word24
TON_CENTER_API_KEY=your_ton_console_api_key
TON_NETWORK=mainnet  # or testnet

# Random.org
RANDOM_ORG_API_KEY=your_random_org_api_key

# Mini App Configuration
BOT_NAME=raffle-bot
BACKEND_PORT=8000
MINI_APP_URL=https://yourdomain.com

# Frontend Build Variables (IMPORTANT!)
VITE_API_URL=https://yourdomain.com/api
VITE_WS_URL=wss://yourdomain.com/ws
VITE_BOT_USERNAME=your_bot_username
VITE_TON_WALLET_ADDRESS=UQxxx...  # Same as TON_WALLET_ADDRESS above
VITE_TON_CONNECT_MANIFEST_URL=https://yourdomain.com/tonconnect-manifest.json
```

## Step 2: Update TON Connect Manifest

Edit `frontend/public/tonconnect-manifest.json`:

```json
{
  "url": "https://yourdomain.com",
  "name": "Raffle Bot",
  "iconUrl": "https://yourdomain.com/icon-256.png",
  "termsOfUseUrl": "https://yourdomain.com/terms",
  "privacyPolicyUrl": "https://yourdomain.com/privacy"
}
```

Replace `yourdomain.com` with your actual domain.

## Step 3: Build and Deploy with Docker

```bash
# Build the project (includes frontend build)
docker-compose build --no-cache

# Start services
docker-compose up -d

# Check logs
docker-compose logs -f bot

# Verify frontend files were built
ls -la ./static/
```

You should see `index.html` and other assets in the `./static/` directory.

## Step 4: Configure Nginx

### Install Nginx (if not already installed)

```bash
sudo apt update
sudo apt install nginx
```

### Setup SSL Certificate

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d yourdomain.com
```

### Create Nginx Configuration

```bash
# Copy the nginx config template
sudo cp nginx.conf /etc/nginx/sites-available/raffle-bot

# Edit the config
sudo nano /etc/nginx/sites-available/raffle-bot
```

Update these lines in the config:
- Replace `yourdomain.com` with your domain
- Update `root /path/to/raffle-telegram-bot/static;` to the correct path

Example:
```nginx
root /opt/raffle-telegram-bot/static;
```

### Enable the Site

```bash
# Create symlink
sudo ln -s /etc/nginx/sites-available/raffle-bot /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

## Step 5: Verify Deployment

### Check Services

```bash
# Check if bot container is running
docker ps

# Check backend API
curl http://localhost:8000/api/health

# Check nginx is serving static files
curl https://yourdomain.com

# Check TON Connect manifest
curl https://yourdomain.com/tonconnect-manifest.json
```

### Test Mini App

1. Open your bot in Telegram
2. Send `/start`
3. Click "🎮 Открыть Mini App"
4. The Mini App should load with the raffle interface

## Step 6: Configure Bot Menu Button (Optional)

You can add the Mini App to the bot's menu button:

```bash
# Use BotFather to set menu button
# Send /setmenubutton to @BotFather
# Select your bot
# Enter URL: https://yourdomain.com
# Enter button text: Open App
```

## Troubleshooting

### Frontend Not Building

```bash
# Check build logs
docker-compose logs bot | grep "Building frontend"

# Verify environment variables are set
docker-compose config | grep VITE_

# Force rebuild
export CACHEBUST=$((CACHEBUST + 1))
docker-compose build --no-cache
```

### Static Files Not Found

```bash
# Check if files are in the volume
ls -la ./static/

# Check nginx error logs
sudo tail -f /var/log/nginx/raffle-bot.error.log

# Verify nginx root path
sudo nginx -T | grep "root"
```

### API Endpoint Not Working

```bash
# Check backend is running
curl http://localhost:8000/api/health

# Check nginx proxy configuration
sudo nginx -T | grep "proxy_pass"

# Check backend logs
docker-compose logs -f bot | grep uvicorn
```

### TON Connect Not Working

1. Verify `tonconnect-manifest.json` is accessible:
   ```bash
   curl https://yourdomain.com/tonconnect-manifest.json
   ```

2. Check CORS headers:
   ```bash
   curl -I https://yourdomain.com/tonconnect-manifest.json
   ```
   Should include `Access-Control-Allow-Origin: *`

3. Verify `VITE_TON_CONNECT_MANIFEST_URL` in `.env` matches the actual URL

## Updating the Frontend

When you make changes to the frontend:

```bash
# Increment cache buster in .env
CACHEBUST=2

# Rebuild
docker-compose build --no-cache

# Restart
docker-compose up -d

# Verify new files
ls -la ./static/
```

## Security Checklist

- [ ] SSL certificate installed and working
- [ ] Firewall configured (only ports 80, 443, 22 open)
- [ ] Strong database password set
- [ ] `.env` file permissions set to 600
- [ ] TON wallet mnemonic kept secure
- [ ] Admin user IDs correctly configured
- [ ] Nginx security headers enabled

## Performance Optimization

### Enable Gzip Compression

Add to nginx config:
```nginx
gzip on;
gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;
```

### Enable Browser Caching

Already configured in the provided `nginx.conf`:
```nginx
location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

## Monitoring

### View Logs

```bash
# Bot logs
docker-compose logs -f bot

# Nginx access logs
sudo tail -f /var/log/nginx/raffle-bot.access.log

# Nginx error logs
sudo tail -f /var/log/nginx/raffle-bot.error.log
```

### Check Resource Usage

```bash
# Docker stats
docker stats

# System resources
htop
```

## Backup

### Database Backup

```bash
# Backup
docker-compose exec postgres pg_dump -U postgres raffle_bot > backup_$(date +%Y%m%d).sql

# Restore
docker-compose exec -T postgres psql -U postgres raffle_bot < backup_20240101.sql
```

### Complete Backup

```bash
# Backup everything
tar -czf raffle-bot-backup-$(date +%Y%m%d).tar.gz \
  .env \
  ./data \
  ./logs \
  backup_*.sql
```

## Support

For issues and questions:
- Check logs first
- Review this documentation
- Check the main CLAUDE.md file
- Create an issue on GitHub

## Next Steps

1. Test the Mini App thoroughly
2. Monitor for errors in the first few days
3. Set up automated backups
4. Configure monitoring/alerting (optional)
5. Add analytics (optional)

Congratulations! Your Raffle Bot Mini App is now deployed! 🎉
