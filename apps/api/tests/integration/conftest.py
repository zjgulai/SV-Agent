import os
from collections.abc import AsyncIterator
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.adapters.db.repositories import ProductRepository
from app.domain.products.entities import ProductSnapshot, ProductSource, SourceType


@pytest.fixture(scope="session")
def test_database_url() -> str:
    return os.environ["TEST_DATABASE_URL"]


@pytest.fixture
async def db_session(test_database_url: str) -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(test_database_url)
    connection = await engine.connect()
    transaction = await connection.begin()
    session = async_sessionmaker(bind=connection, expire_on_commit=False)()
    try:
        yield session
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()
        await engine.dispose()


@pytest.fixture
def product_repository(db_session: AsyncSession) -> ProductRepository:
    return ProductRepository(db_session)


@pytest.fixture
async def sample_snapshot(product_repository: ProductRepository) -> ProductSnapshot:
    await product_repository.add_source(
        ProductSource.create(
            id=UUID("00000000-0000-0000-0000-000000000101"),
            source_type=SourceType.MANUAL,
            raw_payload={"title": "Pulse Mix"},
        )
    )
    return ProductSnapshot.create(
        id=UUID("00000000-0000-0000-0000-000000000102"),
        source_id=UUID("00000000-0000-0000-0000-000000000101"),
        title="Pulse Mix",
        description="Energy powder",
        category_path=("Food", "Drink Mix"),
        images=("https://example.com/a.png",),
        price_amount=Decimal("19.90"),
        price_currency="USD",
    )
