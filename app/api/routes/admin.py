import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import CreateAttorneyRequest, UserResponse
from app.schemas.lead import FileInfoResponse
from app.services import auth_service, file_service

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/attorneys", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_attorney(
    body: CreateAttorneyRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin-only: create a new attorney account."""
    user = await auth_service.register_user(db, email=body.email, password=body.password)
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


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: uuid.UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin-only: delete a user. Admins cannot delete themselves."""
    await auth_service.delete_user(db, user_id, requesting_user=admin)


@router.get("/files", response_model=list[FileInfoResponse])
async def list_files(
    admin: User = Depends(require_admin),
):
    """Admin-only: list all uploaded files from the configured storage backend."""
    return await file_service.list_files()
