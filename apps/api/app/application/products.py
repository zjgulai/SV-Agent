from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.repositories import ProductRepository
from app.domain.products.entities import (
    FactStatus,
    ProductFact,
    ProductSnapshot,
    ProductSource,
    SourceType,
)
from app.domain.products.errors import LockedFactError


class ProductNotFoundError(Exception):
    pass


class FactNotFoundError(Exception):
    pass


class FactStateConflictError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class FactCommand:
    claim_type: str
    claim: str
    value: dict[str, Any]
    evidence_kind: str
    evidence_locator: str
    evidence_excerpt: str
    confidence: Decimal


@dataclass(frozen=True, slots=True)
class ProductView:
    product_id: UUID
    snapshot: ProductSnapshot
    facts: Sequence[ProductFact]


class ProductService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = ProductRepository(session)

    async def create_manual_product(
        self,
        *,
        title: str,
        description: str | None,
        category_path: tuple[str, ...],
        images: tuple[str, ...],
        price_amount: Decimal | None,
        price_currency: str | None,
        facts: Sequence[FactCommand],
    ) -> ProductView:
        raw_payload: dict[str, Any] = {
            "title": title,
            "description": description,
            "category_path": list(category_path),
            "images": list(images),
            "price_amount": str(price_amount) if price_amount is not None else None,
            "price_currency": price_currency,
        }
        source = ProductSource.create(
            source_type=SourceType.MANUAL,
            raw_payload=raw_payload,
        )
        snapshot = ProductSnapshot.create(
            source_id=source.id,
            title=title,
            description=description,
            category_path=category_path,
            images=images,
            price_amount=price_amount,
            price_currency=price_currency,
        )
        product_facts = [self._new_fact(snapshot.id, item) for item in facts]

        async with self.session.begin():
            await self.repository.add_source(source)
            await self.repository.add_snapshot(snapshot)
            for fact in product_facts:
                await self.repository.add_fact(fact)

        return ProductView(product_id=source.id, snapshot=snapshot, facts=product_facts)

    async def list_products(self) -> Sequence[ProductView]:
        products: list[ProductView] = []
        for source in await self.repository.list_sources():
            snapshot = await self.repository.get_latest_snapshot(source.id)
            if snapshot is not None:
                products.append(
                    ProductView(
                        product_id=source.id,
                        snapshot=snapshot,
                        facts=await self.repository.list_facts(snapshot.id),
                    )
                )
        return products

    async def get_product(self, product_id: UUID) -> ProductView:
        snapshot = await self.repository.get_latest_snapshot(product_id)
        if snapshot is None:
            raise ProductNotFoundError(str(product_id))
        return ProductView(
            product_id=product_id,
            snapshot=snapshot,
            facts=await self.repository.list_facts(snapshot.id),
        )

    async def add_fact(self, product_id: UUID, command: FactCommand) -> ProductFact:
        snapshot = await self.repository.get_latest_snapshot(product_id)
        if snapshot is None:
            raise ProductNotFoundError(str(product_id))
        fact = self._new_fact(snapshot.id, command)
        async with self.session.begin():
            await self.repository.add_fact(fact)
        return fact

    async def transition_fact(
        self, product_id: UUID, fact_id: UUID, status: FactStatus
    ) -> ProductFact:
        async with self.session.begin():
            fact = await self.repository.get_fact(fact_id, for_update=True)
            if fact is None:
                raise FactNotFoundError(str(fact_id))
            snapshot = await self.repository.get_snapshot(fact.snapshot_id)
            if snapshot is None or snapshot.source_id != product_id:
                raise FactNotFoundError(str(fact_id))
            try:
                updated = fact.transition_to(status)
            except LockedFactError as exc:
                raise FactStateConflictError(str(exc)) from exc
            await self.repository.save_fact(updated)
        return updated

    @staticmethod
    def _new_fact(snapshot_id: UUID, command: FactCommand) -> ProductFact:
        return ProductFact.create(
            snapshot_id=snapshot_id,
            claim_type=command.claim_type,
            claim=command.claim,
            value=command.value,
            evidence_kind=command.evidence_kind,
            evidence_locator=command.evidence_locator,
            evidence_excerpt=command.evidence_excerpt,
            confidence=command.confidence,
        )
