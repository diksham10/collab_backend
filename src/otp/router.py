from fastapi import APIRouter, Depends
from src.otp.service import create_send_otp, verify_otp,create_resend_otp
from sqlalchemy.ext.asyncio import AsyncSession
from src.otp.schema import VerifyOtp
from src.database import get_session
from src.otp.models import OtpModel
from src.auth.models import Users

router = APIRouter(prefix="/otp", tags=["otp"])

@router.post("/generate_otp")
async def generate_otp(user_in :Users, db: AsyncSession = Depends(get_session)):

    await create_send_otp(db, user_in, subject="Your OTP Code")
    return {"message": "OTP sent to email"}


@router.post("/verify_otp")
async def verify_otp_endpoint(user_in :VerifyOtp, db: AsyncSession = Depends(get_session)):
    email = user_in.email
    otp = user_in.otp

    is_valid = await verify_otp(db, email, otp)
    if is_valid:
        return {"message": "OTP is valid"}
    else:
        return {"message": "OTP is invalid or expired"}  

@router.post("/resend_otp")
async def resend_otp_endpoint(email: str, db: AsyncSession = Depends(get_session)):

    await create_resend_otp(db, email, subject="Resend OTP Code")
    return {"message": "OTP resent to email"}