"""Domain plugins make faithbench universal, not math-only.

A Domain bundles everything domain-specific behind one interface:
  - failure_classes : the taxonomy of "valid but unfaithful" failure modes
  - structural(artifact, context) -> [Verdict]
        deterministic checks that need only the artifact (+ item context, e.g.
        a tool schema). This is the "cheap gate" / reference-free linter slice.
  - reference_diff(candidate, gold, context) -> [Verdict]
        deterministic structural diff vs a known-faithful gold artifact.

Everything else (item model, scorer, CLI) is domain-agnostic. Adding a domain =
implement these and `register()`. The deterministic *reach* varies by domain:
where the cheap gate is strong (Lean type-check, JSON-schema validity) the
structural slice is large; where it is weak (free text) it shrinks toward zero
and you lean on a semantic judge. Exactly one class is irreducibly semantic in
every domain (the "means the wrong thing but is otherwise valid" class).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from ..lint import Verdict  # shared verdict type


@dataclass(frozen=True)
class Domain:
    name: str
    failure_classes: dict[str, str]
    structural: Callable[[Any, dict], list[Verdict]]
    reference_diff: Callable[[Any, Any, dict], list[Verdict]]
    semantic_class: str  # the one class no deterministic check can reach


REGISTRY: dict[str, Domain] = {}


def register(domain: Domain) -> Domain:
    REGISTRY[domain.name] = domain
    return domain


def get_domain(name: str) -> Domain:
    if name not in REGISTRY:
        raise KeyError(f"unknown domain {name!r}; registered: {', '.join(REGISTRY)}")
    return REGISTRY[name]


# Register built-in domains on import.
from . import lean_math as _lean_math  # noqa: E402,F401
from . import tool_call as _tool_call  # noqa: E402,F401
