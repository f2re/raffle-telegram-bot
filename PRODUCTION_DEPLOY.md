# Production Deployment Guide

This guide follows production best practices for deploying the Raffle Bot with Mini App.

## Architecture

```
┌─────────────┐
│   Internet  │
└──────┬──────┘
       │ HTTPS (443)
┌──────▼──────┐
│    Nginx    │ ← Serves static files from ./static/
│  (reverse   │ ← Proxies /api/ to backend
│   proxy)    │
└──────┬──────┘
       │ HTTP (127.0.0.1:8000)
┌──────▼──────────────────┐
│  Docker Container       │
│  ┌─────────────────┐   │
│  │ Uvicorn (API)   │   │ ← FastAPI backend
│  └─────────────────┘   │
│  ┌─────────────────┐   │
│  │ Bot (aiogram)   │   │ ← Telegram bot
│  └─────────────────┘   │
│                         │
│  /app/static-built/ ───┼──► Copied to volume on startup
└─────────────────────────┘
       │
       ▼
  ./static/ ◄─────────────────── Volume mounted here
                                  (nginx reads from here)
```

## Key Principles

1. **Security**: Backend port bound to `127.0.0.1` only (not exposed to internet)
2. **Separation**: Nginx serves static files, Docker runs backend + bot
3. **Simplicity**: Single container with multi-stage build
4. **Reliability**: Clean file copy on each startup

## Step-by-Step Deployment

### 1. Prepare Server

```bash
# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Install Nginx
sudo apt update
sudo apt install nginx certbot python3-certbot-nginx
```

### 2. Clone Repository

```bash
# Choose installation path
cd /opt  # or /home/user or any location you prefer

# Clone
git clone <your-repo-url> raffle-telegram-bot
cd raffle-telegram-bot
```

### 3. Configure Environment

```bash
# Copy template
cp .env.example .env

# Edit configuration
nano .env
```

**Critical settings**:
```bash
# Bot
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
ADMIN_USER_IDS=123456789

# Database (for Docker)
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/raffle_bot
REDIS_URL=redis://redis:6379/0

# TON
TON_WALLET_ADDRESS=UQxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TON_WALLET_MNEMONIC=word1 word2 word3 ... word24
TON_CENTER_API_KEY=your_ton_console_api_key
TON_NETWORK=mainnet

# Mini App (IMPORTANT: Replace yourdomain.com with your actual domain!)
MINI_APP_URL=https://yourdomain.com
VITE_API_URL=https://yourdomain.com/api
VITE_WS_URL=wss://yourdomain.com/ws
VITE_BOT_USERNAME=your_bot_username
VITE_TON_WALLET_ADDRESS=UQxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
VITE_TON_CONNECT_MANIFEST_URL=https://yourdomain.com/tonconnect-manifest.json

# Docker
BOT_NAME=raffle-bot
BACKEND_PORT=8000
CACHEBUST=1
```

### 4. Update TON Connect Manifest

```bash
nano frontend/public/tonconnect-manifest.json
```

```json
{
  "url": "https://yourdomain.com",
  "name": "Raffle Bot",
  "iconUrl": "https://yourdomain.com/icon-256.png",
  "termsOfUseUrl": "https://yourdomain.com/terms",
  "privacyPolicyUrl": "https://yourdomain.com/privacy"
}
```

### 5. Setup SSL Certificate

```bash
# Get certificate
sudo certbot certonly --nginx -d yourdomain.com

# Certificates will be at:
# /etc/letsencrypt/live/yourdomain.com/fullchain.pem
# /etc/letsencrypt/live/yourdomain.com/privkey.pem
```

### 6. Configure Nginx

```bash
# Copy template
sudo cp nginx.conf /etc/nginx/sites-available/raffle-bot

# Edit configuration
sudo nano /etc/nginx/sites-available/raffle-bot
```

**Update these lines:**

1. Replace `yourdomain.com` with your domain (multiple places)
2. Update SSL certificate paths (if different)
3. **CRITICAL**: Update the `root` directive with your actual path:

```nginx
# Line 48 - Update this path!
root /opt/raffle-telegram-bot/static;
# ^--- Change to your actual installation path
```

**Enable site:**
```bash
# Create symlink
sudo ln -s /etc/nginx/sites-available/raffle-bot /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# If test passes:
sudo systemctl reload nginx
```

### 7. Build and Deploy

```bash
# Option A: Use deployment script
chmod +x deploy.sh
./deploy.sh

# Option B: Manual deployment
docker-compose build --no-cache
docker-compose up -d
```

### 8. Verify Deployment

```bash
# 1. Check Docker container
docker ps
# Should see: raffle_bot running

# 2. Check backend API
curl http://localhost:8000/api/health
# Should return: {"status":"ok","version":"1.0.0"}

# 3. Check static files were copied
ls -la ./static/
# Should see: index.html and other assets

# 4. Check nginx serves static files
curl https://yourdomain.com
# Should return HTML

# 5. Check API through nginx
curl https://yourdomain.com/api/health
# Should return: {"status":"ok","version":"1.0.0"}

# 6. Check TON Connect manifest
curl https://yourdomain.com/tonconnect-manifest.json
# Should return JSON with CORS header
```

### 9. Test Mini App

1. Open Telegram
2. Find your bot
3. Send `/start`
4. Click "🎮 Открыть Mini App" button
5. Mini App should load and show raffle interface
6. Try connecting TON wallet

## File Structure After Deployment

```
/opt/raffle-telegram-bot/          # Your installation directory
├── .env                            # Your configuration (KEEP SECURE!)
├── docker-compose.yml
├── frontend/                       # Source code
├── backend/                        # Source code
├── app/                            # Bot source code
├── static/                         # ← Nginx serves from here
│   ├── index.html                  #   (copied from container)
│   ├── assets/
│   └── tonconnect-manifest.json
├── logs/                           # Application logs
└── data/                           # Application data
```

## Updating the Application

### Update Code Only

```bash
# Pull latest code
git pull origin main

# Rebuild and restart
docker-compose build --no-cache
docker-compose up -d
```

### Update Frontend Only

```bash
# Make changes to frontend/src/
# Increment CACHEBUST
export CACHEBUST=$((CACHEBUST + 1))
echo "CACHEBUST=$CACHEBUST" >> .env

# Rebuild
docker-compose build --no-cache
docker-compose up -d

# Verify new files
ls -la ./static/
```

### Force Clean Rebuild

```bash
# Stop containers
docker-compose down

# Clean static directory
rm -rf ./static/*

# Increment CACHEBUST
export CACHEBUST=$((CACHEBUST + 1))

# Rebuild
docker-compose build --no-cache --pull

# Start
docker-compose up -d
```

## Monitoring

```bash
# View real-time logs
docker-compose logs -f bot

# View backend logs only
docker-compose logs -f bot | grep uvicorn

# View bot logs only
docker-compose logs -f bot | grep "Bot starting"

# View nginx logs
sudo tail -f /var/log/nginx/raffle-bot.access.log
sudo tail -f /var/log/nginx/raffle-bot.error.log

# Check container status
docker ps
docker stats raffle_bot
```

## Troubleshooting

### Static Files Not Found (404)

```bash
# 1. Check if files exist in container
docker exec raffle_bot ls -la /app/static-built/

# 2. Check if files copied to volume
ls -la ./static/

# 3. Check nginx root path
sudo nginx -T | grep "root"

# 4. Manually trigger copy
docker-compose restart bot
sleep 5
ls -la ./static/

# 5. Check nginx can read files
sudo -u www-data ls -la /opt/raffle-telegram-bot/static/
```

### Backend API Not Responding

```bash
# 1. Check if backend is running
curl http://localhost:8000/api/health

# 2. Check docker logs
docker-compose logs bot | grep uvicorn

# 3. Check port binding
docker port raffle_bot

# 4. Check nginx proxy
sudo nginx -T | grep proxy_pass
```

### Frontend Build Failed

```bash
# 1. Check build logs
docker-compose logs bot | grep "Building frontend"

# 2. Verify environment variables
docker-compose config | grep VITE_

# 3. Build locally to debug
cd frontend
npm install
npm run build
ls -la dist/
```

### Container Won't Start

```bash
# 1. View startup logs
docker-compose logs bot

# 2. Check for errors
docker-compose logs bot | grep ERROR

# 3. Try running manually
docker-compose run --rm bot bash
# Inside container:
ls -la /app/static-built/
ls -la /app/backend/
```

## Security Checklist

- [ ] `.env` file has secure permissions (`chmod 600 .env`)
- [ ] Backend port bound to `127.0.0.1` only (not `0.0.0.0`)
- [ ] SSL certificate installed and working
- [ ] Firewall allows only ports 80, 443, 22
- [ ] Strong database password set
- [ ] TON wallet mnemonic kept secure (backup offline)
- [ ] Admin user IDs correctly configured
- [ ] Nginx security headers enabled
- [ ] Regular security updates applied

## Backup Strategy

```bash
# Create backup directory
mkdir -p ~/backups

# Backup script
cat > ~/backup-raffle-bot.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=~/backups/raffle-bot-$DATE

mkdir -p $BACKUP_DIR

# Backup configuration
cp /opt/raffle-telegram-bot/.env $BACKUP_DIR/

# Backup database
docker exec raffle_postgres pg_dump -U postgres raffle_bot > $BACKUP_DIR/database.sql

# Backup data directory
tar -czf $BACKUP_DIR/data.tar.gz /opt/raffle-telegram-bot/data/

echo "Backup completed: $BACKUP_DIR"
EOF

chmod +x ~/backup-raffle-bot.sh

# Run backup
~/backup-raffle-bot.sh

# Schedule daily backups (cron)
# crontab -e
# Add: 0 2 * * * ~/backup-raffle-bot.sh
```

## Performance Tips

1. **Enable Nginx Caching**:
   - Already configured for static assets (1 year)
   - HTML files not cached (fresh on each request)

2. **Database Connection Pooling**:
   - Already enabled in SQLAlchemy async

3. **Log Rotation**:
   - Already configured in docker-compose.yml
   - Max 10MB per file, keep 3 files

4. **Monitor Resource Usage**:
   ```bash
   docker stats raffle_bot
   ```

## Production Checklist

- [ ] Domain configured and DNS pointing to server
- [ ] SSL certificate installed and auto-renewing
- [ ] `.env` fully configured with production values
- [ ] TON wallet funded for payouts
- [ ] Database backups scheduled
- [ ] Monitoring set up (optional: Sentry, Prometheus)
- [ ] Nginx configured and tested
- [ ] Static files serving correctly
- [ ] API endpoints responding
- [ ] Mini App loads in Telegram
- [ ] TON Connect wallet connection works
- [ ] Test raffle completed successfully
- [ ] Admin commands working
- [ ] Withdrawal process tested

## Support

For issues:
1. Check this guide's troubleshooting section
2. Review logs: `docker-compose logs -f bot`
3. Check documentation: `MINI_APP_SETUP.md`, `QUICK_START.md`
4. Verify configuration: `.env` and `nginx.conf`

---

**Ready for production!** 🚀
