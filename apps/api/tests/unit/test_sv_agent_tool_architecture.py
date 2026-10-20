import ast
from pathlib import Path


def test_tool_registry_and_handlers_do_not_import_persistence_or_workers() -> None:
    application_root = Path(__file__).parents[2] / "app" / "application"
    targets = (
        application_root / "sv_agent_tool_registry.py",
        application_root / "sv_agent_tool_handler.py",
        application_root / "sv_agent_orchestration.py",
    )
    forbidden = (
        "app.adapters",
        "app.worker",
        "celery",
    )
    violations: list[str] = []

    for target in targets:
        tree = ast.parse(target.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module.startswith(forbidden):
                    violations.append(f"{target.name}:{node.lineno}:{module}")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith(forbidden):
                        violations.append(f"{target.name}:{node.lineno}:{alias.name}")

    assert violations == []
