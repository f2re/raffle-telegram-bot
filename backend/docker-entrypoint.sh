#!/bin/bash
set -e

echo "======================================"
echo "Starting Raffle Bot & Backend"
echo "======================================"

# Clean and copy static files
echo "🗑️  Removing old static files..."
rm -rf /app/static/*

echo "📦 Copying fresh static files from /app/static-built..."
cp -r /app/static-built/* /app/static/ || {
    echo "❌ ERROR: Failed to copy static files"
    exit 1
}

# Verify critical files
if [ ! -f "/app/static/index.html" ]; then
    echo "❌ ERROR: index.html not found after copy!"
    exit 1
fi

echo "✅ Static files updated ($(ls -1 /app/static/ | wc -l) items)"
ls -lh /app/static/

# Verify TON Connect manifest
if [ -f "/app/static/tonconnect-manifest.json" ]; then
    echo "✅ TON Connect manifest found"
else
    echo "⚠️  WARNING: tonconnect-manifest.json not found!"
fi

# Configure ports
export PORT=${BACKEND_PORT:-${PORT:-8000}}

# Display environment info
echo "======================================"
echo "Environment Configuration:"
echo "======================================"
echo "Backend Port: ${PORT}"
echo "Bot Name: ${BOT_NAME}"
echo "Python Path: ${PYTHONPATH}"
echo "======================================"

echo "🚀 Starting services on port ${PORT}..."

# Execute the command
exec "$@"
