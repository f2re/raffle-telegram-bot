#!/usr/bin/env python3
"""
Standalone script to apply TON support migration
Adds balance_ton and ton_wallet_address columns to users table
"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def apply_migration():
    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/raffle_bot')

    # Convert asyncpg URL format if needed
    if database_url.startswith('postgresql+asyncpg://'):
        database_url = database_url.replace('postgresql+asyncpg://', 'postgresql://')

    print(f"Connecting to database...")

    # Connect to database
    conn = await asyncpg.connect(database_url)

    try:
        print("Applying TON support migration...")

        # Add 'ton' to CurrencyType enum
        print("  - Adding 'ton' to CurrencyType enum...")
        await conn.execute("ALTER TYPE currencytype ADD VALUE IF NOT EXISTS 'ton'")

        # Check if columns already exist
        columns_exist = await conn.fetch("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'users'
            AND column_name IN ('balance_ton', 'ton_wallet_address')
        """)

        existing_columns = {row['column_name'] for row in columns_exist}

        # Add balance_ton column if it doesn't exist
        if 'balance_ton' not in existing_columns:
            print("  - Adding balance_ton column to users table...")
            await conn.execute("""
                ALTER TABLE users
                ADD COLUMN balance_ton DOUBLE PRECISION DEFAULT 0.0
            """)
        else:
            print("  - balance_ton column already exists, skipping...")

        # Add ton_wallet_address column if it doesn't exist
        if 'ton_wallet_address' not in existing_columns:
            print("  - Adding ton_wallet_address column to users table...")
            await conn.execute("""
                ALTER TABLE users
                ADD COLUMN ton_wallet_address VARCHAR(48)
            """)
        else:
            print("  - ton_wallet_address column already exists, skipping...")

        # Check if transaction_hash column exists in transactions table
        tx_columns = await conn.fetch("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'transactions'
            AND column_name = 'transaction_hash'
        """)

        if not tx_columns:
            print("  - Adding transaction_hash column to transactions table...")
            await conn.execute("""
                ALTER TABLE transactions
                ADD COLUMN transaction_hash VARCHAR(44)
            """)

            # Create index for transaction_hash
            print("  - Creating index for transaction_hash...")
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS ix_transactions_transaction_hash
                ON transactions(transaction_hash)
            """)
        else:
            print("  - transaction_hash column already exists, skipping...")

        # Check if wallet_address column exists in withdrawal_requests table
        wr_columns = await conn.fetch("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'withdrawal_requests'
            AND column_name = 'wallet_address'
        """)

        if not wr_columns:
            print("  - Adding wallet_address column to withdrawal_requests table...")
            await conn.execute("""
                ALTER TABLE withdrawal_requests
                ADD COLUMN wallet_address VARCHAR(48)
            """)
        else:
            print("  - wallet_address column already exists, skipping...")

        print("\n✓ Migration applied successfully!")

    except Exception as e:
        print(f"\n✗ Error applying migration: {e}")
        raise
    finally:
        await conn.close()
        print("Database connection closed.")

if __name__ == "__main__":
    asyncio.run(apply_migration())
