import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.api.routes import admin, auth, leads
from app.core.config import settings
from app.db.seed import seed_admin, seed_attorney
from app.db.session import async_session_factory, engine
from app.models.base import Base
import app.models  # noqa: F401 — register all models with Base.metadata

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info("environment=%s", settings.environment)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as session:
        await seed_admin(session)
        await seed_attorney(session)

    yield


app = FastAPI(
    title="Alma Lead Management",
    description="API for managing prospect leads with resume uploads",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_MAX_REQUEST_BYTES = (settings.max_upload_size_mb + 1) * 1024 * 1024


@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > _MAX_REQUEST_BYTES:
        return JSONResponse(
            status_code=413,
            content={"detail": f"Request too large. Max upload size: {settings.max_upload_size_mb} MB"},
        )
    return await call_next(request)


app.include_router(leads.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(admin.router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok"}
