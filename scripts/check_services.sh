#!/bin/bash
# Check if required services are running

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🔍 Checking required services..."
echo ""

# Check PostgreSQL
echo -n "PostgreSQL: "
if pg_isready &> /dev/null; then
    echo -e "${GREEN}✓ Running${NC}"
    PG_VERSION=$(psql --version | grep -oP '\d+\.\d+' | head -1)
    echo "  Version: $PG_VERSION"
else
    echo -e "${RED}✗ Not running${NC}"
    echo ""
    echo "  Start PostgreSQL:"
    echo "    macOS: brew services start postgresql@16"
    echo "    Linux: sudo systemctl start postgresql"
    echo "    Docker: docker run --name raffle-postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 -d postgres:16"
fi

echo ""

# Check Redis
echo -n "Redis: "
if redis-cli ping &> /dev/null 2>&1; then
    echo -e "${GREEN}✓ Running${NC}"
    REDIS_VERSION=$(redis-cli --version | grep -oP '\d+\.\d+\.\d+' | head -1)
    echo "  Version: $REDIS_VERSION"
else
    echo -e "${RED}✗ Not running${NC}"
    echo ""
    echo "  Start Redis:"
    echo "    macOS: brew services start redis"
    echo "    Linux: sudo systemctl start redis"
    echo "    Docker: docker run --name raffle-redis -p 6379:6379 -d redis:7"
fi

echo ""

# Check Python
echo -n "Python: "
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | grep -oP '\d+\.\d+\.\d+')
    echo -e "${GREEN}✓ Installed${NC}"
    echo "  Version: $PYTHON_VERSION"
else
    echo -e "${RED}✗ Not installed${NC}"
fi

echo ""

# Check virtual environment
echo -n "Virtual environment: "
if [ -d "venv" ]; then
    echo -e "${GREEN}✓ Created${NC}"

    if [ -n "$VIRTUAL_ENV" ]; then
        echo "  Status: Activated"
    else
        echo -e "  Status: ${YELLOW}Not activated${NC}"
        echo "  Activate with: source venv/bin/activate"
    fi
else
    echo -e "${RED}✗ Not created${NC}"
    echo "  Create with: python3 -m venv venv"
fi

echo ""

# Check .env file
echo -n ".env file: "
if [ -f ".env" ]; then
    echo -e "${GREEN}✓ Exists${NC}"

    # Check if it has required variables
    if grep -q "your_telegram_bot_token_here" .env; then
        echo -e "  ${YELLOW}⚠️  Contains placeholder values${NC}"
        echo "  Please edit .env with real credentials"
    else
        echo "  Status: Configured"
    fi
else
    echo -e "${RED}✗ Not found${NC}"
    echo "  Create with: cp .env.example .env"
fi

echo ""
echo "=========================================="
