import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from faithbench.lint import run_suite, split_statement
from faithbench.lint.diff import lint_against_reference

FAITHFUL_1 = "theorem ex0001 (x : ℝ) : x ^ 2 = 4 ↔ x = 2 ∨ x = -2 := by sorry"
FAITHFUL_2 = "theorem ex0002 (n : ℕ) : n + 0 = n := by sorry"


def test_parser_splits_goal_and_binders():
    head, binders, goal = split_statement(FAITHFUL_2)
    assert goal == "n + 0 = n"
    assert ("n", "ℕ") in binders


def test_reference_free_catches_structural_classes():
    # vacuous: goal is True
    assert {v.class_id for v in run_suite("theorem t (x : ℝ) : True := by sorry")} == {"vacuous"}
    # conclusion_as_axiom: a hypothesis equals the goal
    circ = "theorem ex0002 (n : ℕ) (h : n + 0 = n) : n + 0 = n := by exact h"
    assert {v.class_id for v in run_suite(circ)} == {"conclusion_as_axiom"}
    # false hypothesis
    assert {v.class_id for v in run_suite("theorem t (h : False) : 1 = 2 := by sorry")} == {"vacuous"}


def test_reference_free_is_blind_to_semantic_classes():
    # answer-leaking and a swapped quantifier are NOT caught reference-free — by design.
    leak = "theorem ex0001 : (2 : ℝ) ^ 2 = 4 ∨ (-2 : ℝ) ^ 2 = 4 := by sorry"
    swap = "theorem ex0001 : ∃ x : ℝ, x ^ 2 = 4 ↔ x = 2 ∨ x = -2 := by sorry"
    assert run_suite(leak) == []
    assert run_suite(swap) == []


def test_reference_free_no_false_positive_on_faithful():
    assert run_suite(FAITHFUL_1) == []
    assert run_suite(FAITHFUL_2) == []


def test_reference_diff_catches_three_more_classes():
    swap = "theorem ex0001 : ∃ x : ℝ, x ^ 2 = 4 ↔ x = 2 ∨ x = -2 := by sorry"
    prem = "theorem ex0001 (x : ℝ) (h : x > 0) : x ^ 2 = 4 ↔ x = 2 ∨ x = -2 := by sorry"
    dom = "theorem ex0002 (n : ℤ) : n + 0 = n := by sorry"
    assert any(v.class_id == "quantifier_swapped" for v in lint_against_reference(swap, FAITHFUL_1))
    assert any(v.class_id == "premise_mistranslated" for v in lint_against_reference(prem, FAITHFUL_1))
    assert any(v.class_id == "domain_type_mismatch" for v in lint_against_reference(dom, FAITHFUL_2))


def test_reference_diff_blind_to_answer_leaking():
    # even WITH a gold reference, answer-leaking needs a semantic judge.
    leak = "theorem ex0001 : (2 : ℝ) ^ 2 = 4 ∨ (-2 : ℝ) ^ 2 = 4 := by sorry"
    assert not any(v.class_id == "answer_leaking" for v in lint_against_reference(leak, FAITHFUL_1))
