# Faithfulness failure taxonomy — v0.1.0

A *negative* is a Lean 4 statement that **type-checks** but is an **unfaithful**
formalization of the informal problem. Each negative is tagged with exactly one
primary failure class. This taxonomy is versioned; adding/renaming/removing a
class is a **breaking** change and bumps `TAXONOMY_VERSION` in `faithbench/core.py`.

| id | definition | canonical (illustrative) example |
|---|---|---|
| `vacuous` | Trivially true — goal is `True`, or a hypothesis is contradictory — so any proof is meaningless. | goal replaced by `True`: `theorem t (x : ℝ) : True := …` |
| `answer_leaking` | The to-be-determined value is baked into the statement, so it no longer asks what the problem asks. | `(2:ℝ)^2 = 4 ∨ (-2:ℝ)^2 = 4` instead of "for all x, x²=4 ↔ x=±2" |
| `quantifier_swapped` | Quantifier kind/order is wrong (∀/∃ swapped, bounded vs unbounded, reordered binders). | `∃ x, P x` where the problem means `∀ x, P x` |
| `premise_mistranslated` | A hypothesis is dropped, weakened, strengthened, or altered vs the informal problem. | adds a spurious `(h : x > 0)` the problem never stated |
| `conclusion_as_axiom` | The goal is asserted as a hypothesis (or otherwise assumed), making the theorem circular. | `(h : Goal) : Goal := by exact h` |
| `domain_type_mismatch` | Wrong type/domain or boundary (ℕ vs ℤ, `<` vs `≤`, off-by-one bounds, …). | states it over `ℤ` when the problem is about `ℕ` |

## Labeling rules

- A negative **must type-check** (the whole point is that it passes the cheap filter).
- Pick the **single most salient** failure class. If a statement exhibits two, file
  it under the one a reader would notice last (the more dangerous one), and note the other.
- Examples in this file are **illustrative and have not been machine-verified**.
- Faithful statements must be **human-verified to type-check against Mathlib** before
  an item leaves `UNVERIFIED_EXAMPLE` status.
