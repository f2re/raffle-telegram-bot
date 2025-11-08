# Local Development Guide

This guide will help you run the Telegram Raffle Bot on your local machine without Docker.

## Prerequisites

- **Python 3.11+**
- **PostgreSQL 14+**
- **Redis 6+**
- **Git**

## Quick Start (Recommended)

### 1. Run Setup Script

```bash
# Make script executable (first time only)
chmod +x scripts/setup.sh

# Run setup
./scripts/setup.sh
```

The setup script will:
- ✅ Check Python version
- ✅ Create virtual environment
- ✅ Install dependencies
- ✅ Create .env file from template
- ✅ Check if PostgreSQL and Redis are installed/running

### 2. Install PostgreSQL and Redis (if needed)

**macOS (Homebrew):**
```bash
./scripts/install_services_macos.sh
```

**Linux (Ubuntu/Debian):**
```bash
sudo ./scripts/install_services_linux.sh
```

**Or use Docker for services only:**
```bash
# PostgreSQL
docker run --name raffle-postgres \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  -d postgres:16

# Redis
docker run --name raffle-redis \
  -p 6379:6379 \
  -d redis:7
```

### 3. Configure Environment

Edit `.env` file with your credentials:

```bash
nano .env  # or use your preferred editor
```

Required settings:
```env
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
ADMIN_USER_ID=your_telegram_user_id
RANDOM_ORG_API_KEY=your_random_org_api_key
```

**How to get credentials:**
- **Bot Token**: Message [@BotFather](https://t.me/BotFather) on Telegram
- **User ID**: Message [@userinfobot](https://t.me/userinfobot) on Telegram
- **Random.org API Key**: Register at [api.random.org](https://api.random.org/)

### 4. Initialize Database

```bash
python scripts/init_db.py
```

This will:
- Create database if it doesn't exist
- Create all required tables
- Verify the setup

### 5. Start the Bot

```bash
./scripts/run.sh
```

Or manually:
```bash
source venv/bin/activate
python app/main.py
```

The bot is now running! 🎉

## Manual Setup (Step by Step)

### 1. Clone Repository

```bash
git clone <your-repo-url>
cd raffle-telegram-bot
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Install PostgreSQL

**macOS:**
```bash
brew install postgresql@16
brew services start postgresql@16
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib
sudo systemctl start postgresql
```

**Windows:**
Download installer from [postgresql.org](https://www.postgresql.org/download/windows/)

### 5. Install Redis

**macOS:**
```bash
brew install redis
brew services start redis
```

**Ubuntu/Debian:**
```bash
sudo apt-get install redis-server
sudo systemctl start redis
```

**Windows:**
Download from [redis.io](https://redis.io/download/) or use WSL

### 6. Configure PostgreSQL

Create database and user:

```bash
# Connect to PostgreSQL
psql -U postgres

# In PostgreSQL shell:
CREATE DATABASE raffle_bot;
ALTER USER postgres PASSWORD 'postgres';
\q
```

### 7. Configure Environment

```bash
cp .env.example .env
nano .env
```

Update these values:
```env
TELEGRAM_BOT_TOKEN=your_actual_token
ADMIN_USER_ID=your_actual_id
RANDOM_ORG_API_KEY=your_actual_key
```

### 8. Initialize Database

```bash
python scripts/init_db.py
```

### 9. Run the Bot

```bash
python app/main.py
```

## Utility Scripts

All scripts are located in the `scripts/` directory:

### Check Services Status
```bash
./scripts/check_services.sh
```
Shows status of PostgreSQL, Redis, Python, venv, and .env

### Setup Everything
```bash
./scripts/setup.sh
```
One-command setup for new installations

### Initialize Database
```bash
python scripts/init_db.py
```
Creates database and tables

### Run Bot
```bash
./scripts/run.sh
```
Runs bot with automatic restart on crashes

### Install Services (macOS)
```bash
./scripts/install_services_macos.sh
```
Installs PostgreSQL and Redis via Homebrew

### Install Services (Linux)
```bash
sudo ./scripts/install_services_linux.sh
```
Installs PostgreSQL and Redis via apt-get

## Development Workflow

### Daily Development

1. **Start services** (if not auto-started):
   ```bash
   # macOS
   brew services start postgresql@16
   brew services start redis

   # Linux
   sudo systemctl start postgresql
   sudo systemctl start redis
   ```

2. **Activate virtual environment**:
   ```bash
   source venv/bin/activate
   ```

3. **Run the bot**:
   ```bash
   ./scripts/run.sh
   # or
   python app/main.py
   ```

### Database Migrations

**Create new migration**:
```bash
alembic revision --autogenerate -m "description of changes"
```

**Apply migrations**:
```bash
alembic upgrade head
```

**Rollback migration**:
```bash
alembic downgrade -1
```

### Reset Database

```bash
# Drop and recreate database
psql -U postgres -c "DROP DATABASE raffle_bot;"
psql -U postgres -c "CREATE DATABASE raffle_bot;"

# Reinitialize
python scripts/init_db.py
```

### View Logs

Logs are stored in `logs/` directory:
```bash
tail -f logs/bot_$(date +%Y-%m-%d).log
```

### Run Tests (when implemented)

```bash
pytest tests/ -v
```

## Troubleshooting

### PostgreSQL Connection Issues

**Error: "could not connect to server"**

Check if PostgreSQL is running:
```bash
# macOS
brew services list | grep postgresql

# Linux
systemctl status postgresql
```

Start it if needed:
```bash
# macOS
brew services start postgresql@16

# Linux
sudo systemctl start postgresql
```

**Error: "password authentication failed"**

Reset PostgreSQL password:
```bash
psql -U postgres
# In psql:
ALTER USER postgres PASSWORD 'postgres';
\q
```

### Redis Connection Issues

**Error: "Connection refused"**

Check if Redis is running:
```bash
redis-cli ping
```

If not running, start it:
```bash
# macOS
brew services start redis

# Linux
sudo systemctl start redis
```

### Import Errors

**Error: "ModuleNotFoundError"**

Ensure virtual environment is activated and dependencies installed:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Database Table Missing

Reinitialize database:
```bash
python scripts/init_db.py
```

Or use Alembic:
```bash
alembic upgrade head
```

### Bot Token Invalid

Verify your token in `.env` file:
```bash
grep TELEGRAM_BOT_TOKEN .env
```

Get a new token from [@BotFather](https://t.me/BotFather) if needed.

### Port Already in Use

**PostgreSQL (5432) or Redis (6379) port conflict:**

Find process using the port:
```bash
# macOS/Linux
lsof -i :5432
lsof -i :6379
```

Kill the process or change port in `.env`:
```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5433/raffle_bot
REDIS_URL=redis://localhost:6380/0
```

## Environment Variables Reference

### Required Variables

| Variable | Description | Where to Get |
|----------|-------------|--------------|
| `TELEGRAM_BOT_TOKEN` | Bot token | [@BotFather](https://t.me/BotFather) |
| `ADMIN_USER_ID` | Your Telegram user ID | [@userinfobot](https://t.me/userinfobot) |
| `RANDOM_ORG_API_KEY` | Random.org API key | [api.random.org](https://api.random.org/) |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `YOOKASSA_SHOP_ID` | YooKassa shop ID | None (RUB payments disabled) |
| `YOOKASSA_SECRET_KEY` | YooKassa secret key | None |
| `MIN_PARTICIPANTS` | Minimum raffle participants | 10 |
| `STARS_ENTRY_FEE` | Entry fee in Stars | 10 |
| `RUB_ENTRY_FEE` | Entry fee in Rubles | 100 |
| `LOG_LEVEL` | Logging level | INFO |

### Database URLs

**Local development:**
```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/raffle_bot
REDIS_URL=redis://localhost:6379/0
```

**Docker services:**
```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/raffle_bot
REDIS_URL=redis://redis:6379/0
```

## IDE Setup

### VS Code

Install recommended extensions:
- Python
- Pylance
- Python Debugger

Create `.vscode/launch.json`:
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: Bot",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/app/main.py",
      "console": "integratedTerminal",
      "envFile": "${workspaceFolder}/.env"
    }
  ]
}
```

### PyCharm

1. Open project
2. Configure Python interpreter: `venv/bin/python`
3. Mark `app` as Sources Root
4. Set environment file to `.env`

## Performance Tips

1. **Use local PostgreSQL/Redis** for faster development (vs Docker)
2. **Enable DEBUG logging** for development:
   ```env
   LOG_LEVEL=DEBUG
   ```
3. **Use SQLAlchemy query logging**:
   - Automatically enabled when `LOG_LEVEL=DEBUG`
4. **Monitor resource usage**:
   ```bash
   # PostgreSQL connections
   psql -U postgres -c "SELECT count(*) FROM pg_stat_activity;"

   # Redis memory
   redis-cli info memory
   ```

## Next Steps

- [ ] Configure YooKassa for RUB payments
- [ ] Set up production monitoring
- [ ] Configure SSL certificates
- [ ] Set up automated backups
- [ ] Deploy to production server

## Support

If you encounter issues:
1. Check service status: `./scripts/check_services.sh`
2. Review logs: `tail -f logs/bot_*.log`
3. Verify .env configuration
4. Check PostgreSQL/Redis connectivity

For more information, see [README.md](README.md) and [CLAUDE.md](CLAUDE.md).
