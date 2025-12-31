#!/bin/bash
set -e

echo "======================================"
echo "Starting Raffle Bot & Backend"
echo "======================================"

# Copy built frontend to static volume (for nginx)
if [ -d "/app/static-built" ]; then
    echo "Copying built frontend to /app/static..."
    rsync -av --delete /app/static-built/ /app/static/
    echo "Frontend files copied successfully"
    echo "Files in /app/static:"
    ls -lah /app/static/
else
    echo "WARNING: /app/static-built not found!"
fi

# Ensure tonconnect-manifest.json is accessible
if [ -f "/app/static/tonconnect-manifest.json" ]; then
    echo "✅ TON Connect manifest found"
else
    echo "⚠️  WARNING: tonconnect-manifest.json not found in static!"
fi

# Display environment info
echo "======================================"
echo "Environment Configuration:"
echo "======================================"
echo "PORT: ${PORT:-8000}"
echo "PYTHONPATH: ${PYTHONPATH}"
echo "BOT_NAME: ${BOT_NAME}"
echo "======================================"

echo "Starting services..."
echo "======================================"

# Execute the command
exec "$@"
