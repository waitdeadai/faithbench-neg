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

## Deterministic lint suite (`faithbench.lint`) — and its honest ceiling

A suite of **single-purpose, deterministic, fail-open** linters in the bash-hook
idiom. No LLM, no network, no randomness — same input → same verdict. They are a
fast **pre-filter**, not a faithfulness oracle.

```bash
python -m faithbench lint 'theorem t (x : ℝ) : True := by sorry'   # -> vacuous
bin/faithlint.sh '<statement>'            # hook form; fail-open (exit 0)
FAITHLINT_STRICT=1 bin/faithlint.sh '<statement>'   # CI mode; exit 2 on a flaw
python -m faithbench score data/seed --checkers type_check,faithlint,mock_judge
```

**What determinism can and cannot reach (measured on the seed, not asserted):**

| | reference-free (lone statement / hook) | + reference-diff (gold known) | needs semantic judge |
|---|---|---|---|
| `vacuous` | ✅ goal is `True` / `False` hyp | ✅ | |
| `conclusion_as_axiom` | ✅ hypothesis == goal | ✅ | |
| `quantifier_swapped` | ❌ | ✅ ∀/∃ diff vs gold | |
| `premise_mistranslated` | ❌ | ✅ binder-count diff | |
| `domain_type_mismatch` | ❌ | ✅ binder-type diff | |
| `answer_leaking` | ❌ | ❌ | **only here** |

So: **2 of 6 classes** are catchable from a lone statement (the hook case), **5 of 6**
once a gold reference exists (the autoformalizer-regression case), and `answer_leaking`
is irreducibly semantic — it needs the LLM judge that the literature puts at a ~45%
ceiling. The deterministic suite's job is to catch the cheap cases at zero cost and
**escalate the rest**, never to pretend it judged them. Two honesty constraints baked
in: linters are **fail-open** (any error → exit 0), and the reference-free hook flags
only **high-precision** patterns (0% false-positive on the seed's faithful statements).

> Real-world caveat (from the adversarial review): the reference-free hook needs only
> a lone Lean statement, but the higher-recall reference-diff checks need a paired gold
> statement, which mathlib/blueprint projects don't systematically carry. The suite is
> most useful as a **regression gate on an autoformalizer that already has gold targets**,
> and as a cheap pre-filter elsewhere.

## Universal: domains (not math-only)

faithbench is a **domain-pluggable framework**. The item model, scorer, and CLI
are domain-agnostic; everything domain-specific lives behind one interface
(`faithbench/domains/`): a failure-class taxonomy, a deterministic
`structural(artifact, context)` "cheap gate", and a `reference_diff` against a
gold artifact. Adding a domain = implement that interface and `register()`.

```bash
python -m faithbench domains                      # list registered domains
python -m faithbench score data/seed              # lean_math (auto-detected)
python -m faithbench score data/seed_tool_call    # tool_call
python -m faithbench lint --domain tool_call --context tools.json '{"tool":"get_weather","arguments":{"unit":"kelvin"}}'
```

Two domains ship, and they make the central point measurable: **how much of
faithfulness is deterministically checkable depends entirely on how strong the
domain's cheap gate is.**

| domain | cheap gate | reference-free reach | irreducibly-semantic class | data |
|---|---|---|---|---|
| `lean_math` | Lean type-check | **2 / 6** classes | `answer_leaking` | needs human Lean+math labeling |
| `tool_call` | JSON-schema validity (pure code) | **5 / 6** classes | `intent_drift` | **self-verifying** (machine-decidable) |

The `tool_call` domain (agent / function-call faithfulness) is the cleaner proof:
because schema validity is decidable by code, its structural negatives need **no
human labeling** — the seed is `machine_verified`. Every domain still has exactly
one class that is "valid but means the wrong thing" and needs a semantic judge —
`answer_leaking` for math, `intent_drift` for tool calls. That is the honest,
universal shape: **valid ≠ faithful; the deterministic suite catches the cheap
violations for free and escalates the one semantic class.**

License: Apache-2.0.
