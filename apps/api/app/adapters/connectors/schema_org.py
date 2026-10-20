import asyncio
import json
from dataclasses import replace
from decimal import Decimal, InvalidOperation
from html import unescape
from html.parser import HTMLParser
from typing import Any
from urllib.parse import SplitResult, urlsplit, urlunsplit

import httpx

from app.adapters.connectors.ssrf import SourceFetchBlocked, SsrfGuard
from app.domain.common.canonical import canonical_digest
from app.ports.product_connector import ParsedProduct

MAX_RESPONSE_BYTES = 1024 * 1024
MAX_IMAGE_COUNT = 20
MAX_IMAGE_URL_LENGTH = 2048
ALLOWED_CONTENT_TYPES = (
    "text/html",
    "application/xhtml+xml",
    "application/json",
    "application/ld+json",
)


class ProductDataMissing(Exception):
    code = "PRODUCT_DATA_MISSING"


class SourceFetchTimeout(Exception):
    code = "SOURCE_FETCH_TIMEOUT"


class SourceTooLarge(Exception):
    code = "SOURCE_TOO_LARGE"


class SourceContentTypeUnsupported(Exception):
    code = "SOURCE_CONTENT_TYPE_UNSUPPORTED"


class SourceHttpError(Exception):
    code = "SOURCE_HTTP_ERROR"


class SourceUnavailable(Exception):
    code = "SOURCE_UNAVAILABLE"


class _JsonLdCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[str] = []
        self._active = False
        self._buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key.lower(): (value or "").lower() for key, value in attrs}
        if tag.lower() == "script" and attributes.get("type") == "application/ld+json":
            self._active = True
            self._buffer = []

    def handle_data(self, data: str) -> None:
        if self._active:
            self._buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "script" and self._active:
            self.blocks.append("".join(self._buffer))
            self._active = False
            self._buffer = []


class _PlainTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, _attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style"}:
            self._ignored_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style"} and self._ignored_depth:
            self._ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._ignored_depth:
            self.parts.append(data)


def _plain_text(value: object) -> str:
    parser = _PlainTextExtractor()
    parser.feed(unescape(str(value or "")))
    return " ".join("".join(parser.parts).split())


def _has_product_type(value: object) -> bool:
    if isinstance(value, str):
        return value.lower() == "product" or value.lower().endswith("/product")
    if isinstance(value, list):
        return any(_has_product_type(item) for item in value)
    return False


def _walk_json_ld(value: object) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(value, dict):
        if _has_product_type(value.get("@type")):
            found.append(value)
        for item in value.values():
            found.extend(_walk_json_ld(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(_walk_json_ld(item))
    return found


def _images(value: object) -> tuple[str, ...]:
    candidates = value if isinstance(value, list) else [value]
    images: list[str] = []
    for item in candidates:
        if isinstance(item, str):
            images.append(item.strip())
        elif isinstance(item, dict) and isinstance(item.get("url"), str):
            images.append(item["url"].strip())
    return tuple(
        item
        for item in images[:MAX_IMAGE_COUNT]
        if len(item) <= MAX_IMAGE_URL_LENGTH
        and item.startswith(("http://", "https://"))
    )


def _offer(value: object) -> tuple[Decimal | None, str | None]:
    offer = value[0] if isinstance(value, list) and value else value
    if not isinstance(offer, dict):
        return None, None
    raw_price = offer.get("price") or offer.get("lowPrice")
    try:
        amount = Decimal(str(raw_price)) if raw_price is not None else None
    except InvalidOperation:
        amount = None
    raw_currency = offer.get("priceCurrency")
    currency = str(raw_currency).strip().upper() if raw_currency else None
    return amount, currency


def parse_schema_org_product(document: str) -> ParsedProduct:
    nodes: list[dict[str, Any]] = []
    try:
        nodes.extend(_walk_json_ld(json.loads(document)))
    except json.JSONDecodeError:
        pass
    collector = _JsonLdCollector()
    collector.feed(document)
    for block in collector.blocks:
        try:
            nodes.extend(_walk_json_ld(json.loads(block)))
        except json.JSONDecodeError:
            continue
    if not nodes:
        raise ProductDataMissing("No Schema.org Product JSON-LD was found")

    node = nodes[0]
    title = _plain_text(node.get("name"))
    if not title:
        raise ProductDataMissing("Product name is required")
    description = _plain_text(node.get("description"))
    raw_category = _plain_text(node.get("category"))
    categories = tuple(item.strip() for item in raw_category.split(">") if item.strip())
    images = _images(node.get("image"))
    amount, currency = _offer(node.get("offers"))
    raw_payload: dict[str, Any] = {
        "title": title,
        "description": description,
        "category_path": list(categories),
        "images": list(images),
        "price_amount": str(amount) if amount is not None else None,
        "price_currency": currency,
    }
    return ParsedProduct(
        title=title,
        description=description,
        category_path=categories,
        images=images,
        price_amount=amount,
        price_currency=currency,
        raw_payload=raw_payload,
    )


class SchemaOrgProductConnector:
    def __init__(
        self,
        client: httpx.AsyncClient,
        guard: SsrfGuard | None = None,
        *,
        total_timeout_seconds: float = 12,
    ) -> None:
        self.client = client
        self.guard = guard or SsrfGuard()
        self.total_timeout_seconds = total_timeout_seconds

    async def fetch(self, url: str) -> ParsedProduct:
        try:
            async with asyncio.timeout(self.total_timeout_seconds):
                return await self._fetch(url)
        except TimeoutError as exc:
            raise SourceFetchTimeout("Product source exceeded its total deadline") from exc

    async def _fetch(self, url: str) -> ParsedProduct:
        validated = await self.guard.validate(url)
        parsed_url = urlsplit(validated.url)
        last_network_error: httpx.RequestError | None = None
        for address in validated.resolved_ips:
            try:
                document = await self._download(
                    parsed_url=parsed_url,
                    address=address,
                    hostname=validated.hostname,
                    port=validated.port,
                )
            except httpx.HTTPStatusError as exc:
                raise SourceHttpError("Product source returned an HTTP error") from exc
            except httpx.RequestError as exc:
                last_network_error = exc
                continue
            product = parse_schema_org_product(document)
            product = await self._filter_public_images(product)
            return replace(
                product,
                resolution_digest=canonical_digest(
                    {
                        "hostname": validated.hostname,
                        "resolved_ips": list(validated.resolved_ips),
                    }
                ),
            )

        if isinstance(last_network_error, httpx.TimeoutException):
            raise SourceFetchTimeout("Product source timed out") from last_network_error
        raise SourceUnavailable("Product source could not be reached") from last_network_error

    async def _download(
        self,
        *,
        parsed_url: SplitResult,
        address: str,
        hostname: str,
        port: int,
    ) -> str:
        pinned_host = f"[{address}]" if ":" in address else address
        pinned_url = urlunsplit(
            (
                parsed_url.scheme,
                f"{pinned_host}:{port}",
                parsed_url.path,
                parsed_url.query,
                "",
            )
        )
        original_host = f"[{hostname}]" if ":" in hostname else hostname
        timeout = httpx.Timeout(10, connect=3, read=5)
        async with self.client.stream(
            "GET",
            pinned_url,
            headers={"Host": original_host},
            extensions={"sni_hostname": hostname},
            follow_redirects=False,
            timeout=timeout,
        ) as response:
            response.raise_for_status()
            content_type = (
                response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
            )
            if content_type not in ALLOWED_CONTENT_TYPES:
                raise SourceContentTypeUnsupported(content_type)
            content = bytearray()
            async for chunk in response.aiter_bytes():
                content.extend(chunk)
                if len(content) > MAX_RESPONSE_BYTES:
                    raise SourceTooLarge("Product response exceeds 1 MiB")
            encoding = response.encoding or "utf-8"
        return bytes(content).decode(encoding, "replace")

    async def _filter_public_images(self, product: ParsedProduct) -> ParsedProduct:
        async def validate_image(image_url: str) -> str | None:
            try:
                return (await self.guard.validate(image_url)).url
            except SourceFetchBlocked:
                return None

        validated = await asyncio.gather(
            *(validate_image(image_url) for image_url in product.images)
        )
        images = tuple(item for item in validated if item is not None)
        raw_payload = dict(product.raw_payload)
        raw_payload["images"] = list(images)
        return replace(product, images=images, raw_payload=raw_payload)
