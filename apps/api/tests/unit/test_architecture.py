import ast
from pathlib import Path


def test_ports_do_not_import_adapters() -> None:
    ports_root = Path(__file__).parents[2] / "app" / "ports"
    violations: list[str] = []

    for port_path in sorted(ports_root.glob("*.py")):
        tree = ast.parse(port_path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith(
                "app.adapters"
            ):
                violations.append(f"{port_path.name}:{node.lineno}:{node.module}")
            elif isinstance(node, ast.Import):
                violations.extend(
                    f"{port_path.name}:{node.lineno}:{alias.name}"
                    for alias in node.names
                    if alias.name.startswith("app.adapters")
                )

    assert violations == []
