from fastapi import HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, time, date
from src.auth.models import Users
from src.brand.models import BrandProfile
from src.influencer.models import InfluencerProfile
from src.event.models import Event, EventApplication
from src.event.schema import EventCreate, EventUpdate, EventApplicationCreate
from uuid import UUID, uuid4
from sqlmodel import select
from typing import Optional


# crud operations for Event model

async def get_event(event_id: str, db: AsyncSession) -> Event:
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalars().first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found.")
    return event
async def get_all_events(db: AsyncSession) -> list[Event]:
    result = await db.execute(select(Event))
    events = result.scalars().all()

    return events


async def get_events_by_brand(brand_id: str, db: AsyncSession) -> list[Event]:
    result = await db.execute(select(Event).where(Event.brand_id == brand_id))
    events = result.scalars().all()
    
    return events


async def create_event(current_users: Users,current_brand_id: str, event_in:EventCreate, db:  AsyncSession) -> Event:
    # Ensure the current user has a brand profile
    result = await db.execute(select(BrandProfile).where(BrandProfile.user_id == current_users.id,BrandProfile.id == current_brand_id))
    brand_profile = result.scalars().first()
    if not brand_profile:
        raise HTTPException(status_code=400, detail="Brand not found for the current user.")
    if str(brand_profile.id) != current_brand_id:
        raise HTTPException(status_code=403, detail="Not authorized to create event for this brand.")
    
    #date handling
    start_dt: Optional[datetime] = None
    if event_in.start_date:
        try:
            # parse string "YYYY-MM-DD" -> date
            start_date_obj = datetime.strptime(event_in.start_date, "%Y-%m-%d").date()
            # convert to datetime at start of day
            start_dt = datetime.combine(start_date_obj, time.min)
        except ValueError:
            raise ValueError("start_date must be in YYYY-MM-DD format")

    end_dt: Optional[datetime] = None
    if event_in.end_date:   
        try:
            # parse string "YYYY-MM-DD" -> date
            end_date_obj = datetime.strptime(event_in.end_date, "%Y-%m-%d").date()
            # convert to datetime at end of day
            end_dt = datetime.combine(end_date_obj, time.max)
        except ValueError:
            raise ValueError("end_date must be in YYYY-MM-DD format")

    new_event = Event(
    user_id= current_users.id,
    brand_id= current_brand_id,
    title= event_in.title,
    description= event_in.description,
    objectives= event_in.objectives,
    budget= event_in.budget,
    start_date= start_dt,
    end_date= end_dt,
    deliverables= event_in.deliverables,
    target_audience= event_in.target_audience,
    category= event_in.category,
    location= event_in.location,
    status= event_in.status,
    )
    try:
        db.add(new_event)
        await db.commit()
        await db.refresh(new_event)
        return new_event
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    

async def delete_event(current_user: Users, event_id: str, db: AsyncSession):

    result1 = await db.execute(select(Event).where(Event.id == event_id))
    event = result1.scalars().first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found.")
    if event.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this event.")
    
    try:
        await db.delete(event)
        await db.commit()
        return {"message": "Event deleted successfully"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    
async def update_event(current_user: Users, event_id: str, event_in: EventUpdate, db: AsyncSession) -> Event:
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalars().first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found.")
    if event.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this event.")
    
    # Update fields if provided
    if event_in.title is not None:
        event.title = event_in.title
    if event_in.description is not None:
        event.description = event_in.description
    if event_in.objectives is not None:
        event.objectives = event_in.objectives
    if event_in.budget is not None:
        event.budget = event_in.budget
    if event_in.start_date is not None:
        try:
            start_date_obj = datetime.strptime(event_in.start_date, "%Y-%m-%d").date()
            event.start_date = datetime.combine(start_date_obj, time.min)
        except ValueError:
            raise ValueError("start_date must be in YYYY-MM-DD format")
    if event_in.end_date is not None:
        try:
            end_date_obj = datetime.strptime(event_in.end_date, "%Y-%m-%d").date()
            event.end_date = datetime.combine(end_date_obj, time.max)
        except ValueError:
            raise ValueError("end_date must be in YYYY-MM-DD format")
    if event_in.deliverables is not None:
        event.deliverables = event_in.deliverables
    if event_in.target_audience is not None:
        event.target_audience = event_in.target_audience
    if event_in.category is not None:
        event.category = event_in.category
    if event_in.location is not None:
        event.location = event_in.location
    
    try:
        db.add(event)
        await db.commit()
        await db.refresh(event)
        return event
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    


# crud operations for EventApplication model
async def apply_to_event(current_user: Users, application_in: EventApplicationCreate, db: AsyncSession) -> EventApplication:

    result = await db.execute(select(InfluencerProfile).where(InfluencerProfile.user_id == current_user.id))
    current_influencer_profile = result.scalars().first()
    if not current_influencer_profile:
        raise HTTPException(status_code=400, detail="Influencer profile not found for the current user.")
    result1 = await db.execute(select(Event).where(Event.id == application_in.event_id))
    event = result1.scalars().first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found.")
    if event.status != "active":
        raise HTTPException(status_code=400, detail="Cannot apply to an inactive event.")
    # Check if the influencer has already applied to this event
    result2 = await db.execute(select(EventApplication).where(EventApplication.event_id == application_in.event_id, EventApplication.influencer_id == current_influencer_profile.id))
    existing_application = result2.scalars().first()
    if existing_application:
        raise HTTPException(status_code=400, detail="You have already applied to this event.")
    new_application = EventApplication(
        event_id= application_in.event_id,
        influencer_id= application_in.influencer_id,
        status= "pending"
    )
    try:
        db.add(new_application)
        await db.commit()
        await db.refresh(new_application)
        return new_application
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

async def get_event_appplications(event_id: str, db: AsyncSession) -> list[EventApplication]:
    result = await db.execute(select(EventApplication).where(EventApplication.event_id == event_id))
    applications = result.scalars().all()
    return applications

async def update_application_status(application_id: str, new_status: str, db: AsyncSession) -> EventApplication:
    result = await db.execute(select(EventApplication).where(EventApplication.id == application_id))
    application = result.scalars().first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found.")
    
    application.status = new_status
    try:
        db.add(application)
        await db.commit()
        await db.refresh(application)
        return application
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))



