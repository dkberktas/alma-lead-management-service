import uuid

from fastapi import APIRouter, BackgroundTasks

from app.core.security import decode_access_token
from app.db.session import admin_session_factory
from app.schemas.auth import LoginRequest, TokenResponse
from app.services import audit_service, auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    background_tasks: BackgroundTasks,
):
    """Authenticate an internal user and return a JWT."""
    async with admin_session_factory() as session:
        token = await auth_service.authenticate_user(session, email=body.email, password=body.password)

    payload = decode_access_token(token)
    user_id_str = payload.get("sub")

    if user_id_str:
        background_tasks.add_task(
            audit_service.record_action,
            entity_type="user",
            entity_id=uuid.UUID(user_id_str),
            action="user_login",
            user_id=uuid.UUID(user_id_str),
            user_email=body.email,
        )

    return TokenResponse(access_token=token)
