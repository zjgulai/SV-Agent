import asyncio
import json
from decimal import Decimal

import httpx
import pytest

from app.adapters.connectors.schema_org import (
    SchemaOrgProductConnector,
    SourceContentTypeUnsupported,
    SourceFetchTimeout,
    SourceHttpError,
    parse_schema_org_product,
)
from app.adapters.connectors.ssrf import SsrfGuard
from tests.fixtures.product_page import PRODUCT_HTML_FIXTURE


class StaticResolver:
    async def resolve(self, host: str) -> tuple[str, ...]:
        return ("93.184.216.34",) if host == "example.com" else ()


class MultiAddressResolver:
    async def resolve(self, _host: str) -> tuple[str, ...]:
        return ("93.184.216.34", "93.184.216.35")


def test_schema_org_parser_extracts_only_product_fields() -> None:
    product = parse_schema_org_product(PRODUCT_HTML_FIXTURE)

    assert product.title == "Pulse Mix"
    assert product.price_amount == Decimal("19.90")
    assert product.price_currency == "USD"
    assert "<script" not in product.description
    assert product.raw_payload == {
        "title": "Pulse Mix",
        "description": "Energy powder in a resealable pouch.",
        "category_path": ["Food", "Drink Mix"],
        "images": ["https://example.com/pulse.png"],
        "price_amount": "19.90",
        "price_currency": "USD",
    }


async def test_connector_pins_connection_to_validated_ip() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "93.184.216.34"
        assert request.url.path == "/product"
        assert request.headers["host"] == "example.com"
        assert request.extensions["sni_hostname"] == "example.com"
        return httpx.Response(
            200,
            headers={"content-type": "text/html; charset=utf-8"},
            text=PRODUCT_HTML_FIXTURE,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        product = await SchemaOrgProductConnector(
            client,
            guard=SsrfGuard(StaticResolver()),
        ).fetch("https://example.com/product")

    assert product.title == "Pulse Mix"


async def test_connector_falls_back_across_validated_public_ips() -> None:
    attempted: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        attempted.append(str(request.url.host))
        if request.url.host == "93.184.216.34":
            raise httpx.ConnectError("first address unavailable", request=request)
        return httpx.Response(
            200,
            headers={"content-type": "text/html"},
            text=PRODUCT_HTML_FIXTURE,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        product = await SchemaOrgProductConnector(
            client, guard=SsrfGuard(MultiAddressResolver())
        ).fetch("https://example.com/product")

    assert product.title == "Pulse Mix"
    assert attempted[:2] == ["93.184.216.34", "93.184.216.35"]


async def test_connector_drops_non_public_product_images() -> None:
    document = json.dumps(
        {
            "@type": "Product",
            "name": "Public image only",
            "image": [
                "https://example.com/public.png",
                "http://169.254.169.254/latest/meta-data",
                "https://user:secret@example.com/private.png",
                "https://example.com:444/wrong-port.png",
            ],
        }
    )

    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, headers={"content-type": "application/ld+json"}, text=document
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        product = await SchemaOrgProductConnector(
            client, guard=SsrfGuard(StaticResolver())
        ).fetch("https://example.com/product")

    assert product.images == ("https://example.com/public.png",)
    assert product.raw_payload["images"] == ["https://example.com/public.png"]


async def test_connector_rejects_content_type_prefix_collision() -> None:
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(
                200,
                headers={"content-type": "application/jsonp"},
                text=PRODUCT_HTML_FIXTURE,
            )
        )
    ) as client:
        with pytest.raises(SourceContentTypeUnsupported):
            await SchemaOrgProductConnector(
                client, guard=SsrfGuard(StaticResolver())
            ).fetch("https://example.com/product")


async def test_connector_parses_direct_schema_org_json() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            text=json.dumps(
                {
                    "@type": "Product",
                    "name": "Pulse Mix JSON",
                    "description": "Resealable pouch",
                }
            ),
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        product = await SchemaOrgProductConnector(
            client, guard=SsrfGuard(StaticResolver())
        ).fetch("https://example.com/product.json")

    assert product.title == "Pulse Mix JSON"


async def test_connector_enforces_total_deadline() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(0.1)
        return httpx.Response(200, headers={"content-type": "text/html"}, text="")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        connector = SchemaOrgProductConnector(
            client,
            guard=SsrfGuard(StaticResolver()),
            total_timeout_seconds=0.01,
        )
        with pytest.raises(SourceFetchTimeout):
            await connector.fetch("https://example.com/product")


async def test_connector_maps_http_failure_without_exposing_url() -> None:
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _request: httpx.Response(503))
    ) as client:
        connector = SchemaOrgProductConnector(client, guard=SsrfGuard(StaticResolver()))
        with pytest.raises(SourceHttpError) as failure:
            await connector.fetch("https://example.com/product")

    assert "example.com" not in str(failure.value)
