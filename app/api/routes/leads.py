import uuid

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.models.user import User
from app.db.session import get_db
from app.schemas.lead import LeadCreateForm, LeadResponse, LeadStateUpdate
from app.services import email_service, file_service, lead_service

router = APIRouter(prefix="/leads", tags=["leads"])


async def _parse_lead_form(
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
) -> LeadCreateForm:
    """Dependency that validates lead form fields via Pydantic."""
    try:
        return LeadCreateForm(first_name=first_name, last_name=last_name, email=email)
    except ValidationError as exc:
        raise RequestValidationError(exc.errors())


@router.post("", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
async def create_lead(
    form: LeadCreateForm = Depends(_parse_lead_form),
    resume: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Public endpoint — prospects submit their information and resume."""
    resume_path = await file_service.save_resume(resume)

    lead = await lead_service.create_lead(
        db,
        first_name=form.first_name,
        last_name=form.last_name,
        email=form.email,
        resume_path=resume_path,
    )

    email_service.notify_new_lead(prospect_email=form.email, first_name=form.first_name)
    return lead


@router.get("", response_model=list[LeadResponse])
async def list_leads(
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Internal endpoint — authenticated attorneys view all leads."""
    return await lead_service.list_leads(db)


@router.get("/{lead_id}", response_model=LeadResponse)
async def get_lead(
    lead_id: uuid.UUID,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Internal endpoint — get a single lead by ID."""
    return await lead_service.get_lead(db, lead_id)


@router.patch("/{lead_id}", response_model=LeadResponse)
async def update_lead_state(
    lead_id: uuid.UUID,
    body: LeadStateUpdate,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Internal endpoint — attorney marks a lead as REACHED_OUT."""
    return await lead_service.update_lead_state(db, lead_id, body.state)
