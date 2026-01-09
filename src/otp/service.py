import secrets
from typing import Optional
from datetime import datetime, timezone, timedelta
from src.otp.models import OtpModel
from src.auth.models import Users
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from src.wow import send_email
from src.otp.schema import VerifyOtp


def generate_otp() ->str:
    return str(secrets.randbelow(1000000)).zfill(6)
    
async def create_send_otp(session: AsyncSession, user: Users, subject:str):

    otp = generate_otp()
    
    now= datetime.utcnow()
    expires= now  + timedelta(minutes=5)

    new_otp = OtpModel(
        user_id = user.id,
        otp_code = otp,
        created_at = now.isoformat(),
        expires_at = expires.isoformat(),
        is_used = False
    )
    session.add(new_otp)
    await session.commit()

    #email send
    await send_email(
        to_mail = user.email,
        subject = subject,
        body = f"Your OTP code is {otp}. It will expire in 5 minutes."
    )

async def verify_otp(session: AsyncSession, user_email:str, otp_code: str) -> bool:
    result1 = await session.execute(
        select(Users).where(Users.email == user_email)
    )
    current_user = result1.scalars().first()
    result = await session.execute(
        select(OtpModel).where(OtpModel.user_id == current_user.id, OtpModel.is_used == False)
    )
    otp_record = result.scalars().first()

    if not otp_record:
        return False

    now = datetime.utcnow()
    timenow = now.isoformat()
    if timenow > otp_record.expires_at:
        return False

    if otp_record.otp_code != otp_code:
        return False
    
    current_user.is_verified = True
    await session.execute(delete(OtpModel).where(OtpModel.id == otp_record.id))
    await session.commit()

    return True
 
     
async def create_resend_otp(session: AsyncSession, user_email: str, subject:str):

    otp = generate_otp()
    
    now= datetime.utcnow()
    expires= now  + timedelta(minutes=5)

    result1 = await session.execute(
        select(Users).where(Users.email == user_email)
    )
    current_user = result1.scalars().first()

    result = await session.execute(select(OtpModel).where(OtpModel.user_id == current_user.id, OtpModel.is_used == False))
    old_otp = result.scalars().all()
    if old_otp:
        await session.execute(delete(OtpModel).where(OtpModel.user_id == current_user.id, OtpModel.is_used == False))
    await session.commit()
    

    new_otp = OtpModel(
        user_id = current_user.id,
        otp_code = otp,
        created_at = now.isoformat(),
        expires_at = expires.isoformat(),
        is_used = False
    )
    session.add(new_otp)
    await session.commit()

    #email send
    await send_email(
        to_mail = current_user.email,
        subject = subject,
        body = f"Your OTP code is {otp}. It will expire in 5 minutes."
    )  


