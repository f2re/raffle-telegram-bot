from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class RaffleResponse(BaseModel):
    id: int
    entry_fee: float
    participants_count: int
    min_participants: int
    max_participants: Optional[int] = None
    status: str
    user_participated: bool
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ParticipantResponse(BaseModel):
    id: int
    username: Optional[str] = None
    first_name: str
    joined_at: datetime

    class Config:
        from_attributes = True


class JoinRaffleRequest(BaseModel):
    raffle_id: int = Field(..., gt=0)
    transaction_hash: str = Field(..., min_length=44, max_length=44)
    wallet_address: str = Field(..., min_length=48, max_length=48)


class JoinRaffleResponse(BaseModel):
    status: str
    participant_id: int
    message: str


class ErrorResponse(BaseModel):
    detail: str
