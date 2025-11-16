#!/usr/bin/env python3
"""
Manual enum fix script for TON currency support

This script directly connects to PostgreSQL and adds the 'ton' value
to the currencytype enum using autocommit mode.

Run this if the automatic database initialization isn't working.

Usage:
    python fix_ton_enum.py
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncpg
from loguru import logger
from app.config import settings


async def fix_ton_enum():
    """Manually add 'ton' value to currencytype enum"""

    # Parse database URL for asyncpg
    db_url = settings.DATABASE_URL.replace('postgresql+asyncpg://', 'postgresql://')

    logger.info(f"Connecting to database...")
    logger.info(f"Database URL: {db_url.split('@')[1] if '@' in db_url else 'hidden'}")

    try:
        # Connect directly with asyncpg (has autocommit by default)
        conn = await asyncpg.connect(db_url)

        logger.info("Connected successfully!")

        # Check if 'ton' value exists
        ton_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 FROM pg_enum e
                JOIN pg_type t ON e.enumtypid = t.oid
                WHERE t.typname = 'currencytype' AND e.enumlabel = 'ton'
            )
        """)

        if ton_exists:
            logger.info("✅ 'ton' value already exists in currencytype enum")
            logger.info("No fix needed!")
        else:
            logger.warning("'ton' value is missing from currencytype enum")
            logger.info("Adding 'ton' value now...")

            # This runs in autocommit mode by default with asyncpg
            await conn.execute("ALTER TYPE currencytype ADD VALUE 'ton'")

            logger.success("✅ Successfully added 'ton' value to currencytype enum!")
            logger.info("The bot should now work correctly with TON currency")

        # Verify
        values = await conn.fetch("""
            SELECT e.enumlabel
            FROM pg_enum e
            JOIN pg_type t ON e.enumtypid = t.oid
            WHERE t.typname = 'currencytype'
            ORDER BY e.enumsortorder
        """)

        logger.info(f"Current currencytype enum values: {[row['enumlabel'] for row in values]}")

        await conn.close()
        logger.info("Done!")

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    logger.remove()
    logger.add(sys.stderr, level="INFO")

    print("=" * 80)
    print("FIX TON ENUM - Manual Database Repair")
    print("=" * 80)
    print()

    asyncio.run(fix_ton_enum())
