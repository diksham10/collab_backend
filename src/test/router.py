from fastapi import APIRouter
from src.wow import send_email
from src.otp.service import create_send_otp

router = APIRouter()

@router.get("/test")
async def test_endpoint():
    await send_email(to_mail="khiunjuk13@gmail.com", subject="fuck you", body="sulu le vaneko fuck you re.")
    return {"message": "Test email sent"}


