# Quick Fix: Static Directory Empty

## The Problem

The `static/` directory is empty because the container hasn't been built/started yet. Here's what happens:

```
1. Docker builds frontend → /app/static-built/ (inside container)
2. Container starts → Entrypoint copies to /app/static/ (inside container)
3. Volume mount → /app/static/ ← → ./static/ (host)
4. Nginx reads from ./static/ (host)
```

## Solution

### Step 1: Ensure directories exist
```bash
cd /opt/telegram-bots-platform/bots/raffle-telegram
mkdir -p static logs data
```

### Step 2: Check your docker-compose.yml

Your current `docker-compose.yml` shows:
```yaml
context: ./app
```

But it should be:
```yaml
build:
  context: .              # Root directory (where frontend/ and backend/ are)
  dockerfile: backend/Dockerfile   # Path to Dockerfile from context
```

**Fix it:**
```bash
nano docker-compose.yml
```

Change line 40-41 from:
```yaml
build:
  context: ./app
```

To:
```yaml
build:
  context: .
  dockerfile: backend/Dockerfile
```

### Step 3: Build and start

```bash
# Build the image
docker-compose build --no-cache

# Start services
docker-compose up -d

# Check logs
docker-compose logs -f bot
```

You should see output like:
```
🗑️  Removing old static files...
📦 Copying fresh static files from /app/static-built...
✅ Static files updated (12 items)
```

### Step 4: Verify static files

```bash
# Check static directory on host
ls -la ./static/
# Should show: index.html, assets/, tonconnect-manifest.json, etc.

# Check inside container
docker exec raffle_bot ls -la /app/static/
```

## If You Have Custom Structure

If your `frontend/` is inside `app/`, then you need a different Dockerfile.

**Check your structure:**
```bash
ls -la app/
```

If you see `app/frontend/`, then create `app/Dockerfile`:

```dockerfile
# app/Dockerfile
FROM node:20-alpine AS frontend-builder

WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci

ARG VITE_API_URL
ARG VITE_WS_URL
ARG VITE_BOT_USERNAME
ARG VITE_TON_WALLET_ADDRESS
ARG VITE_TON_CONNECT_MANIFEST_URL

ENV VITE_API_URL=${VITE_API_URL}
ENV VITE_WS_URL=${VITE_WS_URL}
ENV VITE_BOT_USERNAME=${VITE_BOT_USERNAME}
ENV VITE_TON_WALLET_ADDRESS=${VITE_TON_WALLET_ADDRESS}
ENV VITE_TON_CONNECT_MANIFEST_URL=${VITE_TON_CONNECT_MANIFEST_URL}

COPY frontend/ ./
RUN npm run build && \
    test -f /frontend/dist/index.html || exit 1

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends tree curl && \
    rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir 'uvicorn[standard]'

COPY backend/ ./backend/
COPY . ./bot/

COPY --from=frontend-builder /frontend/dist /app/static-built

RUN mkdir -p /app/logs /app/data /app/static && \
    test -f /app/static-built/index.html || exit 1

COPY backend/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENV PORT=8000
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT} & python -u bot/main.py"]
```

Then use:
```yaml
build:
  context: ./app
  # No dockerfile specified = looks for ./app/Dockerfile
```

## Quick Test

After build completes:

```bash
# 1. Check container is running
docker ps | grep raffle

# 2. Check static files copied
ls -la ./static/
# Must show files!

# 3. Test backend
curl http://localhost:8000/api/health

# 4. Check entrypoint logs
docker-compose logs bot | grep "Static files updated"
```

## Common Issues

### Issue 1: "static directory empty"
- **Cause**: Container not started, or entrypoint failed
- **Fix**: Check logs: `docker-compose logs bot`

### Issue 2: "index.html not found"
- **Cause**: Frontend build failed
- **Fix**: Check build logs: `docker-compose logs bot | grep "Building frontend"`

### Issue 3: Port already in use
- **Cause**: Old container running
- **Fix**: `docker-compose down && docker-compose up -d`

## Current Project Structure

Based on the files I created, your structure should be:

```
raffle-telegram-bot/
├── app/                    # Telegram bot (Python)
│   ├── handlers/
│   ├── database/
│   └── main.py
├── frontend/               # Vue 3 Mini App
│   ├── src/
│   ├── public/
│   └── package.json
├── backend/                # FastAPI
│   ├── app/
│   ├── Dockerfile          ← Multi-stage build
│   └── docker-entrypoint.sh
├── docker-compose.yml      ← Use context: .
└── static/                 ← Created by container (volume)
```

With this structure, `docker-compose.yml` **must** use:
```yaml
context: .
dockerfile: backend/Dockerfile
```

## Need Help?

Run these diagnostics:

```bash
# Show structure
find . -maxdepth 2 -type d | grep -E "frontend|backend|app|static"

# Show Dockerfile location
find . -name "Dockerfile" -type f

# Show if container exists
docker ps -a | grep raffle

# Show build logs
docker-compose logs bot | head -50
```

Send me the output and I'll help fix the specific issue!
