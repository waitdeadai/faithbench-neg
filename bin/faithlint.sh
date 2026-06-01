#!/usr/bin/env bash
# faithlint — deterministic Lean-statement faithfulness linter, hook form.
#
# Single-purpose, out-of-band, FAIL-OPEN: it inspects a Lean 4 statement and
# reports structural faithfulness flaws (vacuous goal, False hypothesis, goal
# asserted as a hypothesis). It NEVER blocks by default (exit 0); set
# FAITHLINT_STRICT=1 to exit non-zero when a flaw is found (for CI / pre-commit).
#
# It is deterministic: same input -> same output, no LLM, no network. It is also
# DELIBERATELY shallow — it catches only the cheap, decidable cases and is blind
# to semantic unfaithfulness (e.g. answer-leaking). Treat a clean result as
# "no cheap flaw found", NOT "faithful".
#
# Usage:
#   faithlint.sh 'theorem t (x : ℝ) : True := by sorry'   # statement as arg
#   echo '<statement>' | faithlint.sh                      # or on stdin
#
# Requires `faithbench` importable (run from the repo root, or `pip install -e .`).
set -uo pipefail

stmt="${1:-}"
if [ -z "${stmt}" ]; then stmt="$(cat)"; fi

# Domain-general: FAITHLINT_DOMAIN (default lean_math) + optional FAITHLINT_CONTEXT
# (path to a JSON context file, e.g. tool schemas / code spec+tests).
domain="${FAITHLINT_DOMAIN:-lean_math}"
ctx=()
[ -n "${FAITHLINT_CONTEXT:-}" ] && ctx=(--context "${FAITHLINT_CONTEXT}")

# Fail-open: any internal error -> exit 0, never break the caller's pipeline.
out="$(printf '%s' "${stmt}" | python3 -m faithbench lint --domain "${domain}" "${ctx[@]}" 2>/dev/null)" || exit 0

if [ -n "${out}" ]; then
  while IFS= read -r line; do
    printf 'faithlint: %s\n' "${line}" >&2
  done <<< "${out}"
  if [ "${FAITHLINT_STRICT:-0}" = "1" ]; then exit 2; fi
fi
exit 0
