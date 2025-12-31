import sys
from pathlib import Path

# Add bot directory to path to import database models
# In container: /app/backend/app/api/raffle.py -> ../../../app = /app/app
bot_path = Path(__file__).parent.parent.parent / "app"
sys.path.insert(0, str(bot_path))

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload
from typing import List

from backend.app.api.schemas import (
    RaffleResponse,
    ParticipantResponse,
    JoinRaffleRequest,
    JoinRaffleResponse
)
from backend.app.api.dependencies import get_current_user
from backend.app.database import get_db, AsyncSession
from database.models import Raffle, Participant, User, RaffleStatus, Transaction, TransactionType, TransactionStatus, CurrencyType

router = APIRouter(prefix="/raffle", tags=["raffle"])


@router.get("/current", response_model=RaffleResponse)
async def get_current_raffle(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current active raffle
    """
    # Find active or pending raffle
    stmt = select(Raffle).where(
        Raffle.status.in_([RaffleStatus.ACTIVE, RaffleStatus.PENDING])
    ).order_by(Raffle.created_at.desc())

    result = await db.execute(stmt)
    raffle = result.scalar_one_or_none()

    if not raffle:
        raise HTTPException(status_code=404, detail="No active raffle")

    # Count participants
    participants_stmt = select(func.count(Participant.id)).where(
        Participant.raffle_id == raffle.id
    )
    participants_result = await db.execute(participants_stmt)
    participants_count = participants_result.scalar() or 0

    # Check if user participated
    user_participated = False
    if user.get('user_id'):
        user_stmt = select(User).where(User.telegram_id == user['user_id'])
        user_result = await db.execute(user_stmt)
        db_user = user_result.scalar_one_or_none()

        if db_user:
            participation_stmt = select(Participant).where(
                Participant.raffle_id == raffle.id,
                Participant.user_id == db_user.id
            )
            participation_result = await db.execute(participation_stmt)
            user_participated = participation_result.scalar_one_or_none() is not None

    # Map status
    status_map = {
        RaffleStatus.PENDING: 'collecting',
        RaffleStatus.ACTIVE: 'collecting',
        RaffleStatus.FINISHED: 'completed',
        RaffleStatus.CANCELLED: 'cancelled'
    }

    # Check if ready to start
    if participants_count >= raffle.min_participants and raffle.status == RaffleStatus.PENDING:
        status = 'ready'
    else:
        status = status_map.get(raffle.status, 'collecting')

    return RaffleResponse(
        id=raffle.id,
        entry_fee=raffle.entry_fee_amount,
        participants_count=participants_count,
        min_participants=raffle.min_participants,
        max_participants=raffle.max_participants,
        status=status,
        user_participated=user_participated,
        created_at=raffle.created_at,
        started_at=raffle.started_at
    )


@router.get("/{raffle_id}/participants", response_model=List[ParticipantResponse])
async def get_raffle_participants(
    raffle_id: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of raffle participants
    """
    # Verify raffle exists
    raffle_stmt = select(Raffle).where(Raffle.id == raffle_id)
    raffle_result = await db.execute(raffle_stmt)
    raffle = raffle_result.scalar_one_or_none()

    if not raffle:
        raise HTTPException(status_code=404, detail="Raffle not found")

    # Get participants with user data
    stmt = select(Participant).options(
        joinedload(Participant.user)
    ).where(
        Participant.raffle_id == raffle_id
    ).order_by(Participant.joined_at.asc())

    result = await db.execute(stmt)
    participants = result.scalars().all()

    return [
        ParticipantResponse(
            id=p.user.telegram_id,
            username=p.user.username,
            first_name=p.user.first_name or "User",
            joined_at=p.joined_at
        )
        for p in participants
    ]


@router.post("/join", response_model=JoinRaffleResponse)
async def join_raffle(
    request: JoinRaffleRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Join a raffle with TON payment
    """
    user_id = user.get('user_id')
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Get or create user
    user_stmt = select(User).where(User.telegram_id == user_id)
    user_result = await db.execute(user_stmt)
    db_user = user_result.scalar_one_or_none()

    if not db_user:
        db_user = User(
            telegram_id=user_id,
            username=user.get('username'),
            first_name=user.get('first_name'),
            last_name=user.get('last_name')
        )
        db.add(db_user)
        await db.flush()

    # Get raffle
    raffle_stmt = select(Raffle).where(Raffle.id == request.raffle_id)
    raffle_result = await db.execute(raffle_stmt)
    raffle = raffle_result.scalar_one_or_none()

    if not raffle:
        raise HTTPException(status_code=404, detail="Raffle not found")

    if raffle.status not in [RaffleStatus.PENDING, RaffleStatus.ACTIVE]:
        raise HTTPException(status_code=400, detail="Raffle is not accepting participants")

    # Check if user already participated
    existing_stmt = select(Participant).where(
        Participant.raffle_id == raffle.id,
        Participant.user_id == db_user.id
    )
    existing_result = await db.execute(existing_stmt)
    if existing_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Already participated in this raffle")

    # Check transaction hash uniqueness
    tx_stmt = select(Transaction).where(Transaction.transaction_hash == request.transaction_hash)
    tx_result = await db.execute(tx_stmt)
    if tx_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Transaction already used")

    # Get next participant number
    count_stmt = select(func.count(Participant.id)).where(Participant.raffle_id == raffle.id)
    count_result = await db.execute(count_stmt)
    participant_number = (count_result.scalar() or 0) + 1

    # Create transaction record
    transaction = Transaction(
        user_id=db_user.id,
        type=TransactionType.RAFFLE_ENTRY,
        amount=raffle.entry_fee_amount,
        currency=raffle.entry_fee_type,
        status=TransactionStatus.COMPLETED,
        transaction_hash=request.transaction_hash,
        description=f"Entry to raffle #{raffle.id}",
        payment_metadata={
            'wallet_address': request.wallet_address,
            'raffle_id': raffle.id
        }
    )
    db.add(transaction)
    await db.flush()

    # Create participant record
    participant = Participant(
        raffle_id=raffle.id,
        user_id=db_user.id,
        transaction_id=transaction.id,
        participant_number=participant_number
    )
    db.add(participant)

    # Update user's TON wallet if not set
    if not db_user.ton_wallet_address:
        db_user.ton_wallet_address = request.wallet_address

    await db.commit()

    return JoinRaffleResponse(
        status="success",
        participant_id=participant.id,
        message=f"Successfully joined raffle #{raffle.id}"
    )
