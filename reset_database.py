#!/usr/bin/env python3
"""
Database reset script

This script drops all existing tables and enums, then re-creates them from scratch.
USE WITH CAUTION - this will delete all data!

Usage:
    python reset_database.py
"""

import asyncio
import sys
from loguru import logger

from app.database.session import engine
from app.database.init_db import drop_all, init_database


async def main():
    """Reset database by dropping everything and re-creating"""
    print("=" * 80)
    print("DATABASE RESET SCRIPT")
    print("=" * 80)
    print("\nWARNING: This will DELETE ALL DATA in the database!")
    print("This includes all users, raffles, transactions, and settings.\n")

    response = input("Are you sure you want to continue? (yes/no): ")

    if response.lower() not in ['yes', 'y']:
        print("\nOperation cancelled.")
        sys.exit(0)

    print("\nConfirm again by typing 'DELETE ALL DATA': ")
    confirm = input()

    if confirm != 'DELETE ALL DATA':
        print("\nOperation cancelled.")
        sys.exit(0)

    try:
        logger.info("Starting database reset...")

        # Step 1: Drop everything
        print("\n[1/2] Dropping all tables and enums...")
        await drop_all(engine)
        logger.success("✅ All tables and enums dropped")

        # Step 2: Re-create everything
        print("[2/2] Re-creating database from scratch...")
        await init_database(engine)
        logger.success("✅ Database re-created successfully")

        print("\n" + "=" * 80)
        print("DATABASE RESET COMPLETE!")
        print("=" * 80)
        print("\nYour database has been reset to a clean state.")
        print("You can now start the bot with: python app/main.py\n")

    except Exception as e:
        logger.error(f"Database reset failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
