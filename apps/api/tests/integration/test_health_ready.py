from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.session import get_db_session
from app.api import health
from app.main import create_app


async def test_readiness_reports_postgres_available(db_session: AsyncSession) -> None:
    app = create_app()

    async def override_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db_session] = override_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_readiness_reports_dependency_failure() -> None:
    app = create_app()

    class FailingSession:
        async def execute(self, _statement: object) -> None:
            raise SQLAlchemyError("database unavailable")

    async def override_session() -> AsyncIterator[FailingSession]:
        yield FailingSession()

    app.dependency_overrides[get_db_session] = override_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health/ready")

    assert response.status_code == 503
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["code"] == "DEPENDENCY_UNAVAILABLE"


async def test_readiness_reports_missing_provider_key(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(health.settings, "script_provider", "openai_compatible")
    monkeypatch.setattr(health.settings, "provider_api_key", None)
    app = create_app()

    async def override_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db_session] = override_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["code"] == "PROVIDER_MISCONFIGURED"


async def test_readiness_reports_blank_provider_key(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(health.settings, "script_provider", "openai_compatible")
    monkeypatch.setattr(health.settings, "provider_api_key", SecretStr("   "))
    app = create_app()

    async def override_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db_session] = override_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["code"] == "PROVIDER_MISCONFIGURED"
