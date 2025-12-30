# Docker Deployment Troubleshooting

This guide helps resolve common issues when deploying the bot with Docker.

## Prerequisites Checklist

Before troubleshooting, ensure:

- [ ] `.env` file exists and is properly configured
- [ ] All required API tokens are set (see README.md)
- [ ] Docker and Docker Compose are installed
- [ ] No other instances of the bot are running

## Common Issues and Solutions

### 1. Redis Connection Error

**Error:**
```
ERROR | Failed to generate connection URL: Error -2 connecting to redis:6379.
Name or service not known.
```

**Cause:** Bot container cannot resolve Redis hostname in Docker network.

**Solutions:**

#### A. Check `.env` Configuration
```bash
# Ensure REDIS_URL is set correctly for Docker:
grep REDIS_URL .env
```

Should show: `REDIS_URL=redis://redis:6379/0`

If it shows `localhost` instead of `redis`, fix it:
```bash
sed -i 's|redis://localhost|redis://redis|' .env
docker compose restart bot
```

#### B. Verify Services Are Running
```bash
docker compose ps
```

All services should show "Up" status. If Redis is not running:
```bash
docker compose up -d redis
docker compose logs redis
```

#### C. Check Docker Network
```bash
# Verify all services are on the same network
docker network inspect raffle-telegram-bot_raffle_network
```

If network doesn't exist, recreate it:
```bash
docker compose down
docker compose up -d
```

#### D. Restart Services in Correct Order
```bash
# Stop all services
docker compose down

# Wait 5 seconds
sleep 5

# Start infrastructure first
docker compose up -d postgres redis

# Wait for them to be healthy
sleep 10

# Start bot
docker compose up -d bot
```

---

### 2. Multiple Bot Instances Conflict

**Error:**
```
TelegramConflictError: Conflict: terminated by other getUpdates request
```

**Cause:** Multiple bot instances running with the same token.

**Solution:**

```bash
# 1. Stop Docker instance
docker compose down

# 2. Find and kill any local instances
pkill -f "python.*raffle"
ps aux | grep raffle  # Verify all killed

# 3. Wait for Telegram API to release the session
sleep 15

# 4. Start only ONE instance
docker compose up -d

# 5. Verify only one instance running
docker compose ps
ps aux | grep raffle
```

**Prevention:** Never run `python app/main.py` manually while Docker is running.

---

### 3. Permission Denied for Logs

**Error:**
```
PermissionError: [Errno 13] Permission denied: '/app/logs/bot_2025-XX-XX.log'
```

**Cause:** Log directory ownership mismatch.

**Solution:** This is already fixed in the latest version with graceful fallback to stdout. Update your code:

```bash
git pull origin main
docker compose build --no-cache bot
docker compose up -d bot
```

Logs will now go to stdout/stderr instead of files (Docker best practice).

---

### 4. Module Import Errors

**Error:**
```
ModuleNotFoundError: No module named 'app'
```

**Cause:** Incorrect Python path in container.

**Solution:** This is fixed in the latest Dockerfile. Rebuild:

```bash
docker compose build --no-cache bot
docker compose up -d bot
```

---

### 5. Database Connection Failed

**Error:**
```
could not connect to server: Connection refused
```

**Cause:** PostgreSQL not ready when bot starts.

**Solution:**

```bash
# Check PostgreSQL health
docker compose ps postgres

# View PostgreSQL logs
docker compose logs postgres

# If unhealthy, restart it
docker compose restart postgres

# Wait for healthy status
docker compose ps postgres

# Then restart bot
docker compose restart bot
```

---

### 6. TON Wallet Balance is Zero

**Warning:**
```
WARNING | TON wallet balance (0.0000) is below minimum reserve (10.0 TON)
```

**Cause:** Bot wallet has no funds for winner payouts.

**Solution:**

```bash
# Get your bot's wallet address from .env
grep TON_WALLET_ADDRESS .env

# Send 10-20 TON to this address from your personal wallet
# Wait 1-2 minutes for confirmation
# Check balance in bot logs
```

---

### 7. Admin Chat Not Found

**Warning:**
```
WARNING | Failed to notify admin - chat not found
```

**Cause:** Admin hasn't started conversation with bot.

**Solution:**

1. Open Telegram
2. Find your bot (search by username)
3. Send `/start` command
4. Bot will now be able to send you notifications

---

### 8. TON Liteserver Sync Issues

**Error:**
```
Liteserver crashed with 651 code. Message: cannot load block
```

**Cause:** TON liteserver temporarily out of sync.

**Impact:** Low - transaction monitoring will retry automatically.

**Solution:** Usually resolves itself within 1-5 minutes. If persistent:

```bash
docker compose restart bot
```

---

## Diagnostic Commands

### Check All Service Logs
```bash
docker compose logs -f
```

### Check Specific Service
```bash
docker compose logs -f bot
docker compose logs -f postgres
docker compose logs -f redis
```

### Verify Environment Variables
```bash
docker compose exec bot env | grep -E "REDIS_URL|DATABASE_URL|TON_"
```

### Test Redis Connection Manually
```bash
docker compose exec redis redis-cli ping
# Should return: PONG
```

### Test PostgreSQL Connection
```bash
docker compose exec postgres psql -U postgres -d raffle_bot -c "SELECT 1;"
# Should return: 1
```

### Restart Single Service
```bash
docker compose restart bot
```

### Rebuild and Restart
```bash
docker compose down
docker compose build --no-cache
docker compose up -d
```

### View Resource Usage
```bash
docker stats
```

---

## Complete Reset (Nuclear Option)

If all else fails, completely reset everything:

```bash
# 1. Stop and remove all containers, networks, volumes
docker compose down -v

# 2. Remove any orphaned containers
docker container prune -f

# 3. Remove orphaned networks
docker network prune -f

# 4. Rebuild from scratch
docker compose build --no-cache

# 5. Start fresh
docker compose up -d

# 6. Watch logs
docker compose logs -f bot
```

**⚠️ Warning:** This will delete all data in PostgreSQL and Redis!

---

## Getting Help

If you still have issues after trying these solutions:

1. **Collect logs:**
   ```bash
   docker compose logs > bot-logs.txt
   ```

2. **Check configuration:**
   ```bash
   cat .env | grep -v "SECRET\|TOKEN\|MNEMONIC" > config-sanitized.txt
   ```

3. **Get service status:**
   ```bash
   docker compose ps > services-status.txt
   ```

4. **Create GitHub issue** with:
   - Error message (from logs)
   - Service status
   - Configuration (sanitized - no secrets!)
   - Steps you've already tried

---

## Prevention Tips

1. **Always use the setup script:**
   ```bash
   ./setup-docker.sh
   ```

2. **Use the provided docker-compose commands** instead of running Python directly

3. **Monitor logs regularly:**
   ```bash
   docker compose logs -f bot | grep ERROR
   ```

4. **Keep Docker images updated:**
   ```bash
   docker compose pull
   docker compose up -d
   ```

5. **Backup database regularly:**
   ```bash
   docker compose exec postgres pg_dump -U postgres raffle_bot > backup.sql
   ```
