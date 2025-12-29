from enums import Enum

class UserRole(Enum):
    brand="brand"
    influencer="influencer"
    admin="admin"

class ApplicationStatus(Enum):
    pending="pending"
    accepted="accepted" 
    rejected="rejected"

class NotificationType(Enum):
    new_event="new_event"
    application_update="application_update"
    message="message"
    profile_change="profile_change"
    other="other"

class SocialMedia(Enum):
    facebook="facebook"
    instagram="instagram"
    tiktok="tiktok"
    youtube="youtube"
    other="other"

class AdminAction:
    userban="userban"
    eventdelete="eventdelete"
    

