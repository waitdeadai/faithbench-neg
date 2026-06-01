"""Faithfulness checkers.

A checker answers one question: is this Lean statement a FAITHFUL rendering of
the informal problem? `classify` returns True for faithful, False for unfaithful.
The benchmark scores a checker by how many KNOWN-unfaithful negatives it flags
(per failure class). Every negative type-checks by construction, so a
type-check-only gate catches nothing — that blind spot is the point.

Real checkers (LLM judge, BEq+) are intentionally left as raising stubs rather
than fabricating results.
"""
from __future__ import annotations

import os
import re
from typing import Protocol


class Checker(Protocol):
    name: str
    def classify(self, nl_problem: str, statement: str) -> bool: ...


class TypeCheckOnly:
    """Models a gate that only asks 'does it compile?'. Everything in the
    benchmark compiles, so this returns faithful=True always and is expected to
    score 0% catch-rate on every class — the headline blind spot."""
    name = "type_check"

    def classify(self, nl_problem: str, statement: str) -> bool:
        return True


class MockJudge:
    """Deterministic TOY judge for wiring/CI only — NOT a real semantic check.
    Flags as unfaithful any statement whose goal is literally `True` (the vacuous
    class). Exists so the scorer and tests run end-to-end and to demonstrate
    per-class divergence. Replace with LLMJudge for real evaluation."""
    name = "mock_judge"
    _vacuous = re.compile(r"\bTrue\b")

    def classify(self, nl_problem: str, statement: str) -> bool:
        return self._vacuous.search(statement) is None


class LLMJudge:
    """Real semantic faithfulness judge via an LLM API. Stub by design."""
    name = "llm_judge"

    def __init__(self, model: str | None = None):
        self.model = model or os.environ.get("FAITHBENCH_JUDGE_MODEL", "")

    def classify(self, nl_problem: str, statement: str) -> bool:
        raise NotImplementedError(
            "LLMJudge is a stub. Implement an API call that asks the model whether "
            "`statement` faithfully formalizes `nl_problem`, returning a boolean. "
            "Left unimplemented on purpose so results are never fabricated.")


class BEqPlus:
    """BEq+ symbolic equivalence (Poiroux et al., EMNLP 2025) via LeanInteract.
    Requires a Lean 4 toolchain + LeanInteract; not bundled, stub by design."""
    name = "beq_plus"

    def classify(self, nl_problem: str, statement: str) -> bool:
        raise NotImplementedError(
            "BEqPlus requires a Lean 4 toolchain + LeanInteract (beq_plus.py). "
            "See README. Not stubbed with fake results by design.")


REGISTRY = {c.name: c for c in (TypeCheckOnly, MockJudge, LLMJudge, BEqPlus)}


def build_checkers(names: list[str]) -> list[Checker]:
    out: list[Checker] = []
    for n in names:
        n = n.strip()
        if n not in REGISTRY:
            raise SystemExit(f"unknown checker {n!r}; available: {', '.join(REGISTRY)}")
        out.append(REGISTRY[n]())
    return out
