from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship, Column, ForeignKey
from uuid import UUID, uuid4
from sqlalchemy.orm import Mapped

if TYPE_CHECKING:
    from auth.models import Users  # type hint only

class OtpModel(SQLModel, table=True):
    __tablename__ = "otpmodel"

    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(sa_column=Column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False))
    otp_code: str
    created_at: Optional[str] = None
    expires_at: Optional[str] = None
    is_used: bool = False

    # Relationship using forward reference
    user: Mapped["Users"] = Relationship(back_populates="otps")

# Resolve forward references at the end
from src.auth.models import Users
OtpModel.update_forward_refs()
