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

    CRITICAL: PostgreSQL does NOT allow adding enum values and using them
    in the same transaction. We must commit after adding enum values.
    """
    # First transaction: Create base enum types
    async with engine.begin() as conn:
        logger.info("Checking and creating PostgreSQL enums...")

        # Create currencytype enum - create new or do nothing if exists
        await conn.execute(text("""
            DO $$ BEGIN
                CREATE TYPE currencytype AS ENUM ('stars', 'rub', 'ton');
            EXCEPTION
                WHEN duplicate_object THEN NULL;
            END $$;
        """))
    # Transaction commits here, enum creation is persisted

    # Second step: Check and add missing values
    # CRITICAL: ALTER TYPE ADD VALUE must run OUTSIDE transaction block (PostgreSQL requirement)
    # We must use raw connection with autocommit
    async with engine.connect() as conn:
        # First check if 'ton' exists (this can be in a transaction)
        result = await conn.execute(text("""
            SELECT EXISTS (
                SELECT 1 FROM pg_enum e
                JOIN pg_type t ON e.enumtypid = t.oid
                WHERE t.typname = 'currencytype' AND e.enumlabel = 'ton'
            )
        """))
        ton_exists = result.scalar()

        if not ton_exists:
            logger.warning("Adding missing 'ton' value to currencytype enum...")
            logger.info("Using autocommit mode (required by PostgreSQL for ALTER TYPE ADD VALUE)")

            # ALTER TYPE ADD VALUE requires autocommit (cannot be in transaction block)
            # We need to commit any pending transaction first, then run with autocommit
            await conn.commit()  # Ensure no open transaction

            # Get raw asyncpg connection for autocommit execution
            raw_conn = await conn.get_raw_connection()
            asyncpg_conn = raw_conn.driver_connection

            try:
                # Execute directly on asyncpg connection (autocommit mode)
                await asyncpg_conn.execute("ALTER TYPE currencytype ADD VALUE 'ton'")
                logger.info("✅ Added 'ton' value to currencytype enum")
            except Exception as e:
                error_msg = str(e).lower()
                # If it fails because value already exists, that's OK
                if "already exists" in error_msg or "duplicate" in error_msg:
                    logger.debug("'ton' value already exists (concurrent add)")
                else:
                    logger.error(f"Failed to add 'ton' enum value: {e}")
                    raise
        else:
            logger.debug("✅ 'ton' value already exists in currencytype enum")

    logger.debug("✅ currencytype enum ready")

    # Third transaction: Create other enum types
    async with engine.begin() as conn:

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


async def init_database(engine: AsyncEngine, force_enum_check: bool = True):
    """
    Initialize database from scratch

    This function:
    1. Creates all PostgreSQL enum types
    2. Creates all tables using SQLAlchemy models
    3. Is idempotent (can be run multiple times safely)

    Args:
        engine: SQLAlchemy async engine
        force_enum_check: If True, always check and fix enums even if tables exist
    """
    try:
        logger.info("Initializing database...")

        # Step 1: Always ensure enums are correct (critical for TON support)
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


async def ensure_enums_updated(engine: AsyncEngine):
    """
    Ensure all enum types have the latest values

    This is useful for updating existing databases without full reinitialization
    """
    try:
        logger.info("Ensuring enum types are up to date...")
        await create_enums(engine)
        logger.success("✅ Enum types updated successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to update enum types: {e}", exc_info=True)
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
