from pydantic import BaseModel, EmailStr

class VerifyOtp(BaseModel):
    email: EmailStr
    otp_code: str