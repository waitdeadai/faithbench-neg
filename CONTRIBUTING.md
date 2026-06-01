# Contributing

The code is the easy part; **the labeled data is the product.** Contributions to
the harness are welcome, but the bar for *data* is deliberately high.

## Data labeling protocol

1. **Source.** Anchor each item on a **fresh 2025–2026 competition / problem set**
   to resist training-data contamination. Prefer the *answer-determination* class
   ("determine all / find the value") — it is under-benchmarked and where leakage
   bugs concentrate.
2. **Faithful statement.** Write one Lean 4 statement that **type-checks against a
   pinned Mathlib** and that a domain expert agrees faithfully captures the problem.
   Record the Mathlib/Lean toolchain version.
3. **Negatives.** For each applicable failure class, write a statement that **still
   type-checks** but is unfaithful. Tag it with its class (see `TAXONOMY.md`).
4. **Type-check gate.** Every statement (faithful and negatives) must compile.
   Machine-proposed candidates (`label_status: machine_proposed`) are *not* data
   until a human verifies them.
5. **Inter-annotator agreement.** A ≥20-item subset must be independently
   re-labeled by a second annotator with **agreement ≥ 0.8** before release.
   Labeling quality is the moat; treat disagreements as bugs.
6. **No leakage in the NL.** The informal problem text must not contain the answer.

## Positioning (keep us honest)

Every release must explicitly diff against **CriticLeanBench**, **ProofNetVerif**,
and **FormalEvolve** (see README) so the delta — *named per-class taxonomy + per-class
catch-rates as a reusable held-out suite* — stays legible. If that delta ever
closes (an incumbent ships per-class reporting), say so in the README rather than
overclaim.

## Code

- Keep the core dependency-free; put heavy deps (LeanInteract, API SDKs) behind
  optional extras and adapter stubs that **raise rather than fabricate**.
- `python -m pytest -q` must pass.
- New checker? Add it to `faithbench/adapters/` and the `REGISTRY`.
