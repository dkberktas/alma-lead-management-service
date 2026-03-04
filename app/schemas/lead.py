import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, computed_field, field_validator

from app.models.lead import LeadState  # noqa: TC002


class LeadCreateForm(BaseModel):
    """Validates form fields for lead submission."""

    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr

    @field_validator("first_name", "last_name", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip()
        return v


class LeadResponse(BaseModel):
    id: uuid.UUID
    first_name: str
    last_name: str
    email: EmailStr
    state: LeadState
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @computed_field  # type: ignore[prop-decorator]
    @property
    def resume_url(self) -> str:
        """Auth-protected endpoint that returns a short-lived download URL."""
        return f"/api/leads/{self.id}/resume-url"


class LeadStateUpdate(BaseModel):
    state: LeadState


class ResumeUrlResponse(BaseModel):
    url: str


class AuditLogResponse(BaseModel):
    id: uuid.UUID
    entity_type: str
    entity_id: uuid.UUID
    action: str
    user_id: uuid.UUID | None = None
    user_email: str | None = None
    old_state: str | None = None
    new_state: str | None = None
    detail: str | None = None
    lead_id: uuid.UUID | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditLogListResponse(BaseModel):
    items: list[AuditLogResponse]
    total: int
    limit: int
    offset: int


class FileInfoResponse(BaseModel):
    key: str
    size_bytes: int
    last_modified: datetime
