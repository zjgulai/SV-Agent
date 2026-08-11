import asyncio

import pytest

from app.adapters.connectors.ssrf import SourceFetchBlocked, SsrfGuard


class StaticResolver:
    def __init__(self, addresses: dict[str, list[str]]) -> None:
        self.addresses = addresses

    async def resolve(self, host: str) -> tuple[str, ...]:
        return tuple(self.addresses.get(host, ()))


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "http://127.0.0.1/product",
        "http://[::1]/product",
        "http://169.254.169.254/latest/meta-data",
        "http://user:pass@example.com/product",
        "https://example.com:80/product",
        "http://example.com:443/product",
        "https://example.com/product?token=secret",
        "https://example.com/product#private",
    ],
)
async def test_ssrf_guard_blocks_non_public_targets(url: str) -> None:
    with pytest.raises(SourceFetchBlocked):
        await SsrfGuard(
            resolver=StaticResolver(
                {
                    "127.0.0.1": ["127.0.0.1"],
                    "::1": ["::1"],
                    "169.254.169.254": ["169.254.169.254"],
                    "example.com": ["93.184.216.34"],
                }
            )
        ).validate(url)


async def test_ssrf_guard_accepts_public_https_target() -> None:
    validated = await SsrfGuard(
        resolver=StaticResolver({"example.com": ["93.184.216.34"]})
    ).validate("https://example.com/product")

    assert validated.hostname == "example.com"
    assert validated.resolved_ips == ("93.184.216.34",)


class SlowResolver:
    async def resolve(self, _host: str) -> tuple[str, ...]:
        await asyncio.sleep(0.1)
        return ("93.184.216.34",)


async def test_ssrf_guard_bounds_dns_resolution_time() -> None:
    with pytest.raises(SourceFetchBlocked, match="resolution timed out"):
        await SsrfGuard(SlowResolver(), resolve_timeout_seconds=0.01).validate(
            "https://example.com/product"
        )
