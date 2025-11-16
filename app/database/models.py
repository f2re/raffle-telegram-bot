from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import (
    Column, Integer, String, BigInteger, Float, DateTime,
    ForeignKey, Enum, Boolean, Text, JSON
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class CurrencyType(PyEnum):
    STARS = "stars"
    RUB = "rub"
    TON = "ton"


class RaffleStatus(PyEnum):
    PENDING = "pending"
    ACTIVE = "active"
    FINISHED = "finished"
    CANCELLED = "cancelled"


class TransactionType(PyEnum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    RAFFLE_ENTRY = "raffle_entry"
    RAFFLE_WIN = "raffle_win"
    REFUND = "refund"


class TransactionStatus(PyEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WithdrawalStatus(PyEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class PayoutStatus(PyEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    REJECTED = "rejected"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    balance_stars = Column(Integer, default=0)
    balance_rub = Column(Float, default=0.0)
    balance_ton = Column(Float, default=0.0)
    ton_wallet_address = Column(String(48), nullable=True)  # User's TON wallet for payouts
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    # Relationships
    transactions = relationship("Transaction", back_populates="user")
    participations = relationship("Participant", back_populates="user")
    won_raffles = relationship("Raffle", back_populates="winner")


class Raffle(Base):
    __tablename__ = "raffles"

    id = Column(Integer, primary_key=True, index=True)
    min_participants = Column(Integer, nullable=False)
    max_participants = Column(Integer, nullable=True)
    entry_fee_type = Column(Enum(CurrencyType, values_callable=lambda x: [e.value for e in x], name='currencytype'), nullable=False)
    entry_fee_amount = Column(Float, nullable=False)
    status = Column(Enum(RaffleStatus, values_callable=lambda x: [e.value for e in x], name='rafflestatus'), default=RaffleStatus.PENDING)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    deadline = Column(DateTime, nullable=True)
    winner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    random_result = Column(JSON, nullable=True)  # Random.org signature data
    prize_amount = Column(Float, nullable=True)
    commission_percent = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    winner = relationship("User", back_populates="won_raffles")
    participants = relationship("Participant", back_populates="raffle")


class Participant(Base):
    __tablename__ = "participants"

    id = Column(Integer, primary_key=True, index=True)
    raffle_id = Column(Integer, ForeignKey("raffles.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    joined_at = Column(DateTime, default=datetime.utcnow)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=True)
    participant_number = Column(Integer, nullable=False)  # Order number for random selection

    # Relationships
    raffle = relationship("Raffle", back_populates="participants")
    user = relationship("User", back_populates="participations")
    transaction = relationship("Transaction")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(Enum(TransactionType, values_callable=lambda x: [e.value for e in x], name='transactiontype'), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(Enum(CurrencyType, values_callable=lambda x: [e.value for e in x], name='currencytype'), nullable=False)
    status = Column(Enum(TransactionStatus, values_callable=lambda x: [e.value for e in x], name='transactionstatus'), default=TransactionStatus.PENDING)
    payment_id = Column(String, nullable=True)  # External payment system ID
    transaction_hash = Column(String(44), nullable=True, index=True)  # TON blockchain transaction hash
    description = Column(Text, nullable=True)
    payment_metadata = Column(JSON, nullable=True)  # Additional payment data
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="transactions")


class BotSettings(Base):
    __tablename__ = "bot_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, nullable=False)
    value = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class WithdrawalRequest(Base):
    __tablename__ = "withdrawal_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(Enum(CurrencyType, values_callable=lambda x: [e.value for e in x], name='currencytype'), nullable=False)
    status = Column(Enum(WithdrawalStatus, values_callable=lambda x: [e.value for e in x], name='withdrawalstatus'), default=WithdrawalStatus.PENDING)

    # Payment details (for RUB withdrawals)
    card_number = Column(String, nullable=True)  # Bank card number
    phone_number = Column(String, nullable=True)  # Phone for SBP
    wallet_address = Column(String(48), nullable=True)  # TON wallet address for TON withdrawals

    # Admin actions
    admin_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    rejection_reason = Column(Text, nullable=True)

    # Payment tracking
    payment_id = Column(String, nullable=True)  # YooKassa payout ID or Telegram payment ID
    payment_metadata = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="withdrawal_requests")
    admin = relationship("User", foreign_keys=[admin_id])


class PayoutRequest(Base):
    """
    Payout requests for raffle winners
    Admin must manually pay winners via invoice link
    """
    __tablename__ = "payout_requests"

    id = Column(Integer, primary_key=True, index=True)
    raffle_id = Column(Integer, ForeignKey("raffles.id"), nullable=False)
    winner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Float, nullable=False)  # Prize amount
    currency = Column(Enum(CurrencyType, values_callable=lambda x: [e.value for e in x], name='currencytype'), nullable=False)
    invoice_link = Column(String(500), nullable=False)  # Invoice link for admin to pay
    status = Column(Enum(PayoutStatus, values_callable=lambda x: [e.value for e in x], name='payoutstatus'), default=PayoutStatus.PENDING)

    # Admin actions
    completed_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # Admin who confirmed
    rejection_reason = Column(Text, nullable=True)
    rejected_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # Admin who rejected

    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    rejected_at = Column(DateTime, nullable=True)

    # Relationships
    raffle = relationship("Raffle")
    winner = relationship("User", foreign_keys=[winner_id])
    completed_by_admin = relationship("User", foreign_keys=[completed_by])
    rejected_by_admin = relationship("User", foreign_keys=[rejected_by])


class TonConnectSession(Base):
    """
    TON Connect wallet sessions
    Stores connected wallet data for each user
    """
    __tablename__ = "ton_connect_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    wallet_address = Column(String(48), nullable=False, index=True)  # Connected TON wallet address
    wallet_state_init = Column(Text, nullable=True)  # Wallet state init for contract
    wallet_public_key = Column(String(64), nullable=True)  # Wallet public key
    session_data = Column(JSON, nullable=True)  # TON Connect session data (for restore)
    is_active = Column(Boolean, default=True, index=True)  # Is session active
    connected_at = Column(DateTime, default=datetime.utcnow)
    last_used = Column(DateTime, default=datetime.utcnow)
    disconnected_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", backref="ton_connect_sessions")

    def __repr__(self):
        return f"<TonConnectSession(user_id={self.user_id}, wallet={self.wallet_address[:8]}...)>"
