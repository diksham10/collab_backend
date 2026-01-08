from pydantic_settings import BaseSettings
import os
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    # SMTP_HOST=os.getenv("SMTP_HOST")
    # SMTP_PORT=os.getenv("SMTP_PORT")
    # SMTP_USER=os.getenv("SMTP_USER")
    # SMTP_PASS=os.getenv("SMTP_PASS")
    # EMAIL_FROM=os.getenv("EMAIL_FROM")
    SMTP_HOST: str
    SMTP_PORT: int
    SMTP_USER: str
    SMTP_PASS: str
    EMAIL_FROM: str


settings=Settings()