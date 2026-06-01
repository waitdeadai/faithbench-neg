"""Mutation generator (SKELETON).

Proposes candidate negatives for a faithful item. The real engine needs a Lean
AST (via LeanInteract / Lean metaprogramming) to apply per-class structural
rewrites and keep only candidates that still TYPE-CHECK. v0 ships deterministic
textual placeholders + explicit TODOs so a human only ever labels plausible,
compiling survivors — never a fabricated 'verified' negative.
"""
from __future__ import annotations

from .core import Item, Negative


def propose(item: Item) -> list[Negative]:
    s = item.faithful
    return [
        Negative(
            class_id="conclusion_as_axiom",
            artifact="-- TODO(human): add the goal as a hypothesis `(h : <goal>)`, then weaken the goal\n" + s,
            note="machine-proposed skeleton; MUST be type-checked and human-verified before use",
            label_status="machine_proposed",
        ),
        Negative(
            class_id="vacuous",
            artifact="-- TODO(human): replace the goal term with `True`\n" + s,
            note="machine-proposed skeleton; MUST be type-checked and human-verified before use",
            label_status="machine_proposed",
        ),
    ]

# Honest limitation: without Lean AST access these are placeholders, not
# compiling negatives. Wire LeanInteract to (a) parse the statement, (b) apply
# structural rewrites per failure class, (c) keep only those that still
# type-check, then hand survivors to a human labeler.
