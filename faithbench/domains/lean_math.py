"""Domain: Lean 4 statement autoformalization (the original).

Wraps the deterministic linters in `faithbench.lint`. Cheap gate strength: HIGH
(a real type-checker exists), but reference-FREE reach is only 2/6 classes here
because most math unfaithfulness hides in semantically-equivalent-looking syntax.
`answer_leaking` is the irreducibly semantic class.
"""
from __future__ import annotations

from ..core import FAILURE_CLASSES
from ..lint import run_suite
from ..lint.diff import lint_against_reference


def _structural(artifact, context):
    return run_suite(artifact if isinstance(artifact, str) else str(artifact))


def _reference_diff(candidate, gold, context):
    return lint_against_reference(
        candidate if isinstance(candidate, str) else str(candidate),
        gold if isinstance(gold, str) else str(gold),
    )


def _build():
    from . import Domain, register
    return register(Domain(
        name="lean_math",
        failure_classes=FAILURE_CLASSES,
        structural=_structural,
        reference_diff=_reference_diff,
        semantic_class="answer_leaking",
    ))


DOMAIN = _build()
