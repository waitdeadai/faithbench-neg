# SPEC — `code` domain (code-spec/intent faithfulness)

Goal: leverage the deterministic-hook + per-class-blind-spot architecture into a
`code` domain that productizes faithfulness checking for LLM-generated code, where
the artifact is a Python function, the cheap gate is parse + execute-against-tests,
and the irreducibly-semantic class is `intent_drift` ("passes all given tests but
is still wrong"). Self-verifying: no human labeling.

## Completion conditions

- **C1 — domain registered.** `code` appears in the registry with a 6-class
  taxonomy and `semantic_class == "intent_drift"`.
  verify: `python -m faithbench domains` lists `code: … semantic: intent_drift`.
- **C2 — deterministic reach.** On a self-verifying seed, `faithlint` (the code
  domain's structural gate) catches the 5 structural classes (`syntax_error`,
  `wrong_signature`, `crashes`, `contract_violation`, `forbidden_construct`) at
  100% and is BLIND to `intent_drift`; 0% cry-wolf on the faithful artifact.
  verify: `python -m faithbench score data/seed_code --checkers type_check,faithlint`.
- **C3 — intent_drift recoverable with a reference.** `reference_diff` catches the
  intent_drift negative via held-out probes against the gold oracle.
  verify: `tests/test_code_domain.py::test_reference_diff_catches_intent_drift`.
- **C4 — self-verifying.** The code domain decides correctness by executing the
  candidate (no human labels); seed `label_status == machine_verified`.
  verify: seed file + the passing structural test.
- **C5 — deterministic hook.** `bin/faithlint.sh` works for the code domain
  (domain-general via env), fail-open, strict-exit-2 on a flaw.
  verify: hook invocation with `FAITHLINT_DOMAIN=code`.
- **C6 — no regressions.** Full suite green.
  verify: `python -m pytest -q`.
- **C7 — live.** Pushed to `waitdeadai/faithbench-neg` `main`.
  verify: `gh api repos/waitdeadai/faithbench-neg/commits/main`.

Out of scope: a real LLM-judge for `intent_drift`; multi-language support (Python only at v0).
