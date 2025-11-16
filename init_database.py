#!/usr/bin/env python3
"""
Database initialization script

This script initializes the database without starting the bot.
Useful for setting up a new database or checking database health.

Usage:
    python init_database.py
"""

import asyncio
import sys
from loguru import logger

from app.database.session import engine
from app.database.init_db import init_database, check_db_health


async def main():
    """Initialize database"""
    try:
        logger.remove()
        logger.add(sys.stderr, level="INFO")

        print("=" * 80)
        print("DATABASE INITIALIZATION")
        print("=" * 80)

        # Check current health
        print("\n[1/2] Checking database health...")
        is_healthy = await check_db_health(engine)

        if is_healthy:
            print("✅ Database is already initialized and healthy!")
            print("\nAll required tables and enums exist.")
            print("TON currency is properly configured.")
        else:
            print("⚠️  Database needs initialization")

            # Initialize
            print("\n[2/2] Initializing database...")
            await init_database(engine)

            print("\n" + "=" * 80)
            print("DATABASE INITIALIZATION COMPLETE!")
            print("=" * 80)

        print("\nYou can now start the bot with: python app/main.py\n")

    except Exception as e:
        logger.error(f"Database initialization failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
