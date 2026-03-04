import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lead import Lead, LeadState


async def create_lead(
    db: AsyncSession,
    *,
    first_name: str,
    last_name: str,
    email: str,
    resume_path: str,
) -> Lead:
    lead = Lead(
        first_name=first_name,
        last_name=last_name,
        email=email,
        resume_path=resume_path,
    )
    db.add(lead)
    await db.commit()
    await db.refresh(lead)
    return lead


async def get_lead(db: AsyncSession, lead_id: uuid.UUID) -> Lead:
    lead = await db.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    return lead


async def list_leads(db: AsyncSession) -> list[Lead]:
    result = await db.execute(select(Lead).order_by(Lead.created_at.desc()))
    return list(result.scalars().all())


async def update_lead_state(
    db: AsyncSession, lead_id: uuid.UUID, new_state: LeadState
) -> Lead:
    lead = await get_lead(db, lead_id)

    if lead.state == LeadState.REACHED_OUT and new_state == LeadState.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot transition from REACHED_OUT back to PENDING",
        )

    lead.state = new_state
    await db.commit()
    await db.refresh(lead)
    return lead
