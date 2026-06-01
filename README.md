# faithbench-neg

**A held-out, per-failure-class benchmark of plausible-but-_unfaithful_ Lean 4 statement formalizations — plus a scorer that ranks any faithfulness checker by its _per-class_ catch-rate.**

When an LLM autoformalizes "determine all x such that …" into a Lean statement, the statement can **type-check and still be the wrong theorem**: vacuous, answer-leaking, quantifier-swapped, premise-mistranslated, circular, or off-by-a-domain. Aggregate "judge accuracy" numbers hide _which_ of these a checker is blind to. `faithbench-neg` measures exactly that: every negative compiles, and the report is a **per-class catch-rate table**.

> **Honest status (read this first).** This repo is the *machine*: taxonomy, schema, scorer, baseline adapters, and a mutation skeleton — all runnable today. It is **not** yet a benchmark: the seed data is **illustrative placeholder** (`label_status: UNVERIFIED_EXAMPLE`, Lean **not** type-checked). The actual value — a held-out set of human-verified, compiling negatives — is **labeling work that requires Lean 4 + competition-math expertise** and has not been done here. The taxonomy + harness is the reusable asset; the labels are the moat.

## Why this might matter (and the honest caveats)

This was selected by an adversarial research pass over the 2026 autoformalization frontier, and it survived as a **7/10 — "a win on execution, not a wide moat."** Keeping that honesty up front:

- **The gap is real but narrow.** No existing artifact ships a *named per-failure-class taxonomy with per-class catch-rates*. Closest neighbors and how we differ:
  - **CriticLeanBench** (arXiv:2507.06181) — ships labeled incorrect formalizations, but with unstructured "error annotations (where applicable)", **no per-class taxonomy, no per-class catch-rates**.
  - **ProofNetVerif** (EMNLP 2025) — human-vs-judge agreement in **aggregate**, not per failure class.
  - **FormalEvolve** (arXiv:2603.19828) — AST rewriting for autoformalization **search diversity**, not adversarial-negative generation by failure class.
- **Incumbent-absorption risk is the #1 kill-shot.** M-A-P or EPFL own labeled negatives + annotation pipelines and could fold per-class reporting into a dataset-card update quickly. The moat is being *first* and being the *canonical held-out suite people cite*.
- **Labeling is slow, scarce, and IS the product.** A rushed/sloppy set has near-zero value.
- **Short half-life.** Once public and scraped, usefulness may be ~one model generation. Anchor seeds on **fresh 2025–2026 competitions** to resist contamination.

If you can't commit real Lean+math labeling, the honest move is to **contribute the taxonomy upstream** rather than ship a thin set.

## Install / run

No dependencies for the core (Python ≥3.10). `pytest` for tests.

```bash
# from the repo root
python -m faithbench.cli validate data/seed
python -m faithbench.cli score    data/seed --checkers type_check,mock_judge
python -m faithbench.cli mutate    data/seed/example-0001.json
python -m pytest -q
```

### The headline the scorer is built to produce

`type_check` (compile-only) catches **0%** on every class — by construction, since all negatives compile. A real `llm_judge` (stub here) will catch some classes far better than others. That **per-class divergence** — not an aggregate number — is the deliverable. `v0` success = a table where at least one baseline is near-0 on at least one class.

## What's here

| Piece | State |
|---|---|
| `faithbench/core.py` | frozen taxonomy (v0.1.0) + item model + validation | ✅ runnable |
| `faithbench/scoring.py` | per-class catch-rate + cry-wolf (FP) + table | ✅ runnable |
| `faithbench/adapters/` | `type_check` + `mock_judge` (toy) run; `llm_judge`, `beq_plus` are **honest stubs** (raise, never fake) | ⚠️ partial |
| `faithbench/mutate.py` | textual-placeholder skeleton; real version needs Lean AST via LeanInteract | ⚠️ skeleton |
| `data/seed/` | 2 **UNVERIFIED_EXAMPLE** items — placeholders, Lean not type-checked | ❌ not real data |

## Roadmap to a real `v0`

1. Replace seed with **~50 human-verified items** (target 150–250 at v1), each: a fresh-competition NL problem (answer-determination class), one faithful Lean 4 statement that **type-checks against Mathlib**, and one labeled negative per applicable class (each must compile).
2. Wire `llm_judge` (real API) and `beq_plus` (LeanInteract) adapters.
3. Wire the mutation generator to a Lean AST + a type-check gate so humans only label compiling survivors.
4. Publish the **per-class catch-rate leaderboard** — the thing no existing benchmark reports.

License: Apache-2.0.
