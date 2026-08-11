import asyncio
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.connectors.ssrf import SourceFetchBlocked, SsrfGuard
from app.adapters.db.session import get_db_session
from app.api.problems import ApiProblem
from app.api.routes.product_imports import get_ssrf_guard
from app.api.schemas.products import (
    FactInput,
    FactStatusInput,
    ManualProductInput,
    ProductFactOutput,
    ProductOutput,
    ProductSnapshotOutput,
)
from app.application.products import (
    FactCommand,
    FactNotFoundError,
    FactStateConflictError,
    ProductNotFoundError,
    ProductService,
    ProductView,
)
from app.domain.products.entities import ProductFact

router = APIRouter(prefix="/api/v1/products", tags=["products"])
SessionDependency = Annotated[AsyncSession, Depends(get_db_session)]


def _fact_command(value: FactInput) -> FactCommand:
    return FactCommand(
        claim_type=value.claim_type,
        claim=value.claim,
        value=value.value,
        evidence_kind="user_assertion",
        evidence_locator="manual-form",
        evidence_excerpt=value.evidence_excerpt,
        confidence=Decimal(1),
    )


def _fact_output(fact: ProductFact) -> ProductFactOutput:
    return ProductFactOutput(
        id=fact.id,
        snapshot_id=fact.snapshot_id,
        claim_type=fact.claim_type,
        claim=fact.claim,
        value=fact.value,
        evidence_kind=fact.evidence_kind,
        evidence_locator=fact.evidence_locator,
        evidence_excerpt=fact.evidence_excerpt,
        confidence=fact.confidence,
        status=fact.status,
        updated_at=fact.updated_at,
    )


def _product_output(product: ProductView) -> ProductOutput:
    snapshot = product.snapshot
    return ProductOutput(
        product_id=product.product_id,
        snapshot=ProductSnapshotOutput(
            id=snapshot.id,
            source_id=snapshot.source_id,
            title=snapshot.title,
            description=snapshot.description,
            category_path=list(snapshot.category_path),
            images=list(snapshot.images),
            price_amount=snapshot.price_amount,
            price_currency=snapshot.price_currency,
            canonical_digest=snapshot.canonical_digest,
            created_at=snapshot.created_at,
        ),
        facts=[_fact_output(item) for item in product.facts],
    )


def _not_found(detail: str) -> ApiProblem:
    return ApiProblem(status=404, code="PRODUCT_NOT_FOUND", title="Product not found", detail=detail)


@router.post("", response_model=ProductOutput, status_code=status.HTTP_201_CREATED)
async def create_product(
    payload: ManualProductInput,
    session: SessionDependency,
    guard: Annotated[SsrfGuard, Depends(get_ssrf_guard)],
) -> ProductOutput:
    try:
        images = await asyncio.gather(
            *(guard.validate(str(image)) for image in payload.images)
        )
    except SourceFetchBlocked as exc:
        raise ApiProblem(
            status=422,
            code="IMAGE_URL_BLOCKED",
            title="Product image URL blocked",
            detail="Every product image must pass the public-network safety policy.",
        ) from exc
    view = await ProductService(session).create_manual_product(
        title=payload.title,
        description=payload.description,
        category_path=tuple(payload.category_path),
        images=tuple(item.url for item in images),
        price_amount=payload.price.amount if payload.price else None,
        price_currency=payload.price.currency if payload.price else None,
        facts=[_fact_command(item) for item in payload.facts],
    )
    return _product_output(view)


@router.get("", response_model=list[ProductOutput])
async def list_products(session: SessionDependency) -> list[ProductOutput]:
    return [_product_output(item) for item in await ProductService(session).list_products()]


@router.get("/{product_id}", response_model=ProductOutput)
async def get_product(product_id: UUID, session: SessionDependency) -> ProductOutput:
    try:
        return _product_output(await ProductService(session).get_product(product_id))
    except ProductNotFoundError as exc:
        raise _not_found("The requested product does not exist.") from exc


@router.post(
    "/{product_id}/facts",
    response_model=ProductFactOutput,
    status_code=status.HTTP_201_CREATED,
)
async def create_fact(
    product_id: UUID, payload: FactInput, session: SessionDependency
) -> ProductFactOutput:
    try:
        fact = await ProductService(session).add_fact(product_id, _fact_command(payload))
    except ProductNotFoundError as exc:
        raise _not_found("The requested product does not exist.") from exc
    return _fact_output(fact)


@router.patch("/{product_id}/facts/{fact_id}", response_model=ProductFactOutput)
async def transition_fact(
    product_id: UUID,
    fact_id: UUID,
    payload: FactStatusInput,
    session: SessionDependency,
) -> ProductFactOutput:
    try:
        fact = await ProductService(session).transition_fact(product_id, fact_id, payload.status)
    except (ProductNotFoundError, FactNotFoundError) as exc:
        raise _not_found("The requested product fact does not exist.") from exc
    except FactStateConflictError as exc:
        raise ApiProblem(
            status=409,
            code="FACT_STATE_CONFLICT",
            title="Fact state conflict",
            detail="Locked facts cannot be changed in place.",
        ) from exc
    return _fact_output(fact)
