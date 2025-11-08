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


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    balance_stars = Column(Integer, default=0)
    balance_rub = Column(Float, default=0.0)
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
    entry_fee_type = Column(Enum(CurrencyType), nullable=False)
    entry_fee_amount = Column(Float, nullable=False)
    status = Column(Enum(RaffleStatus), default=RaffleStatus.PENDING)
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
    type = Column(Enum(TransactionType), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(Enum(CurrencyType), nullable=False)
    status = Column(Enum(TransactionStatus), default=TransactionStatus.PENDING)
    payment_id = Column(String, nullable=True)  # External payment system ID
    description = Column(Text, nullable=True)
    metadata = Column(JSON, nullable=True)  # Additional payment data
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
