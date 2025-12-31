# ============================================
# Stage 1: Build Vue Frontend
# ============================================
FROM node:20-alpine AS frontend-builder

ARG CACHEBUST=1
ARG VITE_API_URL
ARG VITE_WS_URL
ARG VITE_BOT_USERNAME
ARG VITE_TON_WALLET_ADDRESS
ARG VITE_TON_CONNECT_MANIFEST_URL

WORKDIR /frontend

# Install dependencies
COPY frontend/package*.json ./
RUN npm ci --only=production || npm install

# Set environment variables for build
ENV VITE_API_URL=${VITE_API_URL}
ENV VITE_WS_URL=${VITE_WS_URL}
ENV VITE_BOT_USERNAME=${VITE_BOT_USERNAME}
ENV VITE_TON_WALLET_ADDRESS=${VITE_TON_WALLET_ADDRESS}
ENV VITE_TON_CONNECT_MANIFEST_URL=${VITE_TON_CONNECT_MANIFEST_URL}

# Debug output
RUN echo "==========================================" && \
    echo "Building frontend with variables:" && \
    echo "==========================================" && \
    env | grep VITE_ | sort && \
    echo "=========================================="

# Copy source and build
COPY frontend/ ./
RUN npm run build

# Verify build
RUN ls -lah /frontend/dist/ && \
    test -f /frontend/dist/index.html || (echo "ERROR: Build failed - index.html not found!" && exit 1)

# ============================================
# Stage 2: Backend + Bot Runtime
# ============================================
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        tree \
        curl && \
    rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY backend/requirements.txt ./backend/
COPY requirements.txt ./bot/
RUN pip install --no-cache-dir -r backend/requirements.txt && \
    pip install --no-cache-dir -r bot/requirements.txt && \
    pip install --no-cache-dir 'uvicorn[standard]' websockets

# Copy backend code
COPY backend/ ./backend/

# Copy bot code
COPY app/ ./bot/

# Copy built frontend from stage 1
COPY --from=frontend-builder /frontend/dist /app/static-built

# Verify frontend files
RUN echo "Verifying built frontend files..." && \
    ls -lah /app/static-built/ && \
    test -f /app/static-built/index.html || (echo "ERROR: Frontend files not copied!" && exit 1)

# Create necessary directories
RUN mkdir -p /app/logs /app/data /app/static

# Copy entrypoint script
COPY backend/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Environment
ENV PORT=8000
ENV PYTHONPATH=/app/backend:/app/bot
ENV PYTHONUNBUFFERED=1

EXPOSE ${PORT}

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT} & python -u bot/main.py"]
