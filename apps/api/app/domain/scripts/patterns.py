from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal, cast

from pydantic import BaseModel, ConfigDict, Field

from app.domain.scripts.audience import AudienceProfileKey, audience_context

PATTERN_CONTRACT_VERSION = "p1.3c"
_COMPILED_PATTERN_CONTRACT_VERSIONS = frozenset(
    {"p1.3a", "p1.3b", PATTERN_CONTRACT_VERSION}
)
PatternLanguage = Literal["en", "zh-CN"]
SUPPORTED_PATTERN_LANGUAGES = ("en", "zh-CN")
_SUPPORTED_LANGUAGES = frozenset(SUPPORTED_PATTERN_LANGUAGES)
_FACT_BOUND_FIELDS = (
    "voiceover",
    "caption",
    "product_claims",
    "supported_fact_ids",
)
_SERVER_OWNED_FIELDS = (
    "phase.purpose",
    "visual",
    "action",
    "acceptance_shot",
    "titles",
    "tags",
    "shooting_list",
)
_ACCEPTANCE_CHECKS = (
    "phase_order",
    "shot_plan",
    "timeline_budget",
    "speaking_rate",
    "fact_binding",
    "excluded_deny_set",
    "server_owned_copy",
)


class ServerOwnedCopyDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    visual: str
    action: str
    acceptance_shot: str
    title: str
    tag_suffix: str
    shooting_list: tuple[str, ...]


DEFAULT_SERVER_OWNED_COPY = ServerOwnedCopyDefinition(
    visual="Show the product clearly.",
    action="Demonstrate the referenced product fact.",
    acceptance_shot="The product and action are clearly visible.",
    title="Fact-led product script",
    tag_suffix="product-demo",
    shooting_list=("product", "clean background", "close-up detail"),
)


class PatternCompileError(ValueError):
    pass


class PatternPhaseDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    key: str
    purpose: str
    shot_role: str
    fact_role: Literal["required_selected"] = "required_selected"


class PatternShotDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    phase_key: str
    role: str
    fact_role: Literal["required_selected"] = "required_selected"
    budget_weight: int = Field(ge=1)


class SpeakingRateDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    unit: Literal["words_per_second", "han_characters_per_second"]
    max: float = Field(gt=0)


class FieldPolicyDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    fact_bound: tuple[str, ...]
    server_owned: tuple[str, ...]


class CtaPolicyDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    mode: Literal["server_generic_no_offer", "server_promotion_final_cta"]


class AudiencePolicyDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    mode: Literal["record_only", "server_owned_profile"] = "record_only"
    allowed_slots: tuple[str, ...] = ()
    profile_key: AudienceProfileKey | None = None


class CompiledPatternDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_version: str
    key: str
    version: str
    name: str
    hook_type: str
    duration_seconds: int = Field(gt=0)
    language: PatternLanguage
    phases: tuple[PatternPhaseDefinition, ...] = Field(min_length=1)
    shots: tuple[PatternShotDefinition, ...] = Field(min_length=1)
    speaking_rate: SpeakingRateDefinition
    field_policy: FieldPolicyDefinition
    server_owned_copy: ServerOwnedCopyDefinition
    cta_policy: CtaPolicyDefinition
    audience_policy: AudiencePolicyDefinition
    acceptance_checks: tuple[str, ...]

    @property
    def phase_sequence(self) -> tuple[str, ...]:
        return tuple(phase.key for phase in self.phases)

    @property
    def is_compiled_contract(self) -> bool:
        return self.contract_version in _COMPILED_PATTERN_CONTRACT_VERSIONS

    @property
    def shot_roles(self) -> tuple[str, ...]:
        return tuple(shot.role for shot in self.shots)


@dataclass(frozen=True, slots=True)
class DurationShotPlan:
    phase_key: str
    role: str
    budget_weight: int


@dataclass(frozen=True, slots=True)
class DurationPatternPlan:
    duration_seconds: int
    phase_sequence: tuple[str, ...]
    shots: tuple[DurationShotPlan, ...]

    @property
    def shot_roles(self) -> tuple[str, ...]:
        return tuple(shot.role for shot in self.shots)


@dataclass(frozen=True, slots=True)
class CreativePattern:
    key: str
    version: str
    name: str
    hook_type: str
    duration_plans: tuple[DurationPatternPlan, ...]

    @property
    def supported_durations(self) -> tuple[int, ...]:
        return tuple(plan.duration_seconds for plan in self.duration_plans)

    @property
    def phase_sequence(self) -> tuple[str, ...]:
        """Canonical 30-second shape for legacy-safe registry readers."""
        return self.plan_for(30).phase_sequence

    @property
    def shot_roles(self) -> tuple[str, ...]:
        return self.plan_for(30).shot_roles

    @property
    def all_phase_keys(self) -> frozenset[str]:
        return frozenset(
            phase_key
            for plan in self.duration_plans
            for phase_key in plan.phase_sequence
        )

    def plan_for(self, duration_seconds: int) -> DurationPatternPlan:
        plan = next(
            (
                item
                for item in self.duration_plans
                if item.duration_seconds == duration_seconds
            ),
            None,
        )
        if plan is None:
            raise PatternCompileError(f"duration is not supported: {duration_seconds}")
        return plan

    def compile(
        self,
        *,
        duration_seconds: int,
        language: str,
        audience_profile_key: AudienceProfileKey = "general",
    ) -> CompiledPatternDefinition:
        if language not in _SUPPORTED_LANGUAGES:
            raise PatternCompileError(f"language is not supported: {language}")
        plan = self.plan_for(duration_seconds)
        _validate_plan(plan)
        audience = audience_context(audience_profile_key)
        primary_roles = {
            phase_key: next(
                shot.role for shot in plan.shots if shot.phase_key == phase_key
            )
            for phase_key in plan.phase_sequence
        }
        return CompiledPatternDefinition(
            contract_version=PATTERN_CONTRACT_VERSION,
            key=self.key,
            version=self.version,
            name=self.name,
            hook_type=self.hook_type,
            duration_seconds=duration_seconds,
            language=cast(PatternLanguage, language),
            phases=tuple(
                PatternPhaseDefinition(
                    key=phase_key,
                    purpose=safe_phase_purpose(phase_key),
                    shot_role=primary_roles[phase_key],
                )
                for phase_key in plan.phase_sequence
            ),
            shots=tuple(
                PatternShotDefinition(
                    phase_key=shot.phase_key,
                    role=shot.role,
                    budget_weight=shot.budget_weight,
                )
                for shot in plan.shots
            ),
            speaking_rate=SpeakingRateDefinition(
                unit=(
                    "han_characters_per_second"
                    if language == "zh-CN"
                    else "words_per_second"
                ),
                max=4.0 if language == "zh-CN" else 2.5,
            ),
            field_policy=FieldPolicyDefinition(
                fact_bound=_FACT_BOUND_FIELDS,
                server_owned=_SERVER_OWNED_FIELDS,
            ),
            server_owned_copy=ServerOwnedCopyDefinition(
                visual=f"Show the product clearly in {audience.scene_context}.",
                action=f"Demonstrate the referenced product fact beside {audience.generic_prop}.",
                acceptance_shot=(
                    "The product and action are clearly visible during "
                    f"{audience.routine_moment}."
                ),
                title=f"Fact-led product script · {audience.label}",
                tag_suffix=f"product-demo-{audience.profile_key}",
                shooting_list=("product", audience.scene_context, audience.generic_prop),
            ),
            cta_policy=CtaPolicyDefinition(
                mode=(
                    "server_promotion_final_cta"
                    if self.key == "offer_cta"
                    else "server_generic_no_offer"
                )
            ),
            audience_policy=AudiencePolicyDefinition(
                mode="server_owned_profile",
                allowed_slots=(
                    "visual", "action", "acceptance_shot", "titles", "tags", "shooting_list"
                ),
                profile_key=audience.profile_key,
            ),
            acceptance_checks=_ACCEPTANCE_CHECKS,
        )


def _plan(
    duration_seconds: int,
    phase_sequence: tuple[str, ...],
    shots: tuple[tuple[str, str], ...],
    weights: tuple[int, ...],
) -> DurationPatternPlan:
    return DurationPatternPlan(
        duration_seconds=duration_seconds,
        phase_sequence=phase_sequence,
        shots=tuple(
            DurationShotPlan(
                phase_key=phase_key,
                role=role,
                budget_weight=weights[index],
            )
            for index, (phase_key, role) in enumerate(shots)
        ),
    )


_SHORT_WEIGHTS = (2, 4, 5, 4)
_MEDIUM_WEIGHTS = (3, 5, 5, 6, 6, 5)
_LONG_WEIGHTS = (4, 5, 6, 7, 7, 6, 5, 5)


CREATIVE_PATTERNS: tuple[CreativePattern, ...] = (
    CreativePattern(
        "problem_solution",
        "1.3",
        "Problem / Solution",
        "pain",
        (
            _plan(
                15,
                ("hook", "solution", "cta"),
                (("hook", "problem"), ("solution", "demo"), ("solution", "result"), ("cta", "cta")),
                _SHORT_WEIGHTS,
            ),
            _plan(
                30,
                ("hook", "problem", "solution", "cta"),
                (("hook", "problem"), ("problem", "problem"), ("problem", "demo"), ("solution", "demo"), ("solution", "result"), ("cta", "cta")),
                _MEDIUM_WEIGHTS,
            ),
            _plan(
                45,
                ("hook", "problem", "solution", "proof", "cta"),
                (("hook", "problem"), ("problem", "problem"), ("problem", "demo"), ("solution", "demo"), ("solution", "result"), ("proof", "proof"), ("proof", "detail"), ("cta", "cta")),
                _LONG_WEIGHTS,
            ),
        ),
    ),
    CreativePattern(
        "demo_first",
        "1.3",
        "Demo First",
        "result",
        (
            _plan(15, ("hook", "demo", "cta"), (("hook", "result"), ("demo", "steps"), ("demo", "detail"), ("cta", "cta")), _SHORT_WEIGHTS),
            _plan(30, ("hook", "demo", "proof", "cta"), (("hook", "result"), ("demo", "steps"), ("demo", "steps"), ("proof", "detail"), ("proof", "detail"), ("cta", "cta")), _MEDIUM_WEIGHTS),
            _plan(45, ("hook", "demo", "proof", "comparison", "cta"), (("hook", "result"), ("demo", "steps"), ("demo", "steps"), ("proof", "detail"), ("proof", "detail"), ("comparison", "proof"), ("comparison", "detail"), ("cta", "cta")), _LONG_WEIGHTS),
        ),
    ),
    CreativePattern(
        "before_after",
        "1.3",
        "Before / After",
        "contrast",
        (
            _plan(15, ("hook", "contrast", "cta"), (("hook", "before"), ("contrast", "transition"), ("contrast", "after"), ("cta", "cta")), _SHORT_WEIGHTS),
            _plan(30, ("hook", "before", "after", "cta"), (("hook", "before"), ("before", "before"), ("before", "transition"), ("after", "transition"), ("after", "after"), ("cta", "cta")), _MEDIUM_WEIGHTS),
            _plan(45, ("hook", "before", "after", "proof", "cta"), (("hook", "before"), ("before", "before"), ("before", "transition"), ("after", "transition"), ("after", "after"), ("proof", "proof"), ("proof", "detail"), ("cta", "cta")), _LONG_WEIGHTS),
        ),
    ),
    CreativePattern(
        "listicle",
        "1.3",
        "Listicle",
        "number",
        (
            _plan(15, ("hook", "items", "cta"), (("hook", "hook"), ("items", "item"), ("items", "item"), ("cta", "cta")), _SHORT_WEIGHTS),
            _plan(30, ("hook", "items", "recap", "cta"), (("hook", "hook"), ("items", "item"), ("items", "item"), ("items", "item"), ("recap", "item"), ("cta", "cta")), _MEDIUM_WEIGHTS),
            _plan(45, ("hook", "items", "proof", "recap", "cta"), (("hook", "hook"), ("items", "item"), ("items", "item"), ("items", "item"), ("proof", "detail"), ("proof", "detail"), ("recap", "item"), ("cta", "cta")), _LONG_WEIGHTS),
        ),
    ),
    CreativePattern(
        "testimonial",
        "1.3",
        "Testimonial",
        "experience",
        (
            _plan(15, ("hook", "experience", "cta"), (("hook", "person"), ("experience", "product"), ("experience", "usage"), ("cta", "cta")), _SHORT_WEIGHTS),
            _plan(30, ("hook", "context", "experience", "cta"), (("hook", "person"), ("context", "product"), ("context", "product"), ("experience", "usage"), ("experience", "usage"), ("cta", "cta")), _MEDIUM_WEIGHTS),
            _plan(45, ("hook", "context", "experience", "proof", "cta"), (("hook", "person"), ("context", "product"), ("context", "product"), ("experience", "usage"), ("experience", "usage"), ("proof", "proof"), ("proof", "detail"), ("cta", "cta")), _LONG_WEIGHTS),
        ),
    ),
    CreativePattern(
        "myth_busting",
        "1.3",
        "Myth Busting",
        "myth",
        (
            _plan(15, ("hook", "fact", "cta"), (("hook", "claim"), ("fact", "evidence"), ("fact", "demo"), ("cta", "cta")), _SHORT_WEIGHTS),
            _plan(30, ("hook", "myth", "fact", "cta"), (("hook", "claim"), ("myth", "evidence"), ("myth", "evidence"), ("fact", "demo"), ("fact", "demo"), ("cta", "cta")), _MEDIUM_WEIGHTS),
            _plan(45, ("hook", "myth", "fact", "proof", "cta"), (("hook", "claim"), ("myth", "evidence"), ("myth", "evidence"), ("fact", "demo"), ("fact", "demo"), ("proof", "proof"), ("proof", "detail"), ("cta", "cta")), _LONG_WEIGHTS),
        ),
    ),
    CreativePattern(
        "offer_cta",
        "1.3",
        "Offer / CTA",
        "offer",
        (
            _plan(15, ("hook", "benefits", "cta"), (("hook", "product"), ("benefits", "benefit"), ("benefits", "benefit"), ("cta", "cta")), _SHORT_WEIGHTS),
            _plan(30, ("hook", "benefits", "offer", "cta"), (("hook", "product"), ("benefits", "benefit"), ("benefits", "benefit"), ("offer", "offer"), ("offer", "offer"), ("cta", "cta")), _MEDIUM_WEIGHTS),
            _plan(45, ("hook", "benefits", "offer", "proof", "cta"), (("hook", "product"), ("benefits", "benefit"), ("benefits", "benefit"), ("offer", "offer"), ("offer", "offer"), ("proof", "proof"), ("proof", "detail"), ("cta", "cta")), _LONG_WEIGHTS),
        ),
    ),
)


def _validate_plan(plan: DurationPatternPlan) -> None:
    if not plan.phase_sequence or not plan.shots:
        raise PatternCompileError("pattern plan must include phases and shots")
    if len(set(plan.phase_sequence)) != len(plan.phase_sequence):
        raise PatternCompileError("pattern phase keys must be unique")
    if sum(shot.budget_weight for shot in plan.shots) != plan.duration_seconds:
        raise PatternCompileError("pattern shot weights must sum to the target duration")
    phase_indexes = {phase_key: index for index, phase_key in enumerate(plan.phase_sequence)}
    shot_indexes = []
    for shot in plan.shots:
        if shot.phase_key not in phase_indexes:
            raise PatternCompileError("pattern shot references an unknown phase")
        shot_indexes.append(phase_indexes[shot.phase_key])
    if shot_indexes != sorted(shot_indexes):
        raise PatternCompileError("pattern shots must follow phase order")
    if set(shot_indexes) != set(range(len(plan.phase_sequence))):
        raise PatternCompileError("every pattern phase must own at least one shot")


def safe_phase_purpose(phase_key: str) -> str:
    return phase_key.replace("_", " ").title()


def compile_pattern(
    key: str,
    *,
    duration_seconds: int,
    language: str,
    audience_profile_key: AudienceProfileKey = "general",
) -> CompiledPatternDefinition:
    pattern = next((item for item in CREATIVE_PATTERNS if item.key == key), None)
    if pattern is None:
        raise PatternCompileError(f"pattern is not supported: {key}")
    return pattern.compile(
        duration_seconds=duration_seconds,
        language=language,
        audience_profile_key=audience_profile_key,
    )


def load_persisted_pattern_definition(
    value: Mapping[str, object],
    *,
    pattern_key: str,
    pattern_version: str,
    duration_seconds: int,
    language: str,
) -> CompiledPatternDefinition:
    if value.get("contract_version") in _COMPILED_PATTERN_CONTRACT_VERSIONS:
        compiled = CompiledPatternDefinition.model_validate(value)
        if (
            compiled.key != pattern_key
            or compiled.version != pattern_version
            or compiled.duration_seconds != duration_seconds
            or compiled.language != language
        ):
            raise PatternCompileError("persisted pattern identity does not match generation")
        expected_unit = "han_characters_per_second" if language == "zh-CN" else "words_per_second"
        if compiled.speaking_rate.unit != expected_unit:
            raise PatternCompileError("persisted pattern speaking rate does not match language")
        return compiled

    try:
        hook_type = str(value["hook_type"])
        raw_phase_sequence = value["phase_sequence"]
        raw_shot_roles = value["shot_roles"]
    except KeyError as exc:
        raise PatternCompileError("persisted legacy pattern is unavailable") from exc
    if (
        not isinstance(raw_phase_sequence, Sequence)
        or isinstance(raw_phase_sequence, str)
        or not isinstance(raw_shot_roles, Sequence)
        or isinstance(raw_shot_roles, str)
    ):
        raise PatternCompileError("persisted legacy pattern is unavailable")
    phase_sequence = tuple(str(item) for item in raw_phase_sequence)
    shot_roles = tuple(str(item) for item in raw_shot_roles)
    if not phase_sequence or len(phase_sequence) != len(shot_roles):
        raise PatternCompileError("persisted legacy pattern plan is invalid")
    return CompiledPatternDefinition(
        contract_version=f"legacy-v{pattern_version}",
        key=pattern_key,
        version=pattern_version,
        name=pattern_key,
        hook_type=hook_type,
        duration_seconds=duration_seconds,
        language=cast(PatternLanguage, language),
        phases=tuple(
            PatternPhaseDefinition(
                key=phase_key,
                purpose=safe_phase_purpose(phase_key),
                shot_role=shot_roles[index],
            )
            for index, phase_key in enumerate(phase_sequence)
        ),
        shots=tuple(
            PatternShotDefinition(phase_key=phase_key, role=shot_roles[index], budget_weight=1)
            for index, phase_key in enumerate(phase_sequence)
        ),
        speaking_rate=SpeakingRateDefinition(
            unit=(
                "han_characters_per_second"
                if language == "zh-CN"
                else "words_per_second"
            ),
            max=4.0 if language == "zh-CN" else 2.5,
        ),
        field_policy=FieldPolicyDefinition(
            fact_bound=_FACT_BOUND_FIELDS,
            server_owned=_SERVER_OWNED_FIELDS,
        ),
        server_owned_copy=DEFAULT_SERVER_OWNED_COPY,
        cta_policy=CtaPolicyDefinition(mode="server_generic_no_offer"),
        audience_policy=AudiencePolicyDefinition(mode="record_only"),
        acceptance_checks=_ACCEPTANCE_CHECKS,
    )
