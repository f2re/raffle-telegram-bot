#!/bin/bash
# Quick start script for local development

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🤖 Starting Telegram Raffle Bot...${NC}\n"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${RED}❌ Virtual environment not found!${NC}"
    echo "Please run setup first: ./scripts/setup.sh"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ .env file not found!${NC}"
    echo "Please copy .env.example to .env and configure it:"
    echo "  cp .env.example .env"
    echo "  # Edit .env with your credentials"
    exit 1
fi

# Check PostgreSQL
echo -e "${YELLOW}Checking PostgreSQL...${NC}"
if ! pg_isready &> /dev/null; then
    echo -e "${RED}❌ PostgreSQL is not running!${NC}"
    echo ""
    echo "Start PostgreSQL with one of these commands:"
    echo "  brew services start postgresql@16  # macOS with Homebrew"
    echo "  sudo systemctl start postgresql    # Linux with systemd"
    echo "  docker run --name raffle-postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 -d postgres:16  # Docker"
    exit 1
fi
echo -e "${GREEN}✓ PostgreSQL is running${NC}"

# Check Redis
echo -e "${YELLOW}Checking Redis...${NC}"
if ! redis-cli ping &> /dev/null 2>&1; then
    echo -e "${RED}❌ Redis is not running!${NC}"
    echo ""
    echo "Start Redis with one of these commands:"
    echo "  brew services start redis          # macOS with Homebrew"
    echo "  sudo systemctl start redis         # Linux with systemd"
    echo "  docker run --name raffle-redis -p 6379:6379 -d redis:7  # Docker"
    exit 1
fi
echo -e "${GREEN}✓ Redis is running${NC}"

# Check if database is initialized
echo -e "\n${YELLOW}Checking database...${NC}"
DB_INITIALIZED=false

# Try to connect to database and check for tables
if python3 -c "
import asyncio
import sys
sys.path.insert(0, '.')
from app.config import settings
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def check():
    try:
        engine = create_async_engine(settings.DATABASE_URL)
        async with engine.connect() as conn:
            result = await conn.execute(text(\"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public'\"))
            count = result.scalar()
            await engine.dispose()
            return count > 0
    except:
        return False

result = asyncio.run(check())
sys.exit(0 if result else 1)
" 2>/dev/null; then
    DB_INITIALIZED=true
fi

if [ "$DB_INITIALIZED" = false ]; then
    echo -e "${YELLOW}⚠️  Database not initialized${NC}"
    echo -e "${YELLOW}Initializing database...${NC}"
    python scripts/init_db.py
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Database initialization failed!${NC}"
        exit 1
    fi
fi
echo -e "${GREEN}✓ Database is ready${NC}"

# Start the bot
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Starting bot...${NC}"
echo -e "${GREEN}========================================${NC}\n"

# Run with automatic restart on crash
while true; do
    python app/main.py
    EXIT_CODE=$?

    if [ $EXIT_CODE -eq 0 ] || [ $EXIT_CODE -eq 130 ]; then
        # Clean exit or Ctrl+C
        echo -e "\n${GREEN}Bot stopped${NC}"
        break
    else
        echo -e "\n${RED}Bot crashed with exit code $EXIT_CODE${NC}"
        echo -e "${YELLOW}Restarting in 5 seconds...${NC}"
        sleep 5
    fi
done
