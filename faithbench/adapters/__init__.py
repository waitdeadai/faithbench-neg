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
    """Semantic faithfulness judge — the layer that catches each domain's
    irreducibly-semantic class (intent_drift / answer_leaking) that the
    deterministic structural gate is blind to.

    Model-agnostic and dependency-free: provide a judge via either
      - `call=<fn(prompt)->str>` (used for tests / custom wiring), or
      - env `FAITHBENCH_JUDGE_CMD` = a shell command that reads the prompt on
        stdin and prints a verdict on stdout (point it at ANY model CLI, e.g.
        `claude -p` or `llm -m ...`).
    If neither is set it RAISES — never fabricates a verdict. A verdict containing
    'UNFAITHFUL' => unfaithful; otherwise faithful (default-faithful, judge must
    affirmatively object)."""
    name = "llm_judge"

    PROMPT = (
        "You are a strict faithfulness judge. Decide if the CANDIDATE faithfully "
        "satisfies the INTENT — not merely whether it is well-formed.\n\n"
        "INTENT:\n{intent}\n\nCANDIDATE:\n{artifact}\n\n"
        "Answer with exactly one word: FAITHFUL or UNFAITHFUL."
    )

    def __init__(self, call=None, model: str | None = None):
        self._call = call
        self.model = model or os.environ.get("FAITHBENCH_JUDGE_MODEL", "")

    def _judge(self, prompt: str) -> str:
        if self._call is not None:
            return self._call(prompt)
        cmd = os.environ.get("FAITHBENCH_JUDGE_CMD")
        if cmd:
            import subprocess
            p = subprocess.run(cmd, shell=True, input=prompt.encode(),
                               capture_output=True, timeout=120)
            return p.stdout.decode()
        raise NotImplementedError(
            "LLMJudge needs an injected `call` or env FAITHBENCH_JUDGE_CMD "
            "(a CLI that reads the prompt on stdin, prints FAITHFUL/UNFAITHFUL). "
            "Not faked by design.")

    def classify(self, item, artifact) -> bool:
        verdict = (self._judge(self.PROMPT.format(intent=item.intent, artifact=artifact)) or "").upper()
        return "UNFAITHFUL" not in verdict


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
