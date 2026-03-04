import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.models.lead import LeadState


class LeadResponse(BaseModel):
    id: uuid.UUID
    first_name: str
    last_name: str
    email: EmailStr
    resume_path: str
    state: LeadState
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LeadStateUpdate(BaseModel):
    state: LeadState
