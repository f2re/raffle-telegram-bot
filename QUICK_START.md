# Quick Start Guide - Raffle Bot Mini App

## Overview

This bot now includes a Vue 3 Mini App with TON Connect integration for seamless raffle participation.

## Quick Setup (5 Minutes)

### 1. Configure Environment

```bash
# Copy and edit .env
cp .env.example .env
nano .env
```

**Essential variables to configure:**
```bash
TELEGRAM_BOT_TOKEN=your_bot_token
ADMIN_USER_IDS=your_telegram_id
TON_WALLET_ADDRESS=UQxxx...
TON_CENTER_API_KEY=your_api_key
RANDOM_ORG_API_KEY=your_api_key

# Mini App URLs (replace yourdomain.com)
MINI_APP_URL=https://yourdomain.com
VITE_API_URL=https://yourdomain.com/api
VITE_BOT_USERNAME=your_bot_username
VITE_TON_WALLET_ADDRESS=UQxxx...
VITE_TON_CONNECT_MANIFEST_URL=https://yourdomain.com/tonconnect-manifest.json
```

### 2. Update TON Connect Manifest

```bash
# Edit the manifest
nano frontend/public/tonconnect-manifest.json
```

Replace `yourdomain.com` with your actual domain.

### 3. Build and Run

```bash
# Build with Docker
docker-compose build

# Start all services
docker-compose up -d

# Check logs
docker-compose logs -f bot
```

### 4. Setup Nginx

```bash
# Copy nginx config
sudo cp nginx.conf /etc/nginx/sites-available/raffle-bot

# Edit and update paths
sudo nano /etc/nginx/sites-available/raffle-bot

# Enable site
sudo ln -s /etc/nginx/sites-available/raffle-bot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 5. Test

```bash
# Check backend health
curl http://localhost:8000/api/health

# Check frontend
curl https://yourdomain.com

# Test in Telegram
# 1. Send /start to your bot
# 2. Click "🎮 Открыть Mini App"
```

## Project Structure

```
raffle-telegram-bot/
├── frontend/              # Vue 3 Mini App
│   ├── src/
│   │   ├── App.vue       # Main component
│   │   ├── composables/  # TON Connect, Telegram
│   │   └── api/          # API client
│   └── public/
│       └── tonconnect-manifest.json
├── backend/               # FastAPI Backend
│   ├── app/
│   │   ├── main.py       # FastAPI app
│   │   └── api/          # API endpoints
│   └── Dockerfile        # Multi-stage build
├── app/                   # Telegram Bot
│   ├── handlers/         # Bot handlers
│   └── database/         # Database models
└── docker-compose.yml
```

## Key Features

### Mini App
- 🎮 Vue 3 + TypeScript
- 💎 TON Connect integration
- ⚡ Real-time raffle updates
- 📱 Telegram WebApp integration
- 🎨 Beautiful gradient UI

### Backend
- 🚀 FastAPI REST API
- 🔐 Telegram WebApp data verification
- 📊 Shared database with bot
- ⚡ Fast async operations

### Bot
- 🤖 Aiogram 3.x
- 💎 TON blockchain payments
- 🎲 Random.org fair draws
- 📊 Complete raffle management

## API Endpoints

- `GET /api/health` - Health check
- `GET /api/raffle/current` - Get current raffle
- `GET /api/raffle/{id}/participants` - Get participants
- `POST /api/raffle/join` - Join raffle with TON payment

## Development

### Frontend Development

```bash
cd frontend
npm install
npm run dev
```

Access at http://localhost:5173

### Backend Development

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Access at http://localhost:8000

## Troubleshooting

### Build Issues

```bash
# Force clean rebuild
export CACHEBUST=$((CACHEBUST + 1))
docker-compose build --no-cache
```

### Static Files Not Found

```bash
# Check static directory
ls -la ./static/

# Verify nginx serves files
curl https://yourdomain.com/index.html
```

### API Not Working

```bash
# Check backend logs
docker-compose logs -f bot | grep uvicorn

# Test API directly
curl http://localhost:8000/api/health
```

## Update Frontend

```bash
# Make changes to frontend/src/
# Increment CACHEBUST in .env
# Rebuild
docker-compose build --no-cache
docker-compose up -d
```

## Production Checklist

- [ ] SSL certificate installed
- [ ] `.env` configured with production values
- [ ] Nginx configured and tested
- [ ] Domain DNS pointing to server
- [ ] Firewall configured
- [ ] Database backups scheduled
- [ ] TON wallet funded
- [ ] Bot tested end-to-end

## Documentation

- **Full Setup**: See `MINI_APP_SETUP.md`
- **Bot Architecture**: See `CLAUDE.md`
- **API Docs**: http://localhost:8000/docs (when running)

## Support

For detailed documentation and troubleshooting, see:
- `MINI_APP_SETUP.md` - Complete deployment guide
- `CLAUDE.md` - Project architecture
- GitHub Issues - Report problems

---

**Ready to launch!** 🚀

Your users can now participate in raffles through a beautiful Mini App interface with seamless TON payments!
