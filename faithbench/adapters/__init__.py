"""Faithfulness checkers (domain-agnostic interface).

A checker answers: is this artifact a FAITHFUL rendering of the item's intent?
`classify(item, artifact)` returns True for faithful. It receives the whole Item
so it can use the domain + context (e.g. a tool schema). The benchmark scores a
checker by how many KNOWN-unfaithful negatives it flags, per failure class.

Real semantic checkers (LLM judge, BEq+) are intentionally raising stubs rather
than fabricating results.
"""
from __future__ import annotations

import os
import re
from typing import Protocol


class Checker(Protocol):
    name: str
    def classify(self, item, artifact) -> bool: ...


class TypeCheckOnly:
    """Models a 'does it pass the cheap gate?' baseline that always says faithful.
    Expected to score 0% on every class — the headline blind spot."""
    name = "type_check"

    def classify(self, item, artifact) -> bool:
        return True


class MockJudge:
    """Deterministic TOY judge (lean_math only) for wiring/CI. Flags `True`
    goals. Not a real semantic check."""
    name = "mock_judge"
    _vacuous = re.compile(r"\bTrue\b")

    def classify(self, item, artifact) -> bool:
        return self._vacuous.search(str(artifact)) is None


class FaithLint:
    """The deterministic structural slice for the item's DOMAIN. Reproducible,
    no LLM: unfaithful when any structural check fires. Blind to each domain's
    irreducibly-semantic class by design — that blind spot is the honest point."""
    name = "faithlint"

    def classify(self, item, artifact) -> bool:
        from ..domains import get_domain
        return not get_domain(item.domain).structural(artifact, item.context)


class LLMJudge:
    """Real semantic faithfulness judge via an LLM API. Stub by design."""
    name = "llm_judge"

    def __init__(self, model: str | None = None):
        self.model = model or os.environ.get("FAITHBENCH_JUDGE_MODEL", "")

    def classify(self, item, artifact) -> bool:
        raise NotImplementedError(
            "LLMJudge is a stub. Implement an API call that asks the model whether "
            "`artifact` faithfully renders `item.intent`, returning a boolean. "
            "Left unimplemented on purpose so results are never fabricated.")


class BEqPlus:
    """BEq+ symbolic equivalence (Poiroux et al., EMNLP 2025) via LeanInteract.
    lean_math only; requires a Lean toolchain. Stub by design."""
    name = "beq_plus"

    def classify(self, item, artifact) -> bool:
        raise NotImplementedError(
            "BEqPlus requires a Lean 4 toolchain + LeanInteract. Not stubbed with "
            "fake results by design.")


REGISTRY = {c.name: c for c in (TypeCheckOnly, MockJudge, FaithLint, LLMJudge, BEqPlus)}


def build_checkers(names: list[str]) -> list[Checker]:
    out: list[Checker] = []
    for n in names:
        n = n.strip()
        if n not in REGISTRY:
            raise SystemExit(f"unknown checker {n!r}; available: {', '.join(REGISTRY)}")
        out.append(REGISTRY[n]())
    return out
