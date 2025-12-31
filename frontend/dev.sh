#!/bin/bash

echo "=========================================="
echo "Starting Frontend Development Server"
echo "=========================================="

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
fi

# Create .env.local if it doesn't exist
if [ ! -f ".env.local" ]; then
    echo "Creating .env.local..."
    cat > .env.local << EOF
VITE_API_URL=http://localhost:8000/api
VITE_WS_URL=ws://localhost:8000/ws
VITE_BOT_USERNAME=test_bot
VITE_TON_WALLET_ADDRESS=UQTest...
VITE_TON_CONNECT_MANIFEST_URL=http://localhost:5173/tonconnect-manifest.json
EOF
    echo "✓ .env.local created"
    echo "Edit .env.local to customize development settings"
fi

echo ""
echo "Starting Vite dev server..."
echo "Mini App will be available at: http://localhost:5173"
echo ""
echo "Note: To test with Telegram WebApp API, you'll need ngrok:"
echo "  ngrok http 5173"
echo ""

npm run dev
