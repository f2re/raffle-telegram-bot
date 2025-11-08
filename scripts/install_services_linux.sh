#!/bin/bash
# Install PostgreSQL and Redis on Ubuntu/Debian

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}📦 Installing services on Linux...${NC}\n"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run as root (use sudo)${NC}"
    exit 1
fi

# Update package list
echo -e "${YELLOW}Updating package list...${NC}"
apt-get update

# Install PostgreSQL
echo ""
echo -e "${YELLOW}Installing PostgreSQL...${NC}"
if command -v psql &> /dev/null; then
    echo -e "${GREEN}✓ PostgreSQL already installed${NC}"
else
    apt-get install -y postgresql postgresql-contrib
    echo -e "${GREEN}✓ PostgreSQL installed${NC}"
fi

# Install Redis
echo ""
echo -e "${YELLOW}Installing Redis...${NC}"
if command -v redis-server &> /dev/null; then
    echo -e "${GREEN}✓ Redis already installed${NC}"
else
    apt-get install -y redis-server
    echo -e "${GREEN}✓ Redis installed${NC}"
fi

# Start services
echo ""
echo -e "${YELLOW}Starting services...${NC}"

systemctl start postgresql
systemctl enable postgresql
echo -e "${GREEN}✓ PostgreSQL started and enabled${NC}"

systemctl start redis
systemctl enable redis
echo -e "${GREEN}✓ Redis started and enabled${NC}"

# Wait for services to be ready
echo ""
echo -e "${YELLOW}Waiting for services to be ready...${NC}"
sleep 3

# Configure PostgreSQL for local development
echo ""
echo -e "${YELLOW}Configuring PostgreSQL...${NC}"

# Create postgres user password
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'postgres';" || true

# Allow password authentication
PG_HBA="/etc/postgresql/$(ls /etc/postgresql | head -1)/main/pg_hba.conf"
if [ -f "$PG_HBA" ]; then
    # Backup original
    cp "$PG_HBA" "$PG_HBA.backup"

    # Update authentication method
    sed -i 's/local   all             postgres                                peer/local   all             postgres                                md5/' "$PG_HBA"
    sed -i 's/host    all             all             127.0.0.1\/32            scram-sha-256/host    all             all             127.0.0.1\/32            md5/' "$PG_HBA"

    # Reload PostgreSQL
    systemctl reload postgresql
    echo -e "${GREEN}✓ PostgreSQL configured${NC}"
fi

# Verify services
echo ""
if systemctl is-active --quiet postgresql; then
    echo -e "${GREEN}✓ PostgreSQL is running${NC}"
else
    echo -e "${RED}✗ PostgreSQL is not running${NC}"
fi

if systemctl is-active --quiet redis; then
    echo -e "${GREEN}✓ Redis is running${NC}"
else
    echo -e "${RED}✗ Redis is not running${NC}"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Installation complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Services are now running and will start automatically on boot."
echo ""
echo "To check status:"
echo "  systemctl status postgresql"
echo "  systemctl status redis"
echo ""
echo "To stop services:"
echo "  systemctl stop postgresql"
echo "  systemctl stop redis"
echo ""
echo "To restart services:"
echo "  systemctl restart postgresql"
echo "  systemctl restart redis"
