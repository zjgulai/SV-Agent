from typing import Literal, cast

from pydantic import BaseModel, ConfigDict

AudienceProfileKey = Literal[
    "general",
    "study_routine",
    "work_routine",
    "home_routine",
    "on_the_go",
]


class AudienceCreativeContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    profile_key: AudienceProfileKey
    label: str
    scene_context: str
    generic_prop: str
    routine_moment: str
    neutral_tone: str


_CONTEXTS: dict[AudienceProfileKey, AudienceCreativeContext] = {
    "general": AudienceCreativeContext(
        profile_key="general",
        label="General routine",
        scene_context="a clean everyday setting",
        generic_prop="a neutral surface",
        routine_moment="an everyday moment",
        neutral_tone="clear",
    ),
    "study_routine": AudienceCreativeContext(
        profile_key="study_routine",
        label="Study routine",
        scene_context="a quiet study setting",
        generic_prop="a notebook",
        routine_moment="a study break",
        neutral_tone="calm",
    ),
    "work_routine": AudienceCreativeContext(
        profile_key="work_routine",
        label="Work routine",
        scene_context="a tidy workspace",
        generic_prop="a desk organizer",
        routine_moment="a work break",
        neutral_tone="practical",
    ),
    "home_routine": AudienceCreativeContext(
        profile_key="home_routine",
        label="Home routine",
        scene_context="a bright home setting",
        generic_prop="a clean countertop",
        routine_moment="a home routine",
        neutral_tone="warm",
    ),
    "on_the_go": AudienceCreativeContext(
        profile_key="on_the_go",
        label="On-the-go routine",
        scene_context="a simple travel-ready setting",
        generic_prop="a plain tote bag",
        routine_moment="a transition between activities",
        neutral_tone="direct",
    ),
}


def audience_context(profile_key: str) -> AudienceCreativeContext:
    try:
        return _CONTEXTS[cast(AudienceProfileKey, profile_key)]
    except KeyError as exc:
        raise ValueError(f"unsupported audience profile: {profile_key}") from exc


def audience_profiles() -> tuple[AudienceCreativeContext, ...]:
    return tuple(_CONTEXTS.values())
