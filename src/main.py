# import src.db.model_loader  

from sqlmodel import SQLModel
from src.database import engine
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse
from src.middleware.logging import logging_middleware
from src.redis import redis

app=FastAPI()

@app.on_event("startup")
async def startup_event():
    try:
        await redis.ping()
        print("Redis connected")
    except Exception as e:
        print(" Redis connection failed:", e)
        raise e
@app.on_event("shutdown")
async def shutdown_event():
    await redis.close()
    print("Redis connection closed")


app.middleware("http")(logging_middleware)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000",
                   "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)






from src.auth.router import router as auth_router
from src.otp.router import router as otp_router
from src.test.router import router as test_router
from src.brand.router import router as brand_router
from src.influencer.router import router as influencer_router
from src.event.router import router as event_router
from src.chat.router import router as chat_router

app.include_router(auth_router, tags=["user"])
app.include_router(otp_router,tags=["otp"])
app.include_router(test_router, prefix="/test", tags=["test"])
app.include_router(brand_router, prefix="/brand", tags=["brand"])
app.include_router(influencer_router, prefix="/influencer", tags=["influencer"])
app.include_router(event_router, prefix="/event", tags=["event"])
app.include_router(chat_router, prefix="/chat", tags=["chat"])  


from scalar_fastapi import get_scalar_api_reference

@app.get("/scalar", include_in_schema=False)
async def scalar_html():
    return get_scalar_api_reference(
        openapi_url=app.openapi_url,
        scalar_proxy_url="https://proxy.scalar.com"
    )



def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="Collab Backend API",
        version="1.0.0",
        description="API for collaboration platform",
        routes=app.routes,
    )
    
    # Add OAuth2 security scheme for Swagger UI
    openapi_schema["components"]["securitySchemes"] = {
        "OAuth2PasswordBearer": {
            "type": "oauth2",
            "flows": {
                "password": {
                    "tokenUrl": "/user/token",
                    "scopes": {}
                }
            }
        }
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

@app.get("/")
async def read_root():
    return {"message": "Welcome to the Collab Backend API"}
# SQLModel.metadata.create_all(engine) #because async engine, we cant use this method to create tables

