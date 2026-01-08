# import src.db.model_loader  

from sqlmodel import SQLModel
from src.database import engine
from fastapi import FastAPI
# from src.admin_logs.models import  AdminLog
# from src.auth.models import Users
# from src.brand.models import BrandProfile
# from src.chat.models import Message
# from src.event.models import Event, EventApplication
# from src.influencer.models import InfluencerProfile
# from src.notification.models import Notification
# from src.otp.models import OtpModel
# from src.ratings.models import Rating
from src.auth.router import router as auth_router
from src.test.router import router as test_router

app=FastAPI()

app.include_router(auth_router, tags=["user"])
app.include_router(test_router, prefix="/test", tags=["test"])


# SQLModel.metadata.create_all(engine)
