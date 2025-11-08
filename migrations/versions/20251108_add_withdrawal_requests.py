"""add withdrawal requests table

Revision ID: 20251108_001
Revises:
Create Date: 2025-11-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20251108_001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types if they don't exist
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE currencytype AS ENUM ('stars', 'rub');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE rafflestatus AS ENUM ('pending', 'active', 'finished', 'cancelled');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE transactiontype AS ENUM ('deposit', 'withdrawal', 'raffle_entry', 'raffle_win', 'refund');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE transactionstatus AS ENUM ('pending', 'completed', 'failed', 'cancelled');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE withdrawalstatus AS ENUM ('pending', 'approved', 'rejected', 'processing', 'completed', 'failed');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('telegram_id', sa.BigInteger(), nullable=False),
        sa.Column('username', sa.String(), nullable=True),
        sa.Column('first_name', sa.String(), nullable=True),
        sa.Column('last_name', sa.String(), nullable=True),
        sa.Column('balance_stars', sa.Integer(), nullable=True, default=0),
        sa.Column('balance_rub', sa.Float(), nullable=True, default=0.0),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.PrimaryKeyConstraint('id'),
        if_not_exists=True
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False, if_not_exists=True)
    op.create_index(op.f('ix_users_telegram_id'), 'users', ['telegram_id'], unique=True, if_not_exists=True)

    # Create raffles table
    op.create_table(
        'raffles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('min_participants', sa.Integer(), nullable=False),
        sa.Column('max_participants', sa.Integer(), nullable=True),
        sa.Column('entry_fee_type', sa.Enum('stars', 'rub', name='currencytype'), nullable=False),
        sa.Column('entry_fee_amount', sa.Float(), nullable=False),
        sa.Column('status', sa.Enum('pending', 'active', 'finished', 'cancelled', name='rafflestatus'), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.Column('deadline', sa.DateTime(), nullable=True),
        sa.Column('winner_id', sa.Integer(), nullable=True),
        sa.Column('random_result', sa.JSON(), nullable=True),
        sa.Column('prize_amount', sa.Float(), nullable=True),
        sa.Column('commission_percent', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['winner_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        if_not_exists=True
    )
    op.create_index(op.f('ix_raffles_id'), 'raffles', ['id'], unique=False, if_not_exists=True)

    # Create transactions table
    op.create_table(
        'transactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('type', sa.Enum('deposit', 'withdrawal', 'raffle_entry', 'raffle_win', 'refund', name='transactiontype'), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('currency', sa.Enum('stars', 'rub', name='currencytype'), nullable=False),
        sa.Column('status', sa.Enum('pending', 'completed', 'failed', 'cancelled', name='transactionstatus'), nullable=True),
        sa.Column('payment_id', sa.String(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('payment_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        if_not_exists=True
    )
    op.create_index(op.f('ix_transactions_id'), 'transactions', ['id'], unique=False, if_not_exists=True)

    # Create participants table
    op.create_table(
        'participants',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('raffle_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('joined_at', sa.DateTime(), nullable=True),
        sa.Column('transaction_id', sa.Integer(), nullable=True),
        sa.Column('participant_number', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['raffle_id'], ['raffles.id'], ),
        sa.ForeignKeyConstraint(['transaction_id'], ['transactions.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        if_not_exists=True
    )
    op.create_index(op.f('ix_participants_id'), 'participants', ['id'], unique=False, if_not_exists=True)

    # Create bot_settings table
    op.create_table(
        'bot_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        if_not_exists=True
    )
    op.create_index(op.f('ix_bot_settings_id'), 'bot_settings', ['id'], unique=False, if_not_exists=True)
    op.create_index(op.f('ix_bot_settings_key'), 'bot_settings', ['key'], unique=True, if_not_exists=True)

    # Create withdrawal_requests table
    op.create_table(
        'withdrawal_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('currency', sa.Enum('stars', 'rub', name='currencytype'), nullable=False),
        sa.Column('status', sa.Enum('pending', 'approved', 'rejected', 'processing', 'completed', 'failed', name='withdrawalstatus'), nullable=True),
        sa.Column('card_number', sa.String(), nullable=True),
        sa.Column('phone_number', sa.String(), nullable=True),
        sa.Column('admin_id', sa.Integer(), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('payment_id', sa.String(), nullable=True),
        sa.Column('payment_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['admin_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_withdrawal_requests_id'), 'withdrawal_requests', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_withdrawal_requests_id'), table_name='withdrawal_requests')
    op.drop_table('withdrawal_requests')
    op.drop_index(op.f('ix_bot_settings_key'), table_name='bot_settings')
    op.drop_index(op.f('ix_bot_settings_id'), table_name='bot_settings')
    op.drop_table('bot_settings')
    op.drop_index(op.f('ix_participants_id'), table_name='participants')
    op.drop_table('participants')
    op.drop_index(op.f('ix_transactions_id'), table_name='transactions')
    op.drop_table('transactions')
    op.drop_index(op.f('ix_raffles_id'), table_name='raffles')
    op.drop_table('raffles')
    op.drop_index(op.f('ix_users_telegram_id'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_table('users')

    # Drop enum types
    op.execute('DROP TYPE IF EXISTS withdrawalstatus')
    op.execute('DROP TYPE IF EXISTS transactionstatus')
    op.execute('DROP TYPE IF EXISTS transactiontype')
    op.execute('DROP TYPE IF EXISTS rafflestatus')
    op.execute('DROP TYPE IF EXISTS currencytype')
