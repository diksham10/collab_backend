from fastapi import APIRouter,Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.auth.dependencies import get_current_user
from src.auth.models import Users
from src.influencer.models import InfluencerProfile
from src.event.models import Event
from src.event.schema import EventApplicationCreate, EventApplicationRead, EventApplicationStatusUpdate, EventCreate, EventRead, EventUpdate, UserPreference
from src.event.services import create_event, delete_event, get_all_events, get_event, get_events_by_brand, apply_to_event, get_event_appplications, update_event, update_application_status
from src.database import get_session
from src.notification.services import create_notification
from src.myenums import NotificationType
from uuid import UUID

router = APIRouter()

@router.post("/create_event{current_brand_id}", response_model=EventRead)
async def create_event_endpoint(event_in: EventCreate, current_brand_id: str, current_users: Users = Depends(get_current_user),db: AsyncSession = Depends(get_session)):  
    new_event = await create_event(current_users,current_brand_id, event_in, db)
    return new_event

@router.get("/eventsbybrand/{brand_id}", response_model= list[EventRead])
async def get_events_by_brand_endpoint( brand_id: UUID, db: AsyncSession = Depends(get_session)):
    events = await get_events_by_brand( brand_id, db)
    return events


@router.delete("/delete_event/{event_id}")
async def delete_event_endpoint( event_id: UUID, current_user: Users = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    await delete_event( current_user, event_id, db)

@router.post("/eventsusinghybrid", response_model= list[EventRead])
async def get_all_events_endpoint(user_pref: UserPreference, db: AsyncSession = Depends(get_session)):
    events = await get_all_events(user_pref=user_pref, db=db)
    return events

@router.get("/eventbyid/{event_id}", response_model= EventRead)
async def get_event_endpoint(event_id: UUID, db: AsyncSession = Depends(get_session)):
    event = await get_event(event_id, db)
    return event

@router.patch("/update_event/{event_id}", response_model= EventRead)
async def update_event_endpoint(event_id: UUID, event_in: EventUpdate, current_user: Users = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    updated_event = await update_event(current_user, event_id, event_in, db)
    return updated_event


# event appplications endpoints will be here

@router.post ("/apply_event", response_model=EventApplicationRead)
async def apply_to_event_endpoint(application_in: EventApplicationCreate, user: Users = Depends(get_current_user), db : AsyncSession = Depends(get_session)):
    application = await apply_to_event(user,application_in, db)
     # Get the event to find the brand owner's user_id
    event_result = await db.execute(
        select(Event).where(Event.id == application_in.event_id)
    )
    event = event_result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Get influencer profile for the name
    influencer_result = await db.execute(
        select(InfluencerProfile).where(InfluencerProfile.id == application_in.influencer_id)
    )
    influencer = influencer_result.scalar_one_or_none()
    if not influencer:
        raise HTTPException(status_code=404, detail="Influencer profile not found")
    

    # create notification for brand
    try:
        await create_notification(
            db=db,
            user_id=event.user_id,
            type=NotificationType.application_update,
            context={
                "status": "applied",
                "influencer_name": influencer.name
            },
            data ={
                "application_id": str(application.id),
                "influencer_id": str(influencer.id),
                "event_id": str(event.id)
            }
        )
    except Exception as e:
        print(f"Failed to create notification: {e}")

    return application

@router.get ("/event_applications/{event_id}", response_model= list[EventApplicationRead])
async def get_event_applications_endpoint(event_id: UUID, current_user: Users = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    applications = await get_event_appplications(event_id, current_user, db)
    return applications

@router.patch ("/update_application_status/{application_id}", response_model= EventApplicationRead)
async def update_application_status_endpoint(application_id: UUID, status_in: EventApplicationStatusUpdate, current_user: Users = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    updated_application = await update_application_status(application_id, status_in, current_user, db)
    return updated_application




