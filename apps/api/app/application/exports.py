import json
from typing import Any

from app.adapters.db.models import ScriptGenerationRecord, ScriptVersionRecord


def export_payload(
    generation: ScriptGenerationRecord, version: ScriptVersionRecord
) -> dict[str, Any]:
    return {
        "metadata": {
            "script_id": str(generation.id),
            "version_id": str(version.id),
            "snapshot_id": str(generation.snapshot_id),
            "pattern": f"{generation.pattern_key}@{generation.pattern_version}",
            "provider": generation.provider,
            "model": generation.model,
            "prompt_contract_version": generation.prompt_contract_version,
            "input_digest": generation.input_digest,
        },
        "validation_report": version.validation_report,
        "draft": version.draft,
    }


def export_markdown(generation: ScriptGenerationRecord, version: ScriptVersionRecord) -> str:
    payload = export_payload(generation, version)
    metadata = payload["metadata"]
    report = version.validation_report
    draft = version.draft
    lines = [
        "# Script export",
        "",
        "## Metadata",
        "",
        *[f"- {key}: `{value}`" for key, value in metadata.items()],
        "",
        "## Validation summary",
        "",
        f"- acceptable: `{str(bool(report.get('acceptable', False))).lower()}`",
        f"- blocking findings: `{len(report.get('blocking', []))}`",
        "",
        "## Phases",
        "",
    ]
    for phase in draft.get("phases", []):
        lines.append(
            f"- {phase['start_seconds']}–{phase['end_seconds']}s · "
            f"**{phase['key']}** · {phase['purpose']}"
        )
    lines.extend(["", "## Shots", ""])
    for index, shot in enumerate(draft.get("shots", []), start=1):
        lines.extend(
            [
                f"### Shot {index} · {shot['start_seconds']}–{shot['end_seconds']}s",
                "",
                f"- Voiceover: {shot['voiceover']}",
                f"- Visual: {shot['visual']}",
                f"- Action: {shot['action']}",
                f"- Caption: {shot['caption']}",
                f"- Acceptance: {shot['acceptance_shot']}",
                "",
            ]
        )
    for heading, key in (
        ("Titles", "titles"),
        ("Tags", "tags"),
        ("Shooting list", "shooting_list"),
    ):
        lines.extend([f"## {heading}", ""])
        lines.extend(f"- {item}" for item in draft.get(key, []))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def export_json(generation: ScriptGenerationRecord, version: ScriptVersionRecord) -> str:
    return json.dumps(export_payload(generation, version), ensure_ascii=False, indent=2) + "\n"
