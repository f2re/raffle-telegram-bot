"""add TON cryptocurrency support

Revision ID: 20251116_001
Revises: 20251108_002
Create Date: 2025-11-16

This migration adds support for TON (The Open Network) cryptocurrency:
- Adds 'ton' to CurrencyType enum
- Adds balance_ton field to users table
- Adds ton_wallet_address field to users table for receiving payouts
- Adds transaction_hash field to transactions table for blockchain verification
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20251116_001'
down_revision: Union[str, None] = '20251108_002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add 'ton' to CurrencyType enum
    op.execute("ALTER TYPE currencytype ADD VALUE IF NOT EXISTS 'ton'")

    # Add balance_ton column to users table
    op.add_column('users',
        sa.Column('balance_ton', sa.Float(), nullable=True, server_default='0.0')
    )

    # Add ton_wallet_address column to users table for payouts
    # This stores user's TON wallet address for receiving prizes
    op.add_column('users',
        sa.Column('ton_wallet_address', sa.String(48), nullable=True)
    )

    # Add transaction_hash column to transactions table for blockchain verification
    # This stores the TON blockchain transaction hash for transparency
    op.add_column('transactions',
        sa.Column('transaction_hash', sa.String(44), nullable=True)
    )

    # Add wallet_address column to withdrawal_requests for TON withdrawals
    op.add_column('withdrawal_requests',
        sa.Column('wallet_address', sa.String(48), nullable=True)
    )

    # Create index for transaction_hash for faster lookups
    op.create_index(
        'ix_transactions_transaction_hash',
        'transactions',
        ['transaction_hash'],
        unique=False
    )


def downgrade() -> None:
    # Drop index
    op.drop_index('ix_transactions_transaction_hash', table_name='transactions')

    # Drop columns
    op.drop_column('withdrawal_requests', 'wallet_address')
    op.drop_column('transactions', 'transaction_hash')
    op.drop_column('users', 'ton_wallet_address')
    op.drop_column('users', 'balance_ton')

    # Note: Cannot remove 'ton' from enum in PostgreSQL without recreating the enum
    # This would require recreating all tables that use the enum
    # For production, consider creating a new migration that handles this properly
