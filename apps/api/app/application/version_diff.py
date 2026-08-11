from typing import Any

_IGNORED_FIELDS = {"id", "created_at"}


def _flatten(value: Any, path: str = "") -> dict[str, Any]:
    flattened: dict[str, Any] = {}
    if isinstance(value, dict):
        for key in sorted(value):
            if key in _IGNORED_FIELDS:
                continue
            child_path = f"{path}.{key}" if path else key
            flattened.update(_flatten(value[key], child_path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            flattened.update(_flatten(item, f"{path}[{index}]"))
    else:
        flattened[path] = value
    return flattened


def diff_versions(left: dict[str, Any], right: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    left_flat = _flatten(left)
    right_flat = _flatten(right)
    left_paths = set(left_flat)
    right_paths = set(right_flat)
    added = [{"path": path, "value": right_flat[path]} for path in sorted(right_paths - left_paths)]
    removed = [{"path": path, "value": left_flat[path]} for path in sorted(left_paths - right_paths)]
    changed = [
        {"path": path, "left": left_flat[path], "right": right_flat[path]}
        for path in sorted(left_paths & right_paths)
        if left_flat[path] != right_flat[path]
    ]
    return {"added": added, "removed": removed, "changed": changed}
