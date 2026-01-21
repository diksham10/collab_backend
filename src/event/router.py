from fastapi import APIRouter,Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.auth.dependencies import get_current_user
from src.auth.models import Users
from src.event.schema import EventApplicationCreate, EventApplicationRead, EventApplicationStatusUpdate, EventCreate, EventRead, EventUpdate
from src.event.services import create_event, delete_event, get_all_events, get_event, get_events_by_brand, apply_to_event, get_event_appplications, update_event, update_application_status
from src.database import get_session

router = APIRouter()

@router.post("/create_event{current_brand_id}", response_model=EventRead)
async def create_event_endpoint(event_in: EventCreate, current_brand_id: str, current_users: Users = Depends(get_current_user),db: AsyncSession = Depends(get_session)):  
    new_event = await create_event(current_users,current_brand_id, event_in, db)
    return new_event

@router.get("/eventsbybrand/{brand_id}", response_model= list[EventRead])
async def get_events_by_brand_endpoint( brand_id: str, db: AsyncSession = Depends(get_session)):
    events = await get_events_by_brand( brand_id, db)
    return events


@router.delete("/delete_event/{event_id}")
async def delete_event_endpoint( event_id: str, current_user: Users = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    await delete_event( current_user, event_id, db)

@router.get("/events", response_model= list[EventRead])
async def get_all_events_endpoint(db: AsyncSession = Depends(get_session)):
    events = await get_all_events(db)
    return events

@router.get("/event/{event_id}", response_model= EventRead)
async def get_event_endpoint(event_id: str, db: AsyncSession = Depends(get_session)):
    event = await get_event(event_id, db)
    return event
@router.patch("/update_event/{event_id}", response_model= EventRead)
async def update_event_endpoint(event_id: str, event_in: EventUpdate, current_user: Users = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    updated_event = await update_event(current_user, event_id, event_in, db)
    return updated_event


# event appplications endpoints will be here

@router.post ("/apply_event", response_model=EventApplicationRead)
async def apply_to_event_endpoint(application_in: EventApplicationCreate, db : AsyncSession =Depends(get_current_user)):
    application = await apply_to_event(application_in, db)
    return application

@router.get ("/event_applications/{event_id}", response_model= list[EventApplicationRead])
async def get_event_applications_endpoint(event_id: str, current_user: Users = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    applications = await get_event_appplications(event_id, current_user, db)
    return applications

@router.patch ("/update_application_status/{application_id}", response_model= EventApplicationRead)
async def update_application_status_endpoint(application_id: str, status_in: EventApplicationStatusUpdate, current_user: Users = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    updated_application = await update_application_status(application_id, status_in, current_user, db)
    return updated_application


