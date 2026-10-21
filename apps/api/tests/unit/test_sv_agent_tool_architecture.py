import ast
from pathlib import Path

_APPLICATION_ROOT = Path(__file__).parents[2] / "app" / "application"
_SV_AGENT_ROOT = _APPLICATION_ROOT / "sv_agent"
_TARGET_MODULES = (
    _SV_AGENT_ROOT / "orchestration.py",
    _SV_AGENT_ROOT / "task_inbox.py",
    _SV_AGENT_ROOT / "mission_control.py",
    _SV_AGENT_ROOT / "evidence_workspace.py",
    _SV_AGENT_ROOT / "read_tools" / "contracts.py",
    _SV_AGENT_ROOT / "read_tools" / "errors.py",
    _SV_AGENT_ROOT / "read_tools" / "execution.py",
    _SV_AGENT_ROOT / "read_tools" / "handler.py",
    _SV_AGENT_ROOT / "read_tools" / "registry.py",
)
_LEGACY_MODULES = (
    _APPLICATION_ROOT / "sv_agent_orchestration.py",
    _APPLICATION_ROOT / "sv_agent_task_inbox.py",
    _APPLICATION_ROOT / "sv_agent_mission_control.py",
    _APPLICATION_ROOT / "sv_agent_evidence_workspace.py",
    _APPLICATION_ROOT / "sv_agent_tool_contracts.py",
    _APPLICATION_ROOT / "sv_agent_tool_errors.py",
    _APPLICATION_ROOT / "sv_agent_read_tool_execution.py",
    _APPLICATION_ROOT / "sv_agent_tool_handler.py",
    _APPLICATION_ROOT / "sv_agent_tool_registry.py",
)


def test_sv_agent_application_modules_are_localized_without_legacy_facades() -> None:
    package_initializers = (
        _SV_AGENT_ROOT / "__init__.py",
        _SV_AGENT_ROOT / "read_tools" / "__init__.py",
    )

    assert all(path.is_file() for path in (*package_initializers, *_TARGET_MODULES))
    assert all(not path.exists() for path in _LEGACY_MODULES)


def test_sv_agent_package_initializers_do_not_import_implementation() -> None:
    package_initializers = (
        _SV_AGENT_ROOT / "__init__.py",
        _SV_AGENT_ROOT / "read_tools" / "__init__.py",
    )

    violations: list[str] = []
    for initializer in package_initializers:
        tree = ast.parse(initializer.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                violations.append(f"{initializer}:{node.lineno}")

    assert violations == []


def test_tool_registry_and_handlers_do_not_import_persistence_or_workers() -> None:
    targets = (
        _SV_AGENT_ROOT / "read_tools" / "registry.py",
        _SV_AGENT_ROOT / "read_tools" / "handler.py",
        _SV_AGENT_ROOT / "orchestration.py",
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
