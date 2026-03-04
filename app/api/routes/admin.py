import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import CreateAttorneyRequest, UserResponse
from app.schemas.lead import AuditLogListResponse, FileInfoResponse
from app.services import audit_service, auth_service, file_service

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/attorneys", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_attorney(
    body: CreateAttorneyRequest,
    background_tasks: BackgroundTasks,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin-only: create a new attorney account."""
    user = await auth_service.register_user(db, email=body.email, password=body.password)
    background_tasks.add_task(
        audit_service.record_action,
        entity_type="user",
        entity_id=user.id,
        action="attorney_created",
        user_id=admin.id,
        user_email=admin.email,
        detail=f"Created attorney account {user.email}",
    )
    return user


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin-only: list all users (admins and attorneys)."""
    return await auth_service.list_users(db)


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: uuid.UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin-only: get a single user by ID."""
    return await auth_service.get_user(db, user_id)


@router.patch("/users/{user_id}/deactivate", response_model=UserResponse)
async def deactivate_user(
    user_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin-only: soft-delete a user. Login will no longer work for them."""
    user = await auth_service.deactivate_user(db, user_id, requesting_user=admin)
    background_tasks.add_task(
        audit_service.record_action,
        entity_type="user",
        entity_id=user.id,
        action="user_deactivated",
        user_id=admin.id,
        user_email=admin.email,
        detail=f"Deactivated {user.email}",
    )
    return user


@router.patch("/users/{user_id}/reactivate", response_model=UserResponse)
async def reactivate_user(
    user_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin-only: re-enable a previously deactivated user account."""
    user = await auth_service.reactivate_user(db, user_id)
    background_tasks.add_task(
        audit_service.record_action,
        entity_type="user",
        entity_id=user.id,
        action="user_reactivated",
        user_id=admin.id,
        user_email=admin.email,
        detail=f"Reactivated {user.email}",
    )
    return user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin-only: permanently delete a user. Prefer deactivate for soft delete."""
    target = await auth_service.get_user(db, user_id)
    target_email = target.email
    target_id = target.id
    await auth_service.delete_user(db, user_id, requesting_user=admin)
    background_tasks.add_task(
        audit_service.record_action,
        entity_type="user",
        entity_id=target_id,
        action="user_deleted",
        user_id=admin.id,
        user_email=admin.email,
        detail=f"Deleted user {target_email}",
    )


@router.get("/files", response_model=list[FileInfoResponse])
async def list_files(
    admin: User = Depends(require_admin),
):
    """Admin-only: list all uploaded files from the configured storage backend."""
    return await file_service.list_files()


@router.get("/audit-logs", response_model=AuditLogListResponse)
async def list_audit_logs(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    entity_type: str | None = Query(None, description="Filter by entity type (lead, user)"),
    action: str | None = Query(None, description="Filter by action"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Admin-only: view the full audit trail with optional filters."""
    items, total = await audit_service.get_all_audit_logs(
        db,
        entity_type=entity_type,
        action=action,
        limit=limit,
        offset=offset,
    )
    return AuditLogListResponse(items=items, total=total, limit=limit, offset=offset)
