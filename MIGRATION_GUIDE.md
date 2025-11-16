# Database Migration Guide

This guide explains how to apply database migrations to update your database schema.

## When do you need to run migrations?

You need to run migrations when:
- You see error messages about missing columns (e.g., `column users.balance_ton does not exist`)
- After pulling new code that includes database schema changes
- The bot fails to start with a "Database schema is outdated" error

## Quick Fix

### For local development (macOS/Linux/Windows):

```bash
# Activate your virtual environment first
source venv/bin/activate  # On macOS/Linux
# OR
venv\Scripts\activate  # On Windows

# Run migrations
alembic upgrade head
```

### For Docker deployment:

```bash
docker-compose run bot alembic upgrade head
```

## Detailed Steps

### 1. Check if migrations are needed

```bash
# Check current database version
alembic current

# Check pending migrations
alembic history
```

### 2. Apply all pending migrations

```bash
alembic upgrade head
```

### 3. Verify the migration

Start the bot and check for errors:

```bash
python app/main.py
```

If successful, you should see:
```
Database initialized successfully
Database schema validation passed
```

## Common Issues

### Issue: `alembic: command not found`

**Solution:** Install alembic in your virtual environment:

```bash
pip install alembic
```

### Issue: Database connection error

**Solution:** Make sure your `.env` file has the correct `DATABASE_URL`:

```
DATABASE_URL=postgresql+asyncpg://username:password@localhost:5432/raffle_bot
```

### Issue: Migration fails with constraint errors

**Solution:** Check your database state. You may need to:

1. Backup your database first:
   ```bash
   pg_dump raffle_bot > backup.sql
   ```

2. Try the migration again:
   ```bash
   alembic upgrade head
   ```

3. If it still fails, check the specific migration file in `migrations/versions/` for manual fixes needed

## Available Migrations

- **20251108_add_payout_requests**: Adds payout request tracking
- **20251108_add_withdrawal_requests**: Adds withdrawal request system
- **20251116_add_ton_support**: Adds TON cryptocurrency support (balance_ton, ton_wallet_address columns)

## Rolling Back Migrations

If you need to undo a migration:

```bash
# Roll back one migration
alembic downgrade -1

# Roll back to a specific version
alembic downgrade <revision_id>
```

## Creating New Migrations

If you modify the database models, create a new migration:

```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "description of changes"

# Review the generated file in migrations/versions/
# Then apply it
alembic upgrade head
```

## Support

If you encounter issues not covered here, check:
1. The error logs for specific details
2. The migration files in `migrations/versions/` for requirements
3. PostgreSQL documentation for database-specific issues
