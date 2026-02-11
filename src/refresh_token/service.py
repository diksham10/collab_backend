from src.refresh_token.model import RefreshTokenModel
from sqlalchemy import select
from fastapi import Depends, HTTPException, Response, Request
from sqlmodel.ext.asyncio.session import AsyncSession 
from uuid import UUID
from datetime import datetime,timedelta
import hashlib
from jose import jwt, JWTError, ExpiredSignatureError
from os import getenv
from dotenv import load_dotenv

load_dotenv()
SECRET_KEY = getenv("SECRET_KEY")
ALGORITHM = getenv("ALGORITHM")
 
#hash the token:
async def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

#silent refresh token rotation endpoint
async def save_refresh_token(user_id:UUID, hashed_token:str, db: AsyncSession):
    expires = datetime.utcnow() + timedelta(days=7)
    refresh_token_model = RefreshTokenModel(
        user_id=user_id,
        hashed_token=hashed_token,
        expires_at=expires
    )
    
    db.add(refresh_token_model)
    await db.commit()
    await db.refresh(refresh_token_model)

async def delete_refresh_token(user_id: UUID, db: AsyncSession):
    result = await db.execute(
        select(RefreshTokenModel).where(RefreshTokenModel.user_id == user_id)
    )
    token_entries = result.scalars().all()
    print(f"Token entry to delete: {token_entries}")
    for token_entry in token_entries:
        await db.delete(token_entry)
    await db.commit()
    print("Refresh tokens deleted.")
