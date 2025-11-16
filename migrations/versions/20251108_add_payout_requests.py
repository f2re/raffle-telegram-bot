"""add payout_requests table

Revision ID: 20251108_002
Revises: 20251108_001
Create Date: 2025-11-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20251108_002'
down_revision: Union[str, None] = '20251108_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create payout status enum type
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE payoutstatus AS ENUM ('pending', 'completed', 'rejected');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Create payout_requests table
    op.create_table(
        'payout_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('raffle_id', sa.Integer(), nullable=False),
        sa.Column('winner_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('currency', postgresql.ENUM('stars', 'rub', name='currencytype', create_type=False), nullable=False),
        sa.Column('invoice_link', sa.String(500), nullable=False),
        sa.Column('status', postgresql.ENUM('pending', 'completed', 'rejected', name='payoutstatus', create_type=False), nullable=True),
        sa.Column('completed_by', sa.Integer(), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('rejected_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('rejected_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['raffle_id'], ['raffles.id'], ),
        sa.ForeignKeyConstraint(['winner_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['completed_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['rejected_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_payout_requests_id'), 'payout_requests', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_payout_requests_id'), table_name='payout_requests')
    op.drop_table('payout_requests')
    op.execute('DROP TYPE IF EXISTS payoutstatus')
