from contextlib import asynccontextmanager
from typing import AsyncGenerator
import subprocess
import sys

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy import text
from loguru import logger

from app.config import settings
from .models import Base


# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.LOG_LEVEL == "DEBUG",
    poolclass=NullPool,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def run_migrations():
    """
    Run Alembic migrations to bring database up to date

    This function runs 'alembic upgrade head' programmatically
    Returns True if successful, raises exception on failure
    """
    try:
        logger.info("Running database migrations...")

        # Run alembic upgrade head
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            check=True
        )

        logger.info("Database migrations completed successfully")
        logger.debug(f"Migration output: {result.stdout}")

        return True

    except subprocess.CalledProcessError as e:
        logger.error(f"Migration failed with exit code {e.returncode}")
        logger.error(f"STDOUT: {e.stdout}")
        logger.error(f"STDERR: {e.stderr}")
        raise RuntimeError(f"Database migration failed: {e.stderr}")
    except Exception as e:
        logger.error(f"Unexpected error running migrations: {e}")
        raise


async def init_db():
    """Initialize database tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def validate_db_schema():
    """
    Validate that the database schema is up to date

    Checks for required columns that are added via migrations
    Raises an exception with helpful message if schema is outdated
    """
    try:
        async with engine.begin() as conn:
            # First, check and fix the currencytype enum
            # This is a common issue where the migration ran but enum wasn't updated
            logger.info("Checking currencytype enum for 'ton' value...")

            result = await conn.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_enum e
                    JOIN pg_type t ON e.enumtypid = t.oid
                    WHERE t.typname = 'currencytype' AND e.enumlabel = 'ton'
                )
            """))
            ton_exists = result.scalar()

            if not ton_exists:
                logger.warning("'ton' value missing from currencytype enum, adding it now...")
                await conn.execute(text("ALTER TYPE currencytype ADD VALUE 'ton'"))
                logger.info("✅ Added 'ton' to currencytype enum")
            else:
                logger.debug("✅ 'ton' value exists in currencytype enum")

            # Check if users table has balance_ton column
            result = await conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'users'
                AND column_name = 'balance_ton'
            """))

            if result.fetchone() is None:
                error_msg = (
                    "\n" + "="*80 + "\n"
                    "DATABASE SCHEMA OUTDATED - MIGRATION REQUIRED\n"
                    "="*80 + "\n"
                    "The database is missing the 'balance_ton' column in the 'users' table.\n"
                    "This column is added by migration 20251116_add_ton_support.\n\n"
                    "To fix this, run the following command:\n"
                    "  alembic upgrade head\n\n"
                    "Or if using Docker:\n"
                    "  docker-compose run bot alembic upgrade head\n\n"
                    "If alembic is not installed, install it first:\n"
                    "  pip install alembic\n"
                    "="*80 + "\n"
                )
                logger.error(error_msg)
                raise RuntimeError(
                    "Database schema is outdated. "
                    "Please run 'alembic upgrade head' to apply pending migrations."
                )

            logger.debug("Database schema validation passed")

    except RuntimeError:
        raise
    except Exception as e:
        logger.warning(f"Could not validate database schema: {e}")
        # Don't fail startup if validation check itself fails
        pass


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database session"""
    async with get_session() as session:
        yield session
