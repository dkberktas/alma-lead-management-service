import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.lead import Lead, LeadState
from app.models.user import User


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
    result = await db.execute(
        select(Lead)
        .options(joinedload(Lead.reached_out_by))
        .where(Lead.id == lead_id)
    )
    lead = result.unique().scalar_one_or_none()
    if lead is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    return lead


async def list_leads(
    db: AsyncSession,
    *,
    state: LeadState | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Lead], int]:
    """Return paginated leads with optional state filter, plus total count."""
    query = select(Lead).options(joinedload(Lead.reached_out_by))
    count_query = select(func.count(Lead.id))

    if state is not None:
        query = query.where(Lead.state == state)
        count_query = count_query.where(Lead.state == state)

    total = (await db.execute(count_query)).scalar_one()

    query = query.order_by(Lead.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    return list(result.unique().scalars().all()), total


async def update_lead_state(
    db: AsyncSession, lead_id: uuid.UUID, new_state: LeadState, *, user: User
) -> Lead:
    lead = await get_lead(db, lead_id)

    if lead.state == LeadState.REACHED_OUT and new_state == LeadState.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot transition from REACHED_OUT back to PENDING",
        )

    lead.state = new_state

    if new_state == LeadState.REACHED_OUT:
        lead.reached_out_at = datetime.now(timezone.utc)
        lead.reached_out_by_id = user.id

    await db.commit()
    await db.refresh(lead, attribute_names=["reached_out_by"])
    return lead
