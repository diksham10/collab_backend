import secrets
from typing import Optional
from datetime import datetime, timezone, timedelta
from src.otp.models import OtpModel
from src.auth.models import Users
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.wow import send_email


def generate_otp() ->str:
    return str(secrets.randbelow(1000000)).zfill(6)
    
async def create_send_otp(session: AsyncSession, user: Users, subject:str):

    otp = generate_otp()
    
    now= datetime.utcnow()
    expires= now  + timedelta(minutes=5)

    result =session.execute(select(OtpModel).where(OtpModel.user_id == user.id, OtpModel.is_used == False))
    old_otp = result.scalars().first()
    for record in old_otp:
        record.is_used = True

    new_otp = OtpModel(
        user_id = user.id,
        otp_code = otp,
        created_at = now.isoformat(),
        expires_at = expires.isoformat(),
        is_used = False
    )
    session.add(new_otp)
    session.commit()

    #email send
    await send_email(
        to_mail = user.email,
        subject = subject,
        body = f"Your OTP code is {otp}. It will expire in 5 minutes."
    )

async def verify_otp(session: AsyncSession, user: Users, otp_code: str) -> bool:
      
    result = await session.execute(
        select(OtpModel).where(OtpModel.user_id == user.id, OtpModel.is_used == False)
    )
    otp_record = result.scalars().first()

    if not otp_record:
        return False

    now = datetime.utcnow()
    if now > otp_record.expires_at:
        return False

    if otp_record.otp_code != otp_code:
        return False

    otp_record.is_used = True
    session.add(otp_record)
    await session.commit()

    return True
    

    
    


