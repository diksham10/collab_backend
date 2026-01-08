from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from uuid import UUID, uuid4

if TYPE_CHECKING:
    from auth.models import Users  # type hint only

class OtpModel(SQLModel, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id")
    otp_code: str
    created_at: Optional[str] = None
    expires_at: Optional[str] = None
    is_used: bool = False

    # Relationship using forward reference
    user: "Users" = Relationship(back_populates="otps")

# Resolve forward references at the end
from src.auth.models import Users
OtpModel.update_forward_refs()
