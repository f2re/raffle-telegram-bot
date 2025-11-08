#!/bin/bash
# Install PostgreSQL and Redis on macOS using Homebrew

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🍺 Installing services using Homebrew...${NC}\n"

# Check if Homebrew is installed
if ! command -v brew &> /dev/null; then
    echo -e "${RED}❌ Homebrew is not installed!${NC}"
    echo ""
    echo "Install Homebrew first:"
    echo '  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
    exit 1
fi

echo -e "${GREEN}✓ Homebrew is installed${NC}\n"

# Install PostgreSQL
echo -e "${YELLOW}Installing PostgreSQL 16...${NC}"
if command -v psql &> /dev/null; then
    echo -e "${GREEN}✓ PostgreSQL already installed${NC}"
else
    brew install postgresql@16
    echo -e "${GREEN}✓ PostgreSQL installed${NC}"
fi

# Install Redis
echo ""
echo -e "${YELLOW}Installing Redis...${NC}"
if command -v redis-server &> /dev/null; then
    echo -e "${GREEN}✓ Redis already installed${NC}"
else
    brew install redis
    echo -e "${GREEN}✓ Redis installed${NC}"
fi

# Start services
echo ""
echo -e "${YELLOW}Starting services...${NC}"

brew services start postgresql@16
echo -e "${GREEN}✓ PostgreSQL started${NC}"

brew services start redis
echo -e "${GREEN}✓ Redis started${NC}"

# Wait for services to be ready
echo ""
echo -e "${YELLOW}Waiting for services to be ready...${NC}"
sleep 3

# Verify services
echo ""
if pg_isready &> /dev/null; then
    echo -e "${GREEN}✓ PostgreSQL is running${NC}"
else
    echo -e "${RED}✗ PostgreSQL failed to start${NC}"
fi

if redis-cli ping &> /dev/null 2>&1; then
    echo -e "${GREEN}✓ Redis is running${NC}"
else
    echo -e "${RED}✗ Redis failed to start${NC}"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Installation complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Services are now running and will start automatically on boot."
echo ""
echo "To stop services:"
echo "  brew services stop postgresql@16"
echo "  brew services stop redis"
echo ""
echo "To restart services:"
echo "  brew services restart postgresql@16"
echo "  brew services restart redis"
