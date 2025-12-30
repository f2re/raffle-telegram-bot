#!/bin/bash
# Docker Environment Setup Script for Raffle Telegram Bot

set -e

echo "🤖 Raffle Telegram Bot - Docker Setup"
echo "======================================"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo "Please copy .env.example to .env and configure it:"
    echo "  cp .env.example .env"
    echo "  nano .env  # or use your preferred editor"
    exit 1
fi

# Check for required environment variables
echo "🔍 Checking required configuration..."

required_vars=(
    "TELEGRAM_BOT_TOKEN"
    "ADMIN_USER_IDS"
    "TON_CENTER_API_KEY"
    "TON_WALLET_ADDRESS"
    "TON_WALLET_MNEMONIC"
    "TON_CONNECT_MANIFEST_URL"
    "RANDOM_ORG_API_KEY"
)

missing_vars=()

for var in "${required_vars[@]}"; do
    value=$(grep "^${var}=" .env | cut -d'=' -f2)
    if [[ -z "$value" || "$value" == *"your_"* || "$value" == *"xxxxxxxxxx"* ]]; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -gt 0 ]; then
    echo "❌ Missing or incomplete configuration for:"
    for var in "${missing_vars[@]}"; do
        echo "   - $var"
    done
    echo ""
    echo "Please edit .env and configure all required values."
    echo "See README.md section '🔑 Required API Tokens & Configuration' for help."
    exit 1
fi

# Verify Docker configuration
echo "✅ Configuration looks good!"
echo ""
echo "🔍 Verifying Docker setup..."

# Check if REDIS_URL is set correctly for Docker
redis_url=$(grep "^REDIS_URL=" .env | cut -d'=' -f2)
if [[ "$redis_url" != "redis://redis:6379/0" ]]; then
    echo "⚠️  Warning: REDIS_URL should be 'redis://redis:6379/0' for Docker"
    echo "   Current value: $redis_url"
    echo "   Fixing..."
    sed -i 's|^REDIS_URL=.*|REDIS_URL=redis://redis:6379/0|' .env
    echo "✅ Fixed REDIS_URL"
fi

# Check if DATABASE_URL is set correctly for Docker
db_url=$(grep "^DATABASE_URL=" .env | cut -d'=' -f2)
if [[ "$db_url" != *"@postgres:5432/"* ]]; then
    echo "⚠️  Warning: DATABASE_URL should use '@postgres:5432' for Docker"
    echo "   Current value: $db_url"
    echo "   Fixing..."
    sed -i 's|^DATABASE_URL=.*|DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/raffle_bot|' .env
    echo "✅ Fixed DATABASE_URL"
fi

echo ""
echo "🐳 Starting Docker services..."
echo "======================================"

# Stop any existing instances
if docker compose ps | grep -q "Up"; then
    echo "🛑 Stopping existing services..."
    docker compose down
    sleep 3
fi

# Start services
echo "🚀 Starting services..."
docker compose up -d

echo ""
echo "⏳ Waiting for services to be ready..."
sleep 5

# Check service status
echo ""
echo "📊 Service Status:"
docker compose ps

echo ""
echo "✅ Setup complete!"
echo ""
echo "📝 Next steps:"
echo "   1. View logs:    docker compose logs -f bot"
echo "   2. Check status: docker compose ps"
echo "   3. Stop bot:     docker compose down"
echo ""
echo "💡 Important:"
echo "   - Send /start to your bot in Telegram to initialize admin chat"
echo "   - Send at least 10 TON to your wallet: $(grep "^TON_WALLET_ADDRESS=" .env | cut -d'=' -f2)"
echo ""
