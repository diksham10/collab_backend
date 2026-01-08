from enum import Enum

class UserRole(str, Enum):
    brand = "brand"
    influencer = "influencer"
    admin = "admin"

class ApplicationStatus(str, Enum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"

class NotificationType(str, Enum):
    new_event = "new_event"
    application_update = "application_update"
    message = "message"
    profile_change = "profile_change"
    other = "other"

class SocialPlatform(str, Enum):
    instagram = "instagram"
    tiktok = "tiktok"
    youtube = "youtube"
    other = "other"
class AdminAction(str, Enum):
    user_banned = "user_banned"
    user_unbanned = "user_unbanned"
    content_removed = "content_removed"
    other = "other"