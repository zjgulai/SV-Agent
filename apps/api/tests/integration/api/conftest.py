import ipaddress
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.adapters.connectors.ssrf import SsrfGuard
from app.adapters.db.session import get_db_session
from app.api.routes.product_imports import get_ssrf_guard
from app.main import create_app


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    app = create_app()
    request_session_factory = async_sessionmaker(
        bind=db_session.bind,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )

    async def override_session() -> AsyncIterator[AsyncSession]:
        async with request_session_factory() as request_session:
            yield request_session

    class StaticResolver:
        async def resolve(self, host: str) -> tuple[str, ...]:
            try:
                return (str(ipaddress.ip_address(host)),)
            except ValueError:
                pass
            return ("93.184.216.34",)

    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_ssrf_guard] = lambda: SsrfGuard(StaticResolver())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as api_client:
        yield api_client
