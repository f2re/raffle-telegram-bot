"""
Database initialization module

This module handles database initialization from scratch without migrations.
It creates all necessary PostgreSQL enums and tables.
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from loguru import logger

from .models import Base


async def create_enums(engine: AsyncEngine):
    """
    Create PostgreSQL enum types if they don't exist

    This must be done before creating tables that use these enums
    """
    async with engine.begin() as conn:
        # Drop existing enums if they exist (for clean slate)
        logger.info("Checking and creating PostgreSQL enums...")

        # Create currencytype enum
        await conn.execute(text("""
            DO $$ BEGIN
                CREATE TYPE currencytype AS ENUM ('stars', 'rub', 'ton');
            EXCEPTION
                WHEN duplicate_object THEN
                    -- Type already exists, check if 'ton' value exists
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_enum e
                        JOIN pg_type t ON e.enumtypid = t.oid
                        WHERE t.typname = 'currencytype' AND e.enumlabel = 'ton'
                    ) THEN
                        -- Add 'ton' value if missing
                        ALTER TYPE currencytype ADD VALUE 'ton';
                    END IF;
            END $$;
        """))
        logger.debug("✅ currencytype enum ready")

        # Create rafflestatus enum
        await conn.execute(text("""
            DO $$ BEGIN
                CREATE TYPE rafflestatus AS ENUM ('pending', 'active', 'finished', 'cancelled');
            EXCEPTION
                WHEN duplicate_object THEN NULL;
            END $$;
        """))
        logger.debug("✅ rafflestatus enum ready")

        # Create transactiontype enum
        await conn.execute(text("""
            DO $$ BEGIN
                CREATE TYPE transactiontype AS ENUM ('deposit', 'withdrawal', 'raffle_entry', 'raffle_win', 'refund');
            EXCEPTION
                WHEN duplicate_object THEN NULL;
            END $$;
        """))
        logger.debug("✅ transactiontype enum ready")

        # Create transactionstatus enum
        await conn.execute(text("""
            DO $$ BEGIN
                CREATE TYPE transactionstatus AS ENUM ('pending', 'completed', 'failed', 'cancelled');
            EXCEPTION
                WHEN duplicate_object THEN NULL;
            END $$;
        """))
        logger.debug("✅ transactionstatus enum ready")

        # Create withdrawalstatus enum
        await conn.execute(text("""
            DO $$ BEGIN
                CREATE TYPE withdrawalstatus AS ENUM ('pending', 'approved', 'rejected', 'processing', 'completed', 'failed');
            EXCEPTION
                WHEN duplicate_object THEN NULL;
            END $$;
        """))
        logger.debug("✅ withdrawalstatus enum ready")

        # Create payoutstatus enum
        await conn.execute(text("""
            DO $$ BEGIN
                CREATE TYPE payoutstatus AS ENUM ('pending', 'completed', 'rejected');
            EXCEPTION
                WHEN duplicate_object THEN NULL;
            END $$;
        """))
        logger.debug("✅ payoutstatus enum ready")

        logger.info("All PostgreSQL enums created successfully")


async def init_database(engine: AsyncEngine):
    """
    Initialize database from scratch

    This function:
    1. Creates all PostgreSQL enum types
    2. Creates all tables using SQLAlchemy models
    3. Is idempotent (can be run multiple times safely)
    """
    try:
        logger.info("Initializing database...")

        # Step 1: Create all enum types first
        await create_enums(engine)

        # Step 2: Create all tables
        async with engine.begin() as conn:
            logger.info("Creating database tables...")
            await conn.run_sync(Base.metadata.create_all)
            logger.info("✅ All tables created successfully")

        logger.success("Database initialization completed successfully!")
        return True

    except Exception as e:
        logger.error(f"Database initialization failed: {e}", exc_info=True)
        raise


async def drop_all(engine: AsyncEngine):
    """
    Drop all tables and enums (USE WITH CAUTION!)

    This is useful for development/testing to get a clean slate
    """
    async with engine.begin() as conn:
        logger.warning("Dropping all tables...")
        await conn.run_sync(Base.metadata.drop_all)

        logger.warning("Dropping all enums...")
        await conn.execute(text("DROP TYPE IF EXISTS currencytype CASCADE"))
        await conn.execute(text("DROP TYPE IF EXISTS rafflestatus CASCADE"))
        await conn.execute(text("DROP TYPE IF EXISTS transactiontype CASCADE"))
        await conn.execute(text("DROP TYPE IF EXISTS transactionstatus CASCADE"))
        await conn.execute(text("DROP TYPE IF EXISTS withdrawalstatus CASCADE"))
        await conn.execute(text("DROP TYPE IF EXISTS payoutstatus CASCADE"))

        logger.warning("All tables and enums dropped!")


async def check_db_health(engine: AsyncEngine) -> bool:
    """
    Check if database is healthy and properly initialized

    Returns True if all required tables and enums exist
    """
    try:
        async with engine.begin() as conn:
            # Check if currencytype enum exists and has 'ton' value
            result = await conn.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_type WHERE typname = 'currencytype'
                ) AS enum_exists,
                EXISTS (
                    SELECT 1 FROM pg_enum e
                    JOIN pg_type t ON e.enumtypid = t.oid
                    WHERE t.typname = 'currencytype' AND e.enumlabel = 'ton'
                ) AS ton_exists
            """))
            row = result.fetchone()

            if not row.enum_exists:
                logger.warning("currencytype enum does not exist")
                return False

            if not row.ton_exists:
                logger.warning("'ton' value missing from currencytype enum")
                return False

            # Check if users table exists
            result = await conn.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_name = 'users'
                )
            """))

            if not result.scalar():
                logger.warning("users table does not exist")
                return False

            logger.debug("Database health check passed")
            return True

    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False
