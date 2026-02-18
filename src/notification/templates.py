from src.myenums import NotificationType

NOTIFICATION_TEMPLATES = {
    NotificationType.new_event: {"title": "New event", "message": "{brand_name} posted a new event"},
    NotificationType.application_update: {
        "applied": {"title": "New application", "message": "{influencer_name} applied on event {event_name}"},
        "accepted": {"title": "Application accepted", "message": "Your application was accepted"},
        "rejected": {"title": "Application rejected", "message": "Your application was rejected"},
    },
    NotificationType.message: {"title": "New message", "message": "{sender_name} sent you a message"}
}
