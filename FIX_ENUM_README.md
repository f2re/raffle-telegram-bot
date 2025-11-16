# Fix Database Enum for TON Support

## Problem
The database enum `currencytype` doesn't have the 'ton' value yet, causing this error:
```
invalid input value for enum currencytype: "TON"
```

## Solution

Run the SQL script to add 'ton' to the enum:

### Option 1: Using psql command line
```bash
# If you have a local PostgreSQL instance
psql -U your_username -d raffle_bot -f add_ton_enum.sql

# Or if using docker-compose
docker-compose exec postgres psql -U postgres -d raffle_bot -f /path/to/add_ton_enum.sql
```

### Option 2: Using any PostgreSQL client
Connect to your database and run the contents of `add_ton_enum.sql`

### Option 3: Run this Python script (from your venv)
```bash
# Activate your virtual environment first
source venv/bin/activate  # or: . venv/bin/activate

# Then run:
python3 << 'EOF'
import asyncio
from sqlalchemy import text
from app.database.session import get_db_engine

async def fix():
    engine = get_db_engine()
    async with engine.begin() as conn:
        await conn.execute(text("""
            DO $$ BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_enum e
                    JOIN pg_type t ON e.enumtypid = t.oid
                    WHERE t.typname = 'currencytype' AND e.enumlabel = 'ton'
                ) THEN
                    ALTER TYPE currencytype ADD VALUE 'ton';
                END IF;
            END $$;
        """))
    await engine.dispose()
    print("✅ Fixed!")

asyncio.run(fix())
EOF
```

### Option 4: Quick fix using psql
```bash
# Replace with your actual database connection details
PGPASSWORD=your_password psql -h localhost -p 5432 -U your_user -d raffle_bot -c \
  "ALTER TYPE currencytype ADD VALUE IF NOT EXISTS 'ton';"
```

## After fixing
Once you've added the 'ton' enum value, restart your bot and try creating a raffle again.
