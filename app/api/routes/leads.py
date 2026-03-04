import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Request, UploadFile, status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import get_current_user
from app.core.rate_limit import limiter
from app.models.user import User
from app.db.session import get_db
from app.schemas.lead import AuditLogResponse, LeadCreateForm, LeadResponse, LeadStateUpdate
from app.services import audit_service, auth_service, file_service, lead_service, notification_service

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
@limiter.limit(f"{settings.rate_limit_per_minute}/minute;{settings.rate_limit_per_hour}/hour")
async def create_lead(
    request: Request,
    background_tasks: BackgroundTasks,
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

    attorney_emails = await auth_service.list_active_attorney_emails(db)

    background_tasks.add_task(
        notification_service.notify_new_lead,
        prospect_email=form.email,
        first_name=form.first_name,
        last_name=form.last_name,
        resume_filename=resume.filename or "unknown",
        attorney_emails=attorney_emails,
    )
    background_tasks.add_task(
        audit_service.record_action,
        entity_type="lead",
        entity_id=lead.id,
        action="lead_created",
        lead_id=lead.id,
        detail=f"Lead submitted by {form.first_name} {form.last_name} ({form.email})",
    )
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
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Internal endpoint — attorney marks a lead as REACHED_OUT."""
    lead = await lead_service.get_lead(db, lead_id)
    old_state = lead.state.value

    updated_lead = await lead_service.update_lead_state(db, lead_id, body.state)

    background_tasks.add_task(
        audit_service.record_state_change,
        lead_id=lead_id,
        user_id=user.id,
        user_email=user.email,
        old_state=old_state,
        new_state=body.state.value,
    )

    return updated_lead


@router.get("/{lead_id}/resume-url")
async def get_resume_url(
    lead_id: uuid.UUID,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Internal endpoint — generate a download URL for the lead's resume."""
    lead = await lead_service.get_lead(db, lead_id)
    url = file_service.get_resume_url(lead.resume_path)
    return {"url": url}


@router.get("/{lead_id}/audit-log", response_model=list[AuditLogResponse])
async def get_lead_audit_log(
    lead_id: uuid.UUID,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Internal endpoint — view audit trail for a specific lead."""
    await lead_service.get_lead(db, lead_id)
    return await audit_service.get_lead_audit_logs(db, lead_id)
