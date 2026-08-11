from typing import Protocol

from app.adapters.connectors.schema_org import ParsedProduct


class ProductConnector(Protocol):
    async def fetch(self, url: str) -> ParsedProduct: ...
