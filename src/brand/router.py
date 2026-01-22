from fastapi import APIRouter, Depends
from src.database import get_session
from src.brand.service import create_brand, get_brands, delete_brand, update_brand, get_brand_by_id
from src.brand.schema import BrandCreate, BrandRead, BrandUpdate
from src.auth.models import Users
from src.auth.dependencies import get_current_user
from src.brand.dependencies import check_brand_limit
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession


router = APIRouter()

@router.post("/create_brandprofile", response_model= BrandRead)
async def create_brandprofile( brand_in: BrandCreate, current_user: Users =Depends(get_current_user), db: AsyncSession = Depends(get_session),_: None = Depends(check_brand_limit)):
    new_brand = await create_brand(brand_in, current_user, db)
    return new_brand
db: AsyncSession = Depends(get_session)

@router.get("/brandbyid/{brand_id}", response_model= BrandRead)
async def get_brand_by_id_endpoint( brand_id: UUID, db: AsyncSession=Depends(get_session)):
    brand = await get_brand_by_id(brand_id, db)
    return brand

@router.get("/brandsbyuser", response_model= list[BrandRead])
async def get_brand(current_user: Users = Depends(get_current_user), db: AsyncSession=Depends(get_session)):
    brands = await get_brands(current_user, db)
    return brands



@router.put("/update_brandprofile/{brand_id}", response_model= BrandRead)
async def update_brandprofile(brand_id: UUID, brand_in: BrandUpdate, current_user: Users =Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    updated_brand = await update_brand(current_user, brand_id, brand_in, db)
    return updated_brand


@router.delete("/delete_brandprofile/{brand_id}")
async def delete_brandprofile(brand_id: UUID, current_user: Users =Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    print("Deleting brand profile with ID:", brand_id)
    payload = await delete_brand(current_user, brand_id, db)
    return payload