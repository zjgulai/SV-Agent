from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CreativePattern:
    key: str
    version: str
    name: str
    hook_type: str
    phase_sequence: tuple[str, ...]
    shot_roles: tuple[str, ...]
    supported_durations: tuple[int, ...] = (15, 30, 45)


CREATIVE_PATTERNS: tuple[CreativePattern, ...] = (
    CreativePattern("problem_solution", "1.0", "Problem / Solution", "pain", ("hook", "problem", "solution", "cta"), ("problem", "demo", "result", "cta")),
    CreativePattern("demo_first", "1.0", "Demo First", "result", ("hook", "demo", "proof", "cta"), ("result", "steps", "detail", "cta")),
    CreativePattern("before_after", "1.0", "Before / After", "contrast", ("hook", "before", "after", "cta"), ("before", "transition", "after", "cta")),
    CreativePattern("listicle", "1.0", "Listicle", "number", ("hook", "items", "recap", "cta"), ("hook", "item", "item", "cta")),
    CreativePattern("testimonial", "1.0", "Testimonial", "experience", ("hook", "context", "experience", "cta"), ("person", "product", "usage", "cta")),
    CreativePattern("myth_busting", "1.0", "Myth Busting", "myth", ("hook", "myth", "fact", "cta"), ("claim", "evidence", "demo", "cta")),
    CreativePattern("offer_cta", "1.0", "Offer / CTA", "offer", ("hook", "benefits", "offer", "cta"), ("product", "benefit", "offer", "cta")),
)
