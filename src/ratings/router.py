from fastapi import Depends, HTTPException, APIRouter
from src.auth.dependencies import get_current_user
from src.database import get_session
from src.ratings.schema import RatingCreate, RatingRead, RatingUpdate, ratingAvgRead
from src.ratings.models import Rating
from src.ratings.services import create_rating, update_rating, get_rating_by_id

router = APIRouter()

@router.post("/create_rating", response_model=RatingRead)
async def create_rating_endpoint(rating_create: RatingCreate, db=Depends(get_session), current_user=Depends(get_current_user)):
    rating = await create_rating(rating_create, db)
    return rating

@router.get("/rating/{user_id}", response_model=ratingAvgRead)
async def get_rating_endpoint(user_id: str, db=Depends(get_session), current_user=Depends(get_current_user)):
    rating = await get_rating_by_id(user_id, db)
    if not rating:
        raise HTTPException(status_code=404, detail="Rating not found")
    return rating

@router.put("/rating/{rating_id}", response_model=RatingRead)
async def update_rating_endpoint(rating_id: str, rating_update: RatingUpdate, db=Depends(get_session), current_user=Depends(get_current_user)):
    rating = await update_rating(rating_id, rating_update, db)
    if not rating:
        raise HTTPException(status_code=404, detail="Rating not found")
    return rating

