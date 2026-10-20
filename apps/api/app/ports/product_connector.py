from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class ParsedProduct:
    title: str
    description: str
    category_path: tuple[str, ...]
    images: tuple[str, ...]
    price_amount: Decimal | None
    price_currency: str | None
    raw_payload: dict[str, Any]
    resolution_digest: str | None = None


class ProductConnector(Protocol):
    async def fetch(self, url: str) -> ParsedProduct: ...
