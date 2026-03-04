import logging
import time
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.api.routes import admin, auth, leads
from app.core.config import settings
from app.core.rate_limit import limiter
from app.db.seed import seed_admin, seed_attorney
from app.db.session import async_session_factory, get_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info("environment=%s", settings.environment)

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

app.state.limiter = limiter


async def _rate_limit_handler(request: Request, exc: RateLimitExceeded):
    headers = {}
    try:
        rate_limit_info = request.state.view_rate_limit
        if rate_limit_info:
            window_stats = limiter.limiter.get_window_stats(
                rate_limit_info[0], *rate_limit_info[1]
            )
            retry_after = max(0, int(window_stats[0] - time.time()))
            headers["Retry-After"] = str(retry_after)
    except Exception:
        pass
    return JSONResponse(
        status_code=429,
        content={"detail": f"Rate limit exceeded: {exc.detail}"},
        headers=headers,
    )


app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
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
async def health(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "database": "disconnected"},
        )
