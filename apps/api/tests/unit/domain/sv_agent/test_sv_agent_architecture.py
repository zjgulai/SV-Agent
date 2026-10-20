import ast
from pathlib import Path

FORBIDDEN_IMPORT_ROOTS = (
    "app.adapters",
    "app.api",
    "app.worker",
    "celery",
    "fastapi",
    "openai",
    "redis",
    "sqlalchemy",
)


def test_sv_agent_domain_does_not_depend_on_infrastructure() -> None:
    domain_root = Path(__file__).parents[4] / "app" / "domain" / "sv_agent"
    violations: list[str] = []

    for module_path in sorted(domain_root.glob("*.py")):
        tree = ast.parse(module_path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                imported_names = (node.module or "",)
            elif isinstance(node, ast.Import):
                imported_names = tuple(alias.name for alias in node.names)
            else:
                continue
            violations.extend(
                f"{module_path.name}:{node.lineno}:{imported_name}"
                for imported_name in imported_names
                if imported_name.startswith(FORBIDDEN_IMPORT_ROOTS)
            )

    assert violations == []
