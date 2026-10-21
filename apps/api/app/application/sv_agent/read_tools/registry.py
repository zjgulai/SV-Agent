from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol, cast

from pydantic import TypeAdapter

from .contracts import (
    CreativeComparisonReadInput,
    CreativeComparisonReadOutput,
    JobReadInput,
    JobReadOutput,
    PatternContractReadInput,
    PatternContractReadOutput,
    ProductTruthReadInput,
    ProductTruthReadOutput,
    ReadToolInput,
    ReadToolName,
    ReadToolOutput,
    ScriptReadInput,
    ScriptReadOutput,
    StoryboardReadInput,
    StoryboardReadOutput,
    StrictToolModel,
)


class ReadToolNotRegistered(Exception):
    code = "TOOL_NOT_REGISTERED"


class ReadToolUnavailable(Exception):
    code = "TOOL_UNAVAILABLE"


class ReadToolContractViolation(Exception):
    code = "TOOL_CONTRACT_INVALID"


class ReadToolRuntime(Protocol):
    def supports(self, name: ReadToolName) -> bool: ...

    async def execute(self, command: ReadToolInput) -> ReadToolOutput: ...


@dataclass(frozen=True, slots=True)
class ReadToolDescription:
    name: ReadToolName
    version: str
    effect_class: str
    intent_summary: str
    available: bool
    input_schema: Mapping[str, object]
    output_schema: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class _ReadToolContract:
    name: ReadToolName
    version: str
    intent_summary: str
    input_model: type[StrictToolModel]
    output_model: type[StrictToolModel]


_CONTRACTS = (
    _ReadToolContract(
        name=ReadToolName.PRODUCT_TRUTH,
        version="1.0.0",
        intent_summary="Inspect authoritative Product Snapshot and Product Facts without mutation.",
        input_model=ProductTruthReadInput,
        output_model=ProductTruthReadOutput,
    ),
    _ReadToolContract(
        name=ReadToolName.PATTERN_CONTRACT,
        version="1.0.0",
        intent_summary="Inspect one compiled, versioned creative pattern contract.",
        input_model=PatternContractReadInput,
        output_model=PatternContractReadOutput,
    ),
    _ReadToolContract(
        name=ReadToolName.JOB,
        version="1.0.0",
        intent_summary="Inspect Job state and its factual execution history without retrying it.",
        input_model=JobReadInput,
        output_model=JobReadOutput,
    ),
    _ReadToolContract(
        name=ReadToolName.SCRIPT,
        version="1.0.0",
        intent_summary="Inspect immutable Script versions, diffs, or exports without creating a version.",
        input_model=ScriptReadInput,
        output_model=ScriptReadOutput,
    ),
    _ReadToolContract(
        name=ReadToolName.STORYBOARD,
        version="1.0.0",
        intent_summary="Inspect Storyboard preflight, preview, or approval state without deciding it.",
        input_model=StoryboardReadInput,
        output_model=StoryboardReadOutput,
    ),
    _ReadToolContract(
        name=ReadToolName.CREATIVE_COMPARISON,
        version="1.0.0",
        intent_summary="Inspect a read-only Control and Variant creative comparison projection.",
        input_model=CreativeComparisonReadInput,
        output_model=CreativeComparisonReadOutput,
    ),
)


class StaticReadToolRegistry:
    """Closed, versioned registry for the six SV-Agent read capabilities."""

    def __init__(self, runtime: ReadToolRuntime | None) -> None:
        self._runtime = runtime
        self._contracts = {item.name: item for item in _CONTRACTS}

    def list_tools(self) -> tuple[ReadToolDescription, ...]:
        return tuple(self.describe(name) for name in ReadToolName)

    def describe(self, name: ReadToolName | str) -> ReadToolDescription:
        contract = self._contract(name)
        return ReadToolDescription(
            name=contract.name,
            version=contract.version,
            effect_class="read",
            intent_summary=contract.intent_summary,
            available=self._is_available(contract.name),
            input_schema=TypeAdapter(contract.input_model).json_schema(),
            output_schema=TypeAdapter(contract.output_model).json_schema(),
        )

    def validate_input(
        self,
        name: ReadToolName | str,
        payload: Mapping[str, object],
    ) -> ReadToolInput:
        contract = self._contract(name)
        validated = TypeAdapter(contract.input_model).validate_python(payload)
        return cast(ReadToolInput, validated)

    async def invoke(self, command: ReadToolInput) -> ReadToolOutput:
        name = command.tool
        contract = self._contract(name)
        if not self._is_available(name) or self._runtime is None:
            raise ReadToolUnavailable(f"registered read tool is unavailable: {name.value}")
        output = await self._runtime.execute(command)
        try:
            validated = TypeAdapter(contract.output_model).validate_python(output)
        except Exception as exc:
            raise ReadToolContractViolation(
                f"read tool returned an invalid contract: {name.value}"
            ) from exc
        return cast(ReadToolOutput, validated)

    def _is_available(self, name: ReadToolName) -> bool:
        return self._runtime is not None and self._runtime.supports(name)

    def _contract(self, name: ReadToolName | str) -> _ReadToolContract:
        try:
            normalized = name if isinstance(name, ReadToolName) else ReadToolName(name)
            return self._contracts[normalized]
        except (KeyError, ValueError) as exc:
            raise ReadToolNotRegistered(f"read tool is not registered: {name}") from exc
