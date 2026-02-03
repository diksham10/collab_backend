from src.ratings.models import Rating
from src.ratings.schema import RatingCreate, RatingRead, RatingUpdate, ratingAvgRead
from sqlalchemy import select
from fastapi import HTTPException
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

async def create_rating(rating_create: RatingCreate, db:AsyncSession ) -> RatingRead:

    result = await db.execute(select(Rating).where(
        Rating.rater_id == rating_create.rater_id,
        Rating.ratee_id == rating_create.ratee_id,
        Rating.event_id == rating_create.event_id
    ))
    existing_rating = result.scalars().first()
    if existing_rating:
        raise HTTPException(status_code=400, detail="Rating already exists for this rater, ratee, and event combination.")
    if rating_create.rater_id == rating_create.ratee_id:
        raise HTTPException(status_code=400, detail="Cannot rate yourself.")
    if rating_create.score is not None:
        if rating_create.score < 0 or rating_create.score > 5:
            raise HTTPException(status_code=400, detail="Score must be between 0 and 5.")
        


    new_rating= Rating(
        rater_id = rating_create.rater_id,
        ratee=rating_create.ratee_id,
        event_id=rating_create.event_id,
        score=rating_create.score,
        review=rating_create.review,
        created_at=rating_create.created_at
    )
    try:
        db.add(new_rating)
        await db.commit()
        await db.refresh(new_rating)
        return new_rating
    except Exception as e:
        await db.rollback()
        raise e

async def get_rating_by_id(rating_id: UUID, db:AsyncSession) -> ratingAvgRead:
    result = await db.execute(
        select(Rating).where(Rating.id == rating_id)
    )
    rating = result.scalars().all()

    avg_score = sum(r.score for r in rating)/len(rating) if rating else 0
    avg_rating = {"ratee_id": rating_id, "average_score": avg_score}
    return avg_rating

async def update_rating(rating_id: UUID, rating_update: RatingUpdate, db:AsyncSession) -> RatingRead:   
    result = await db.execute(select(Rating).where(Rating.id == rating_id))
    rating = result.scalars().first()
    if rating:
        if rating_update.score is not None:
            rating.score = rating_update.score
        if rating_update.review is not None:
            rating.review = rating_update.review
        try:
            await db.commit()
            await db.refresh(rating)
            return rating
        except Exception as e:
            await db.rollback()
            raise e
    return rating