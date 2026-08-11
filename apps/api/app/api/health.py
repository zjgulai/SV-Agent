from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.session import get_db_session
from app.settings import provider_api_key_is_configured, settings

router = APIRouter(tags=["health"])


@router.get("/health/live")
async def liveness() -> dict[str, str]:
    return {"status": "ok", "service": "reverse-engineer-mode-api"}


@router.get("/health/ready", response_model=None)
async def readiness(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, str] | JSONResponse:
    try:
        await session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return JSONResponse(
            status_code=503,
            media_type="application/problem+json",
            content={
                "type": "about:blank",
                "title": "Service Unavailable",
                "status": 503,
                "detail": "PostgreSQL dependency is unavailable.",
                "code": "DEPENDENCY_UNAVAILABLE",
            },
        )
    if settings.script_provider == "openai_compatible" and not provider_api_key_is_configured(
        settings.provider_api_key
    ):
        return JSONResponse(
            status_code=503,
            media_type="application/problem+json",
            content={
                "type": "about:blank",
                "title": "Service Misconfigured",
                "status": 503,
                "detail": "The configured script provider is missing its API key.",
                "code": "PROVIDER_MISCONFIGURED",
            },
        )
    return {"status": "ok"}
