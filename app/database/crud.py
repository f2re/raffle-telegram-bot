from typing import Optional, List
from datetime import datetime

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .models import (
    User, Raffle, Participant, Transaction, BotSettings, WithdrawalRequest, PayoutRequest,
    TonConnectSession,
    CurrencyType, RaffleStatus, TransactionType, TransactionStatus, WithdrawalStatus, PayoutStatus
)


# ==================== USER OPERATIONS ====================

async def get_or_create_user(
    session: AsyncSession,
    telegram_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
) -> User:
    """Get existing user or create new one"""
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
        )
        session.add(user)
        await session.flush()
    else:
        # Update user info if changed
        if username and user.username != username:
            user.username = username
        if first_name and user.first_name != first_name:
            user.first_name = first_name
        if last_name and user.last_name != last_name:
            user.last_name = last_name

    return user


async def get_user_by_telegram_id(session: AsyncSession, telegram_id: int) -> Optional[User]:
    """Get user by telegram ID"""
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    return result.scalar_one_or_none()


async def update_user_balance(
    session: AsyncSession,
    user_id: int,
    amount: float,
    currency: CurrencyType,
) -> User:
    """Update user balance"""
    user = await session.get(User, user_id)
    if not user:
        raise ValueError(f"User {user_id} not found")

    if currency == CurrencyType.STARS:
        user.balance_stars += int(amount)
    else:
        user.balance_rub += amount

    await session.flush()
    return user


# ==================== RAFFLE OPERATIONS ====================

async def create_raffle(
    session: AsyncSession,
    min_participants: int,
    entry_fee_type: CurrencyType,
    entry_fee_amount: float,
    commission_percent: float,
    max_participants: Optional[int] = None,
    deadline: Optional[datetime] = None,
) -> Raffle:
    """Create new raffle"""
    raffle = Raffle(
        min_participants=min_participants,
        max_participants=max_participants,
        entry_fee_type=entry_fee_type,
        entry_fee_amount=entry_fee_amount,
        commission_percent=commission_percent,
        deadline=deadline,
        status=RaffleStatus.PENDING,
    )
    session.add(raffle)
    await session.flush()
    return raffle


async def get_active_raffle(session: AsyncSession) -> Optional[Raffle]:
    """Get current active or pending raffle"""
    result = await session.execute(
        select(Raffle)
        .where(Raffle.status.in_([RaffleStatus.PENDING, RaffleStatus.ACTIVE]))
        .order_by(Raffle.created_at.desc())
    )
    return result.scalar_one_or_none()


async def get_raffle_by_id(session: AsyncSession, raffle_id: int) -> Optional[Raffle]:
    """Get raffle by ID with participants"""
    result = await session.execute(
        select(Raffle)
        .options(selectinload(Raffle.participants))
        .where(Raffle.id == raffle_id)
    )
    return result.scalar_one_or_none()


async def update_raffle_status(
    session: AsyncSession,
    raffle_id: int,
    status: RaffleStatus,
) -> Raffle:
    """Update raffle status"""
    raffle = await session.get(Raffle, raffle_id)
    if not raffle:
        raise ValueError(f"Raffle {raffle_id} not found")

    raffle.status = status

    if status == RaffleStatus.ACTIVE and not raffle.started_at:
        raffle.started_at = datetime.utcnow()
    elif status == RaffleStatus.FINISHED and not raffle.finished_at:
        raffle.finished_at = datetime.utcnow()

    await session.flush()
    return raffle


async def set_raffle_winner(
    session: AsyncSession,
    raffle_id: int,
    winner_id: int,
    random_result: dict,
    prize_amount: float,
) -> Raffle:
    """Set raffle winner"""
    raffle = await session.get(Raffle, raffle_id)
    if not raffle:
        raise ValueError(f"Raffle {raffle_id} not found")

    raffle.winner_id = winner_id
    raffle.random_result = random_result
    raffle.prize_amount = prize_amount
    raffle.status = RaffleStatus.FINISHED
    raffle.finished_at = datetime.utcnow()

    await session.flush()
    return raffle


# ==================== PARTICIPANT OPERATIONS ====================

async def add_participant(
    session: AsyncSession,
    raffle_id: int,
    user_id: int,
    transaction_id: Optional[int] = None,
) -> Participant:
    """Add participant to raffle"""
    # Check if already participating
    result = await session.execute(
        select(Participant).where(
            Participant.raffle_id == raffle_id,
            Participant.user_id == user_id,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise ValueError("User already participating in this raffle")

    # Get next participant number
    count_result = await session.execute(
        select(func.count(Participant.id)).where(Participant.raffle_id == raffle_id)
    )
    participant_number = count_result.scalar() + 1

    participant = Participant(
        raffle_id=raffle_id,
        user_id=user_id,
        transaction_id=transaction_id,
        participant_number=participant_number,
    )
    session.add(participant)
    await session.flush()
    return participant


async def get_raffle_participants(
    session: AsyncSession,
    raffle_id: int,
) -> List[Participant]:
    """Get all participants for a raffle"""
    result = await session.execute(
        select(Participant)
        .options(selectinload(Participant.user))
        .where(Participant.raffle_id == raffle_id)
        .order_by(Participant.participant_number)
    )
    return list(result.scalars().all())


async def get_user_participations(
    session: AsyncSession,
    user_id: int,
    limit: int = 10,
) -> List[Participant]:
    """Get user's raffle participation history"""
    result = await session.execute(
        select(Participant)
        .options(selectinload(Participant.raffle))
        .where(Participant.user_id == user_id)
        .order_by(Participant.joined_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


# ==================== TRANSACTION OPERATIONS ====================

async def create_transaction(
    session: AsyncSession,
    user_id: int,
    type: TransactionType,
    amount: float,
    currency: CurrencyType,
    payment_id: Optional[str] = None,
    description: Optional[str] = None,
    payment_metadata: Optional[dict] = None,
) -> Transaction:
    """Create new transaction"""
    transaction = Transaction(
        user_id=user_id,
        type=type,
        amount=amount,
        currency=currency,
        payment_id=payment_id,
        description=description,
        payment_metadata=payment_metadata,
        status=TransactionStatus.PENDING,
    )
    session.add(transaction)
    await session.flush()
    return transaction


async def update_transaction_status(
    session: AsyncSession,
    transaction_id: int,
    status: TransactionStatus,
) -> Transaction:
    """Update transaction status"""
    transaction = await session.get(Transaction, transaction_id)
    if not transaction:
        raise ValueError(f"Transaction {transaction_id} not found")

    transaction.status = status
    await session.flush()
    return transaction


async def get_user_transactions(
    session: AsyncSession,
    user_id: int,
    limit: int = 20,
) -> List[Transaction]:
    """Get user transaction history"""
    result = await session.execute(
        select(Transaction)
        .where(Transaction.user_id == user_id)
        .order_by(Transaction.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


# ==================== BOT SETTINGS OPERATIONS ====================

async def get_setting(session: AsyncSession, key: str) -> Optional[str]:
    """Get bot setting value"""
    result = await session.execute(
        select(BotSettings).where(BotSettings.key == key)
    )
    setting = result.scalar_one_or_none()
    return setting.value if setting else None


async def set_setting(
    session: AsyncSession,
    key: str,
    value: str,
    description: Optional[str] = None,
) -> BotSettings:
    """Set bot setting value"""
    result = await session.execute(
        select(BotSettings).where(BotSettings.key == key)
    )
    setting = result.scalar_one_or_none()

    if setting:
        setting.value = value
        if description:
            setting.description = description
    else:
        setting = BotSettings(key=key, value=value, description=description)
        session.add(setting)

    await session.flush()
    return setting


# ==================== WITHDRAWAL OPERATIONS ====================

async def create_withdrawal_request(
    session: AsyncSession,
    user_id: int,
    amount: float,
    currency: CurrencyType,
    card_number: Optional[str] = None,
    phone_number: Optional[str] = None,
) -> WithdrawalRequest:
    """Create new withdrawal request"""
    withdrawal = WithdrawalRequest(
        user_id=user_id,
        amount=amount,
        currency=currency,
        card_number=card_number,
        phone_number=phone_number,
        status=WithdrawalStatus.PENDING,
    )
    session.add(withdrawal)
    await session.flush()
    return withdrawal


async def get_withdrawal_request(
    session: AsyncSession,
    withdrawal_id: int,
) -> Optional[WithdrawalRequest]:
    """Get withdrawal request by ID"""
    result = await session.execute(
        select(WithdrawalRequest)
        .options(selectinload(WithdrawalRequest.user))
        .where(WithdrawalRequest.id == withdrawal_id)
    )
    return result.scalar_one_or_none()


async def get_pending_withdrawals(
    session: AsyncSession,
    limit: int = 50,
) -> List[WithdrawalRequest]:
    """Get all pending withdrawal requests"""
    result = await session.execute(
        select(WithdrawalRequest)
        .options(selectinload(WithdrawalRequest.user))
        .where(WithdrawalRequest.status == WithdrawalStatus.PENDING)
        .order_by(WithdrawalRequest.created_at)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_user_withdrawals(
    session: AsyncSession,
    user_id: int,
    limit: int = 10,
) -> List[WithdrawalRequest]:
    """Get user's withdrawal history"""
    result = await session.execute(
        select(WithdrawalRequest)
        .where(WithdrawalRequest.user_id == user_id)
        .order_by(WithdrawalRequest.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def update_withdrawal_status(
    session: AsyncSession,
    withdrawal_id: int,
    status: WithdrawalStatus,
    admin_id: Optional[int] = None,
    rejection_reason: Optional[str] = None,
    payment_id: Optional[str] = None,
) -> WithdrawalRequest:
    """Update withdrawal request status"""
    withdrawal = await session.get(WithdrawalRequest, withdrawal_id)
    if not withdrawal:
        raise ValueError(f"Withdrawal request {withdrawal_id} not found")

    withdrawal.status = status

    if admin_id:
        withdrawal.admin_id = admin_id

    if rejection_reason:
        withdrawal.rejection_reason = rejection_reason

    if payment_id:
        withdrawal.payment_id = payment_id

    if status == WithdrawalStatus.APPROVED:
        withdrawal.processed_at = datetime.utcnow()
    elif status in [WithdrawalStatus.COMPLETED, WithdrawalStatus.FAILED]:
        withdrawal.completed_at = datetime.utcnow()

    await session.flush()
    return withdrawal


# ==================== PAYOUT REQUEST OPERATIONS ====================

async def create_payout_request(
    session: AsyncSession,
    raffle_id: int,
    winner_id: int,
    amount: float,
    currency: CurrencyType,
    invoice_link: str,
) -> PayoutRequest:
    """Create new payout request for raffle winner"""
    payout = PayoutRequest(
        raffle_id=raffle_id,
        winner_id=winner_id,
        amount=amount,
        currency=currency,
        invoice_link=invoice_link,
        status=PayoutStatus.PENDING,
    )
    session.add(payout)
    await session.flush()
    return payout


async def get_payout_request(
    session: AsyncSession,
    payout_id: int,
) -> Optional[PayoutRequest]:
    """Get payout request by ID"""
    result = await session.execute(
        select(PayoutRequest)
        .options(
            selectinload(PayoutRequest.winner),
            selectinload(PayoutRequest.raffle)
        )
        .where(PayoutRequest.id == payout_id)
    )
    return result.scalar_one_or_none()


async def get_payout_request_by_raffle(
    session: AsyncSession,
    raffle_id: int,
) -> Optional[PayoutRequest]:
    """Get payout request by raffle ID"""
    result = await session.execute(
        select(PayoutRequest)
        .options(
            selectinload(PayoutRequest.winner),
            selectinload(PayoutRequest.raffle)
        )
        .where(PayoutRequest.raffle_id == raffle_id)
    )
    return result.scalar_one_or_none()


async def get_pending_payouts(
    session: AsyncSession,
    limit: int = 50,
) -> List[PayoutRequest]:
    """Get all pending payout requests"""
    result = await session.execute(
        select(PayoutRequest)
        .options(
            selectinload(PayoutRequest.winner),
            selectinload(PayoutRequest.raffle)
        )
        .where(PayoutRequest.status == PayoutStatus.PENDING)
        .order_by(PayoutRequest.created_at)
        .limit(limit)
    )
    return list(result.scalars().all())


async def update_payout_status(
    session: AsyncSession,
    payout_id: int,
    status: PayoutStatus,
    admin_id: Optional[int] = None,
    rejection_reason: Optional[str] = None,
) -> PayoutRequest:
    """Update payout request status"""
    payout = await session.get(PayoutRequest, payout_id)
    if not payout:
        raise ValueError(f"Payout request {payout_id} not found")

    payout.status = status

    if status == PayoutStatus.COMPLETED:
        payout.completed_at = datetime.utcnow()
        if admin_id:
            payout.completed_by = admin_id
    elif status == PayoutStatus.REJECTED:
        payout.rejected_at = datetime.utcnow()
        if admin_id:
            payout.rejected_by = admin_id
        if rejection_reason:
            payout.rejection_reason = rejection_reason

    await session.flush()
    return payout


# ==================== TON CONNECT OPERATIONS ====================

async def create_ton_connect_session(
    session: AsyncSession,
    user_id: int,
    wallet_address: str,
    session_data: Optional[dict] = None,
    wallet_state_init: Optional[str] = None,
    wallet_public_key: Optional[str] = None,
) -> TonConnectSession:
    """Create new TON Connect session"""
    # Deactivate all previous sessions for this user
    await session.execute(
        update(TonConnectSession)
        .where(TonConnectSession.user_id == user_id)
        .where(TonConnectSession.is_active == True)
        .values(is_active=False, disconnected_at=datetime.utcnow())
    )

    ton_session = TonConnectSession(
        user_id=user_id,
        wallet_address=wallet_address,
        session_data=session_data,
        wallet_state_init=wallet_state_init,
        wallet_public_key=wallet_public_key,
        is_active=True,
    )
    session.add(ton_session)
    await session.flush()
    return ton_session


async def get_active_ton_connect_session(
    session: AsyncSession,
    user_id: int,
) -> Optional[TonConnectSession]:
    """Get active TON Connect session for user"""
    result = await session.execute(
        select(TonConnectSession)
        .where(TonConnectSession.user_id == user_id)
        .where(TonConnectSession.is_active == True)
    )
    return result.scalar_one_or_none()


async def update_ton_connect_session(
    session: AsyncSession,
    session_id: int,
    session_data: Optional[dict] = None,
) -> TonConnectSession:
    """Update TON Connect session data"""
    ton_session = await session.get(TonConnectSession, session_id)
    if not ton_session:
        raise ValueError(f"TON Connect session {session_id} not found")

    if session_data is not None:
        ton_session.session_data = session_data

    ton_session.last_used = datetime.utcnow()
    await session.flush()
    return ton_session


async def disconnect_ton_connect_session(
    session: AsyncSession,
    user_id: int,
) -> bool:
    """Disconnect (deactivate) TON Connect session for user"""
    result = await session.execute(
        update(TonConnectSession)
        .where(TonConnectSession.user_id == user_id)
        .where(TonConnectSession.is_active == True)
        .values(is_active=False, disconnected_at=datetime.utcnow())
    )
    await session.flush()
    return result.rowcount > 0


async def get_ton_connect_session_by_wallet(
    session: AsyncSession,
    wallet_address: str,
) -> Optional[TonConnectSession]:
    """Get TON Connect session by wallet address"""
    result = await session.execute(
        select(TonConnectSession)
        .where(TonConnectSession.wallet_address == wallet_address)
        .where(TonConnectSession.is_active == True)
    )
    return result.scalar_one_or_none()
