#!/bin/bash
# Local development setup script

set -e

echo "🚀 Setting up Telegram Raffle Bot for local development..."

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Python version
echo -e "\n${YELLOW}Checking Python version...${NC}"
python_version=$(python3 --version 2>&1 | grep -oP '(?<=Python )\d+\.\d+')
required_version="3.11"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python 3.11+ is required. You have Python $python_version"
    exit 1
fi
echo -e "${GREEN}✓ Python $python_version${NC}"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo -e "\n${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "\n${GREEN}✓ Virtual environment already exists${NC}"
fi

# Activate virtual environment
echo -e "\n${YELLOW}Activating virtual environment...${NC}"
source venv/bin/activate

# Upgrade pip
echo -e "\n${YELLOW}Upgrading pip...${NC}"
pip install --upgrade pip

# Install dependencies
echo -e "\n${YELLOW}Installing dependencies...${NC}"
pip install -r requirements.txt
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo -e "\n${YELLOW}Creating .env file from template...${NC}"
    cp .env.example .env
    echo -e "${GREEN}✓ .env file created${NC}"
    echo -e "${YELLOW}⚠️  Please edit .env file with your credentials!${NC}"
else
    echo -e "\n${GREEN}✓ .env file already exists${NC}"
fi

# Create logs directory
mkdir -p logs
echo -e "${GREEN}✓ Logs directory created${NC}"

# Check PostgreSQL
echo -e "\n${YELLOW}Checking PostgreSQL...${NC}"
if command -v psql &> /dev/null; then
    echo -e "${GREEN}✓ PostgreSQL is installed${NC}"

    # Check if PostgreSQL is running
    if pg_isready &> /dev/null; then
        echo -e "${GREEN}✓ PostgreSQL is running${NC}"
    else
        echo -e "${YELLOW}⚠️  PostgreSQL is not running. Please start it:${NC}"
        echo "  brew services start postgresql@16  # macOS with Homebrew"
        echo "  sudo systemctl start postgresql    # Linux with systemd"
    fi
else
    echo -e "${YELLOW}⚠️  PostgreSQL is not installed. Please install it:${NC}"
    echo "  macOS: brew install postgresql@16"
    echo "  Ubuntu: sudo apt-get install postgresql postgresql-contrib"
    echo "  Or use Docker: docker run --name raffle-postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 -d postgres:16"
fi

# Check Redis
echo -e "\n${YELLOW}Checking Redis...${NC}"
if command -v redis-cli &> /dev/null; then
    echo -e "${GREEN}✓ Redis is installed${NC}"

    # Check if Redis is running
    if redis-cli ping &> /dev/null 2>&1; then
        echo -e "${GREEN}✓ Redis is running${NC}"
    else
        echo -e "${YELLOW}⚠️  Redis is not running. Please start it:${NC}"
        echo "  brew services start redis  # macOS with Homebrew"
        echo "  sudo systemctl start redis # Linux with systemd"
    fi
else
    echo -e "${YELLOW}⚠️  Redis is not installed. Please install it:${NC}"
    echo "  macOS: brew install redis"
    echo "  Ubuntu: sudo apt-get install redis-server"
    echo "  Or use Docker: docker run --name raffle-redis -p 6379:6379 -d redis:7"
fi

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Setup complete!${NC}"
echo -e "${GREEN}========================================${NC}"

echo -e "\n${YELLOW}Next steps:${NC}"
echo "1. Edit .env file with your credentials:"
echo "   - TELEGRAM_BOT_TOKEN (from @BotFather)"
echo "   - ADMIN_USER_ID (your Telegram user ID from @userinfobot)"
echo "   - RANDOM_ORG_API_KEY (from https://api.random.org/)"
echo ""
echo "2. Make sure PostgreSQL and Redis are running"
echo ""
echo "3. Initialize the database:"
echo "   python scripts/init_db.py"
echo ""
echo "4. Start the bot:"
echo "   python app/main.py"
echo ""
echo "Or use the quick start script:"
echo "   ./scripts/run.sh"
