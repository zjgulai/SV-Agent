import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID


def _decimal_string(value: Decimal) -> str:
    normalized = value.normalize()
    if normalized == 0:
        return "0"
    return format(normalized, "f")


def _canonicalize(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return _canonicalize(asdict(value))
    if isinstance(value, Mapping):
        return {str(key).strip(): _canonicalize(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return [_canonicalize(item) for item in value]
    if isinstance(value, Decimal):
        return _decimal_string(value)
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, Enum):
        return _canonicalize(value.value)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime | date):
        return value.isoformat()
    return value


def canonical_digest(value: Any) -> str:
    canonical_json = json.dumps(
        _canonicalize(value),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
