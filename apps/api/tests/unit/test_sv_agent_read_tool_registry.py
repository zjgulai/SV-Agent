from collections.abc import Mapping
from typing import Any
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.application.sv_agent.read_tools.contracts import (
    ProductTruthReadOutput,
    ReadResult,
    ReadResultState,
    ReadToolInput,
    ReadToolName,
    ReadToolOutput,
    ScriptExportProjection,
    ScriptReadOutput,
    ScriptReadValue,
    StoryboardApprovalStateProjection,
    StoryboardReadOutput,
    StoryboardReadValue,
)
from app.application.sv_agent.read_tools.registry import (
    ReadToolNotRegistered,
    ReadToolRuntime,
    ReadToolUnavailable,
    StaticReadToolRegistry,
)

PRODUCT_ID = UUID("32000000-0000-0000-0000-000000000001")


class StubRuntime(ReadToolRuntime):
    def __init__(self, supported: set[ReadToolName]) -> None:
        self.supported = supported

    def supports(self, name: ReadToolName) -> bool:
        return name in self.supported

    async def execute(self, command: ReadToolInput) -> ReadToolOutput:
        assert command.tool is ReadToolName.PRODUCT_TRUTH
        return ProductTruthReadOutput.not_found(
            product_id=command.product_id,
            code="PRODUCT_NOT_FOUND",
        )


def _product_payload(**extra: Any) -> Mapping[str, object]:
    return {
        "tool": ReadToolName.PRODUCT_TRUTH.value,
        "product_id": str(PRODUCT_ID),
        **extra,
    }


def test_registry_is_closed_versioned_and_read_only() -> None:
    registry = StaticReadToolRegistry(StubRuntime(set(ReadToolName)))

    descriptions = registry.list_tools()

    assert tuple(item.name for item in descriptions) == tuple(ReadToolName)
    assert len(descriptions) == 6
    assert {item.version for item in descriptions} == {"1.0.0"}
    assert {item.effect_class for item in descriptions} == {"read"}
    assert all(item.available for item in descriptions)
    assert all(item.input_schema["type"] == "object" for item in descriptions)
    assert all(item.output_schema["type"] == "object" for item in descriptions)


def test_registry_rejects_dynamic_names_and_extra_input_fields() -> None:
    registry = StaticReadToolRegistry(StubRuntime(set(ReadToolName)))

    with pytest.raises(ReadToolNotRegistered, match="not registered"):
        registry.validate_input("remote.plugin.execute", {"tool": "remote.plugin.execute"})
    with pytest.raises(ValidationError, match="extra_forbidden"):
        registry.validate_input(ReadToolName.PRODUCT_TRUTH, _product_payload(debug=True))
    with pytest.raises(ValidationError, match="Field required"):
        registry.validate_input(
            ReadToolName.PATTERN_CONTRACT,
            {
                "tool": "pattern_contract.inspect",
                "pattern_key": "problem_solution",
                "duration_seconds": 30,
                "language": "en",
            },
        )

    with pytest.raises(ValidationError, match="less_than_equal"):
        registry.validate_input(
            ReadToolName.JOB,
            {
                "tool": "job.inspect",
                "job_id": str(PRODUCT_ID),
                "event_limit": 201,
            },
        )


def test_negative_evidence_requires_the_queried_subject() -> None:
    with pytest.raises(ValidationError, match="not_found_result_shape_invalid"):
        ReadResult[object](
            state=ReadResultState.NOT_FOUND,
            value=None,
            negative_evidence_code="PRODUCT_NOT_FOUND",
        )


async def test_negative_evidence_is_a_typed_completed_result() -> None:
    registry = StaticReadToolRegistry(StubRuntime({ReadToolName.PRODUCT_TRUTH}))
    command = registry.validate_input(ReadToolName.PRODUCT_TRUTH, _product_payload())

    output = await registry.invoke(command)

    assert isinstance(output, ProductTruthReadOutput)
    assert output.result.state is ReadResultState.NOT_FOUND
    assert output.result.negative_evidence_code == "PRODUCT_NOT_FOUND"
    assert output.result.subject_ref == str(PRODUCT_ID)


async def test_unavailable_adapter_is_not_negative_evidence() -> None:
    registry = StaticReadToolRegistry(StubRuntime(set()))
    command = registry.validate_input(ReadToolName.PRODUCT_TRUTH, _product_payload())

    assert registry.describe(ReadToolName.PRODUCT_TRUTH).available is False
    with pytest.raises(ReadToolUnavailable, match="unavailable"):
        await registry.invoke(command)


def test_action_discriminators_reject_mismatched_output_shapes() -> None:
    with pytest.raises(ValidationError, match="script_action_result_mismatch"):
        ScriptReadOutput(
            action="inspect",
            result=ReadResult[ScriptReadValue].found(
                ScriptExportProjection(
                    script_id=PRODUCT_ID,
                    version_id=UUID(int=2),
                    format="json",
                    media_type="application/json",
                    content="{}\n",
                )
            ),
        )
    with pytest.raises(ValidationError, match="storyboard_action_result_mismatch"):
        StoryboardReadOutput(
            action="preview",
            result=ReadResult[StoryboardReadValue].found(
                StoryboardApprovalStateProjection(
                    storyboard_id=PRODUCT_ID,
                    status="unreviewed",
                    latest_event=None,
                )
            ),
        )
