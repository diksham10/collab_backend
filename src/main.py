# import src.db.model_loader  

from sqlmodel import SQLModel
from src.database import engine
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
app=FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)






from src.auth.router import router as auth_router
from src.otp.router import router as otp_router
from src.test.router import router as test_router

app.include_router(auth_router, tags=["user"])
app.include_router(otp_router,tags=["otp"])
app.include_router(test_router, prefix="/test", tags=["test"])



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
# SQLModel.metadata.create_all(engine) #becuse async engine, we cant use this method to create tables
