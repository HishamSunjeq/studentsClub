import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.models.user import UserRole


class UserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    college: str
    academic_year: int
    role: UserRole
    email_verified_at: datetime | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
