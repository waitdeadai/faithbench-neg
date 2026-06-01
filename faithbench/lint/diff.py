"""Reference-AWARE deterministic linters.

These compare a candidate statement against a known-faithful *gold* statement, so
they only apply when you have a reference (e.g. regression-testing an
autoformalizer against a labeled gold set) — NOT in the wild on a lone statement.
Still fully deterministic (structural diff, no LLM). They cover three more classes
than the reference-free suite; `answer_leaking` remains out of reach for either —
it needs a semantic judge.
"""
from __future__ import annotations

from . import Verdict, split_statement


def _count(s: str, ch: str) -> int:
    return s.count(ch)


def lint_against_reference(candidate: str, gold: str) -> list[Verdict]:
    out: list[Verdict] = []
    _, cb, cg = split_statement(candidate)
    _, gb, gg = split_statement(gold)

    # quantifier_swapped: top-level ∀/∃ balance of the goal changed
    if (_count(cg, "∃") != _count(gg, "∃")) or (_count(cg, "∀") != _count(gg, "∀")):
        out.append(Verdict("quantifier_diff", "quantifier_swapped",
                           f"goal quantifiers differ from gold (∀ {_count(gg,'∀')}→{_count(cg,'∀')}, ∃ {_count(gg,'∃')}→{_count(cg,'∃')})"))

    # premise_mistranslated: hypothesis/binder count changed
    if len(cb) != len(gb):
        verb = "added" if len(cb) > len(gb) else "dropped"
        out.append(Verdict("hyp_count_diff", "premise_mistranslated",
                           f"binder/hypothesis count {len(gb)}→{len(cb)} ({verb} vs gold)"))

    # domain_type_mismatch: a same-named binder's type changed
    gtypes = {n: t for n, t in gb}
    for n, t in cb:
        if n in gtypes and gtypes[n] != t:
            out.append(Verdict("binder_type_diff", "domain_type_mismatch",
                               f"binder `{n}` type {gtypes[n]}→{t} vs gold"))
            break
    return out
