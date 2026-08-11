import asyncio
import ipaddress
import socket
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlsplit


class SourceFetchBlocked(Exception):
    code = "SOURCE_FETCH_BLOCKED"


class Resolver(Protocol):
    async def resolve(self, host: str) -> tuple[str, ...]: ...


class SystemResolver:
    async def resolve(self, host: str) -> tuple[str, ...]:
        loop = asyncio.get_running_loop()
        records = await loop.getaddrinfo(host, None, type=socket.SOCK_STREAM)
        return tuple(sorted({str(record[4][0]) for record in records}))


@dataclass(frozen=True, slots=True)
class ValidatedPublicUrl:
    url: str
    hostname: str
    port: int
    resolved_ips: tuple[str, ...]


class SsrfGuard:
    def __init__(
        self,
        resolver: Resolver | None = None,
        *,
        resolve_timeout_seconds: float = 3,
    ) -> None:
        self.resolver = resolver or SystemResolver()
        self.resolve_timeout_seconds = resolve_timeout_seconds

    async def validate(self, url: str) -> ValidatedPublicUrl:
        try:
            parsed = urlsplit(url)
            port = parsed.port
        except ValueError as exc:
            raise SourceFetchBlocked("URL cannot be parsed") from exc

        if parsed.scheme not in {"http", "https"}:
            raise SourceFetchBlocked("Only public HTTP and HTTPS URLs are allowed")
        if parsed.username is not None or parsed.password is not None:
            raise SourceFetchBlocked("URL user information is not allowed")
        if parsed.hostname is None:
            raise SourceFetchBlocked("URL hostname is required")
        if parsed.query or parsed.fragment:
            raise SourceFetchBlocked("URL query and fragment are not allowed")

        expected_port = 443 if parsed.scheme == "https" else 80
        effective_port = port or expected_port
        if effective_port != expected_port:
            raise SourceFetchBlocked("URL port must match its HTTP scheme")

        try:
            addresses = await asyncio.wait_for(
                self.resolver.resolve(parsed.hostname),
                timeout=self.resolve_timeout_seconds,
            )
        except TimeoutError as exc:
            raise SourceFetchBlocked("Hostname resolution timed out") from exc
        except (OSError, UnicodeError) as exc:
            raise SourceFetchBlocked("Hostname could not be resolved") from exc
        if not addresses:
            raise SourceFetchBlocked("Hostname did not resolve to a public address")

        normalized: list[str] = []
        for address in addresses:
            try:
                ip = ipaddress.ip_address(address)
            except ValueError as exc:
                raise SourceFetchBlocked("Resolver returned an invalid address") from exc
            if not ip.is_global:
                raise SourceFetchBlocked("Target resolves to a non-public address")
            normalized.append(str(ip))

        return ValidatedPublicUrl(
            url=url,
            hostname=parsed.hostname.lower(),
            port=effective_port,
            resolved_ips=tuple(sorted(set(normalized))),
        )
