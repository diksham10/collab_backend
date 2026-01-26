from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from uuid import UUID, uuid4
from typing import Optional


class RefreshTokenModel(SQLModel, table=True):
    __tablename__ = "refresh_tokens"

    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True, index=True)
    user_id: UUID 
    hashed_token: str = Field(unique=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime