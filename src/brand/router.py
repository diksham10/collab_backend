from fastapi import APIRouter, Depends
from src.brand.service import create_brand, get_brands, get_brand_by_id
from src.brand.schema import BrandCreate, BrandRead

from sqlalchemy.ext.asyncio import AsyncSession


router = APIRouter()

router.post("/create_profile", response_model= BrandCreate)






router.get("/brand/me{id}", response_model=BrandRead)
