from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from src.myenums import UserRole
from datetime import datetime

class AdminCreate(BaseModel):
    email: str
    password: str
    role: UserRole

class AdminRead(BaseModel):
    id: UUID
    email: str
    role: UserRole
    created_at: datetime

    class Config:
        orm_mode = True
