from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.db.session import get_db
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new internal user (attorney). First registered user becomes admin."""
    from app.models.user import UserRole
    from sqlalchemy import func, select
    from app.models.user import User

    count_result = await db.execute(select(func.count()).select_from(User))
    user_count = count_result.scalar()
    role = UserRole.ADMIN if user_count == 0 else UserRole.ATTORNEY

    user = await auth_service.register_user(db, email=body.email, password=body.password, role=role)
    token = create_access_token(subject=str(user.id), role=user.role.value)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate an internal user and return a JWT."""
    token = await auth_service.authenticate_user(db, email=body.email, password=body.password)
    return TokenResponse(access_token=token)
