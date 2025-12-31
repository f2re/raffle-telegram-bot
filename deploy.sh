#!/bin/bash

set -e

echo "=========================================="
echo "Raffle Bot Mini App Deployment Script"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${RED}Error: .env file not found!${NC}"
    echo "Please copy .env.example to .env and configure it:"
    echo "  cp .env.example .env"
    echo "  nano .env"
    exit 1
fi

# Load environment variables
source .env

# Check required variables
required_vars=(
    "TELEGRAM_BOT_TOKEN"
    "TON_WALLET_ADDRESS"
    "VITE_API_URL"
    "VITE_BOT_USERNAME"
    "MINI_APP_URL"
)

missing_vars=0
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo -e "${RED}Error: $var is not set in .env${NC}"
        missing_vars=1
    fi
done

if [ $missing_vars -eq 1 ]; then
    echo -e "${RED}Please configure all required variables in .env${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Environment variables validated${NC}"

# Create necessary directories
echo "Creating directories..."
mkdir -p logs data static
echo -e "${GREEN}✓ Directories created${NC}"

# Increment cache buster for fresh build
if [ -z "$CACHEBUST" ]; then
    export CACHEBUST=1
else
    export CACHEBUST=$((CACHEBUST + 1))
fi
echo "CACHEBUST=$CACHEBUST" >> .env
echo -e "${GREEN}✓ Cache buster incremented to $CACHEBUST${NC}"

# Build Docker images
echo ""
echo "=========================================="
echo "Building Docker images..."
echo "=========================================="
docker-compose build --no-cache

if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Docker build failed!${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker build completed${NC}"

# Stop existing containers
echo ""
echo "Stopping existing containers..."
docker-compose down
echo -e "${GREEN}✓ Containers stopped${NC}"

# Start containers
echo ""
echo "=========================================="
echo "Starting containers..."
echo "=========================================="
docker-compose up -d

if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Failed to start containers!${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Containers started${NC}"

# Wait for services to be ready
echo ""
echo "Waiting for services to be ready..."
sleep 5

# Check if backend is healthy
echo "Checking backend health..."
for i in {1..10}; do
    if curl -s http://localhost:${BACKEND_PORT:-8000}/api/health > /dev/null; then
        echo -e "${GREEN}✓ Backend is healthy${NC}"
        break
    fi
    if [ $i -eq 10 ]; then
        echo -e "${YELLOW}Warning: Backend health check failed${NC}"
        echo "Check logs with: docker-compose logs -f bot"
    fi
    sleep 2
done

# Check if static files were built
echo ""
echo "Checking frontend build..."
if [ -f "./static/index.html" ]; then
    echo -e "${GREEN}✓ Frontend build successful${NC}"
    echo "Files in static directory:"
    ls -lh ./static/ | head -10
else
    echo -e "${RED}Error: Frontend build failed - index.html not found!${NC}"
    echo "Check build logs:"
    docker-compose logs bot | grep -A 20 "Building frontend"
    exit 1
fi

# Display status
echo ""
echo "=========================================="
echo "Deployment Status"
echo "=========================================="
docker-compose ps

echo ""
echo "=========================================="
echo "Deployment Summary"
echo "=========================================="
echo -e "${GREEN}✓ Deployment completed successfully!${NC}"
echo ""
echo "Services:"
echo "  - Bot: Running"
echo "  - Backend API: http://localhost:${BACKEND_PORT:-8000}"
echo "  - Mini App: ${MINI_APP_URL}"
echo ""
echo "Next steps:"
echo "  1. Configure nginx if not already done (see nginx.conf)"
echo "  2. Test the Mini App: ${MINI_APP_URL}"
echo "  3. Send /start to your bot and click 'Открыть Mini App'"
echo ""
echo "Useful commands:"
echo "  - View logs: docker-compose logs -f bot"
echo "  - Restart: docker-compose restart"
echo "  - Stop: docker-compose down"
echo ""
echo -e "${GREEN}Happy raffling! 🎉${NC}"
