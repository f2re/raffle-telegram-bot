# 🚀 Quick Start Guide

Get the Telegram Raffle Bot running in 5 minutes!

## One-Command Setup

```bash
# Run setup script
./scripts/setup.sh

# Or use Make
make setup
```

## Manual Steps

### 1. Get Your Credentials (2 minutes)

**Telegram Bot Token:**
1. Open Telegram
2. Message [@BotFather](https://t.me/BotFather)
3. Type `/newbot`
4. Follow instructions
5. Copy the token

**Your User ID:**
1. Message [@userinfobot](https://t.me/userinfobot)
2. Copy your ID

**Random.org API Key:**
1. Visit [api.random.org](https://api.random.org/)
2. Sign up (free)
3. Copy API key

### 2. Install Services

**macOS:**
```bash
./scripts/install_services_macos.sh
```

**Linux:**
```bash
sudo ./scripts/install_services_linux.sh
```

**Windows or Docker:**
```bash
# PostgreSQL
docker run --name raffle-postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 -d postgres:16

# Redis
docker run --name raffle-redis -p 6379:6379 -d redis:7
```

### 3. Configure

```bash
# Copy and edit .env
cp .env.example .env
nano .env
```

Update these lines:
```env
TELEGRAM_BOT_TOKEN=your_token_here
ADMIN_USER_ID=your_id_here
RANDOM_ORG_API_KEY=your_key_here
```

### 4. Run

```bash
# Quick start
./scripts/run.sh

# Or with Make
make run

# Or manually
source venv/bin/activate
python scripts/init_db.py
python app/main.py
```

## Verify Installation

```bash
# Check services
./scripts/check_services.sh

# Or with Make
make check
```

## Common Commands

```bash
# Start services (macOS)
make services-start

# Stop services
make services-stop

# View logs
make logs

# Reset database
make db-reset

# Run with Docker
make docker-up
```

## Test Your Bot

1. Open Telegram
2. Find your bot by username
3. Send `/start`
4. You should see the welcome message! 🎉

## Create First Raffle

1. Send `/admin` to your bot
2. Click "Создать розыгрыш"
3. Enter minimum participants (e.g., `10`)
4. Choose currency: `stars` or `rub`
5. Raffle is created!

## Troubleshooting

**Services not running?**
```bash
# Check what's wrong
./scripts/check_services.sh

# Start services
make services-start
```

**Database issues?**
```bash
# Reinitialize
make db-init
```

**Import errors?**
```bash
# Reinstall dependencies
make install
```

**Still stuck?**
See [LOCAL_DEVELOPMENT.md](LOCAL_DEVELOPMENT.md) for detailed troubleshooting.

## Next Steps

- [ ] Test raffle with test payments
- [ ] Configure YooKassa for RUB (optional)
- [ ] Customize bot messages
- [ ] Deploy to production

## Resources

- 📖 [Full Documentation](README.md)
- 🛠 [Local Development Guide](LOCAL_DEVELOPMENT.md)
- 🏗 [Architecture Details](CLAUDE.md)
- 📋 [Implementation Plan](plan.md)

---

**Questions?** Check the docs or review the logs!
