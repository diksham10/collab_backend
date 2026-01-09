from fastapi import APIRouter, Depends
from src.wow import send_email
from sqlalchemy.ext.asyncio import AsyncSession
from src.otp.service import create_send_otp
from src.database import get_session
from uuid import uuid4
from datetime import datetime, timezone
from src.auth.models import Users, UserRole



router = APIRouter()

@router.get("/test")
async def test_endpoint():
    await send_email(to_mail="khiunjuk13@gmail.com", subject="fuck you", body="sulu le vaneko fuck you re.")
    return {"message": "Test email sent"}


   

    await create_send_otp(db, dummy_user, subject="Your OTP Code")
    return {"message": "OTP sent to email"}

