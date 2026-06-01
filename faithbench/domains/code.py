"""Domain: code-spec / intent faithfulness (Python, self-verifying).

Artifact = a Python function source string. `context` carries:
  {"entrypoint": "fn", "tests": [{"args": [...], "kwargs": {...}, "expected": ...}],
   "held_out": [...same shape, inputs used by reference_diff...],
   "forbidden": ["eval", ...], "timeout": 2.0}

Cheap gate strength: HIGH and PURE CODE — parse + run-against-tests is decidable,
so 5 of 6 classes are caught deterministically with NO human labeling. The
irreducibly-semantic class is `intent_drift`: code that PASSES every provided test
but is still wrong (overfit / Goodhart). By definition the visible tests can't see
it; you need held-out probes against a gold oracle (reference_diff) or a judge.

SAFETY: executes candidate code IN-PROCESS with a wall-clock timeout. Intended for
TRUSTED benchmark data only. For untrusted candidates, run behind a real sandbox
(subprocess / container / seccomp); the structural() interface is unchanged.
"""
from __future__ import annotations

import ast
import signal
from typing import Any

from ..lint import Verdict

FAILURE_CLASSES: dict[str, str] = {
    "syntax_error": "Does not parse — fails the cheapest gate.",
    "wrong_signature": "Entry-point function is missing or wrongly named vs the spec.",
    "crashes": "Raises (or times out) on a provided input.",
    "contract_violation": "Runs but returns the wrong result on a provided test.",
    "forbidden_construct": "Uses a banned construct (eval/exec/etc.) — e.g. cheating the check.",
    "intent_drift": "Passes ALL provided tests but is still wrong (overfit/Goodhart). Semantic — needs held-out probes or a judge.",
}

_DEFAULT_FORBIDDEN = {"eval", "exec", "__import__", "compile", "open"}


class _Timeout(Exception):
    pass


def _call(func, args, kwargs, timeout):
    """Call func with a best-effort wall-clock timeout (Unix main thread)."""
    armed = False
    if hasattr(signal, "SIGALRM"):
        try:
            def _h(signum, frame):
                raise _Timeout()
            signal.signal(signal.SIGALRM, _h)
            signal.setitimer(signal.ITIMER_REAL, float(timeout))
            armed = True
        except (ValueError, OSError):
            armed = False  # not main thread — run without a timer
    try:
        return func(*args, **(kwargs or {}))
    finally:
        if armed:
            signal.setitimer(signal.ITIMER_REAL, 0)


def _load(source: str, entry: str):
    ns: dict[str, Any] = {}
    exec(compile(source, "<faithbench-code>", "exec"), ns)  # noqa: S102 (trusted data)
    fn = ns.get(entry)
    return fn if callable(fn) else None


def _structural(artifact, context) -> list[Verdict]:
    source = artifact if isinstance(artifact, str) else str(artifact)
    entry = (context or {}).get("entrypoint")
    tests = (context or {}).get("tests", [])
    forbidden = set((context or {}).get("forbidden", _DEFAULT_FORBIDDEN))
    timeout = (context or {}).get("timeout", 2.0)

    # 1) syntax
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return [Verdict("syntax", "syntax_error", f"does not parse: {e}")]

    # 2) signature
    funcs = {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    if entry and entry not in funcs:
        return [Verdict("signature", "wrong_signature", f"no function named {entry!r} (found {sorted(funcs)})")]

    # 3) forbidden constructs — short-circuit (don't execute code we've flagged)
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in forbidden:
            return [Verdict("forbidden", "forbidden_construct", f"uses forbidden `{node.id}`")]

    # 4) execute against the provided tests
    try:
        fn = _load(source, entry)
    except Exception as e:  # noqa: BLE001
        return [Verdict("load", "crashes", f"module load raised {type(e).__name__}: {e}")]
    if fn is None:
        return [Verdict("signature", "wrong_signature", f"{entry!r} is not a callable after load")]

    for t in tests:
        args, kwargs, expected = t.get("args", []), t.get("kwargs", {}), t.get("expected")
        try:
            got = _call(fn, args, kwargs, timeout)
        except _Timeout:
            return [Verdict("timeout", "crashes", f"timed out on args={args}")]
        except Exception as e:  # noqa: BLE001
            return [Verdict("runtime", "crashes", f"raised {type(e).__name__} on args={args}")]
        if got != expected:
            return [Verdict("contract", "contract_violation", f"f(*{args})={got!r}, expected {expected!r}")]
    return []


def _reference_diff(candidate, gold, context) -> list[Verdict]:
    entry = (context or {}).get("entrypoint")
    probes = list((context or {}).get("held_out", [])) + list((context or {}).get("tests", []))
    timeout = (context or {}).get("timeout", 2.0)
    try:
        gfn, cfn = _load(gold, entry), _load(candidate, entry)
    except Exception:  # noqa: BLE001
        return []
    if gfn is None or cfn is None:
        return []
    for p in probes:
        args, kwargs = p.get("args", []), p.get("kwargs", {})
        try:
            g = _call(gfn, args, kwargs, timeout)
        except Exception:  # noqa: BLE001
            continue  # gold itself errors on this probe — skip
        try:
            c = _call(cfn, args, kwargs, timeout)
        except Exception as e:  # noqa: BLE001
            return [Verdict("diff_crash", "intent_drift", f"candidate raises {type(e).__name__} on {args} where gold is fine")]
        if c != g:
            return [Verdict("value_diff", "intent_drift", f"f(*{args})={c!r} != gold {g!r}")]
    return []


def _build():
    from . import Domain, register
    return register(Domain(
        name="code",
        failure_classes=FAILURE_CLASSES,
        structural=_structural,
        reference_diff=_reference_diff,
        semantic_class="intent_drift",
    ))


DOMAIN = _build()
