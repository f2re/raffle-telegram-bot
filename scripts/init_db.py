#!/usr/bin/env python3
"""
Database initialization script for local development
Creates database tables and initial data
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from sqlalchemy import text

from app.database.session import engine, init_db
from app.config import settings


async def create_database():
    """Create database if it doesn't exist"""
    # Extract database name from URL
    db_url = str(settings.DATABASE_URL)

    if "postgresql" in db_url:
        # Parse connection details
        try:
            from urllib.parse import urlparse
            parsed = urlparse(db_url.replace("+asyncpg", ""))
            db_name = parsed.path.lstrip('/')

            # Create connection to postgres database
            server_url = db_url.rsplit('/', 1)[0] + '/postgres'

            from sqlalchemy.ext.asyncio import create_async_engine
            server_engine = create_async_engine(server_url, isolation_level="AUTOCOMMIT")

            async with server_engine.connect() as conn:
                # Check if database exists
                result = await conn.execute(
                    text(f"SELECT 1 FROM pg_database WHERE datname='{db_name}'")
                )
                exists = result.scalar()

                if not exists:
                    logger.info(f"Creating database: {db_name}")
                    await conn.execute(text(f"CREATE DATABASE {db_name}"))
                    logger.success(f"Database {db_name} created successfully")
                else:
                    logger.info(f"Database {db_name} already exists")

            await server_engine.dispose()

        except Exception as e:
            logger.warning(f"Could not create database automatically: {e}")
            logger.info("Please create the database manually:")
            logger.info(f"  CREATE DATABASE {db_name};")


async def main():
    """Main initialization function"""
    logger.info("Starting database initialization...")

    # Step 1: Create database if needed
    await create_database()

    # Step 2: Create tables
    logger.info("Creating database tables...")
    try:
        await init_db()
        logger.success("Database tables created successfully!")
    except Exception as e:
        logger.error(f"Failed to create tables: {e}")
        sys.exit(1)

    # Step 3: Verify tables
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname='public'")
        )
        tables = [row[0] for row in result]

        logger.info(f"Created tables: {', '.join(tables)}")

    logger.success("Database initialization complete!")
    logger.info("You can now start the bot with: python app/main.py")


if __name__ == "__main__":
    asyncio.run(main())
