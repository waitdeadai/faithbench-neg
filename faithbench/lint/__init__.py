"""Deterministic, reference-free faithfulness linters for Lean 4 statements.

These are the bash-hook-able slice: pure string/structure checks with NO LLM and
NO randomness, so they are reproducible and fail-open. They catch only the
*structural* failure classes that are decidable from the surface syntax of a lone
statement (no informal text, no gold reference). Everything else — the dangerous,
semantically-equivalent-looking cases — is intentionally OUT of scope here and
must be escalated to a semantic judge. See `faithbench.lint.diff` for the
reference-aware checks usable when a gold statement exists.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_OPEN, _CLOSE = "([{⟨", ")]}⟩"


@dataclass(frozen=True)
class Verdict:
    linter: str
    class_id: str
    evidence: str


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def split_statement(s: str) -> tuple[str, list[tuple[str, str]], str]:
    """Return (head, binders, goal) for a `theorem … : GOAL := …` string.

    binders is a list of (name, type/prop) pairs parsed from top-level (..)/{..}/[..]
    groups. Deterministic: paren-depth scan, no heuristics. Returns ('', [], '')
    when there is no top-level goal colon."""
    body = s.split(":=", 1)[0]
    depth = 0
    colon = -1
    for i, ch in enumerate(body):
        if ch in _OPEN:
            depth += 1
        elif ch in _CLOSE:
            depth -= 1
        elif ch == ":" and depth == 0:
            colon = i  # FIRST depth-0 colon is the goal separator (binder
            break      # colons are depth>0; later depth-0 colons, e.g. `∃ x : T,`,
                       # live inside the goal)
    if colon == -1:
        return _norm(body), [], ""
    head, goal = body[:colon], body[colon + 1:]
    return _norm(head), _binders(head), _norm(goal)


def _binders(head: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    depth = 0
    start = -1
    for i, ch in enumerate(head):
        if ch in "([{":
            if depth == 0:
                start = i + 1
            depth += 1
        elif ch in ")]}":
            depth -= 1
            if depth == 0 and start != -1:
                content = head[start:i]
                if ":" in content:
                    name, _, prop = content.partition(":")
                    out.append((_norm(name), _norm(prop)))
                start = -1
    return out


# ── reference-free linters: each returns a Verdict or None ──────────────────

_VACUOUS_GOALS = {"True", "true", "⊤"}


def lint_vacuous_goal(s: str):
    _, _, goal = split_statement(s)
    if goal in _VACUOUS_GOALS:
        return Verdict("vacuous_goal", "vacuous", f"goal is `{goal}` (trivially provable)")
    return None


def lint_false_hypothesis(s: str):
    _, binders, _ = split_statement(s)
    for name, prop in binders:
        if prop in {"False", "⊥"}:
            return Verdict("false_hypothesis", "vacuous", f"hypothesis `{name} : {prop}` makes the theorem vacuous")
    return None


def lint_self_axiom(s: str):
    _, binders, goal = split_statement(s)
    if not goal:
        return None
    for name, prop in binders:
        if prop == goal:
            return Verdict("self_axiom", "conclusion_as_axiom",
                           f"hypothesis `{name} : {prop}` equals the goal (circular)")
    return None


DEFAULT_SUITE = [lint_vacuous_goal, lint_false_hypothesis, lint_self_axiom]


def run_suite(statement: str, suite=DEFAULT_SUITE) -> list[Verdict]:
    """Run every linter; return the Verdicts that fired (deterministic order)."""
    return [v for lint in suite if (v := lint(statement)) is not None]
