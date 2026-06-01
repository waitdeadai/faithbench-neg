"""Domain: agent tool / function-call faithfulness.

The artifact is a JSON object `{"tool": name, "arguments": {...}}`; the item
`context` carries the available tools as `{"tools": [{"name", "parameters": <json
schema>}]}`. Cheap gate strength: HIGH and PURE CODE — JSON-schema validity is
decidable, so 5 of 6 failure classes are caught deterministically with NO human
labeling. The one irreducibly semantic class is `intent_drift`: a call that is
fully schema-valid but does the wrong thing (right tool, wrong argument value vs
what the user asked) — catchable only against a gold reference or by a judge.
"""
from __future__ import annotations

import json
from typing import Any

from ..lint import Verdict

FAILURE_CLASSES: dict[str, str] = {
    "wrong_tool": "Calls a tool that doesn't exist / isn't the right one for the request.",
    "missing_required_arg": "Omits an argument the tool's schema marks required.",
    "wrong_arg_type": "An argument has the wrong JSON type vs the schema.",
    "unexpected_arg": "Passes an argument the tool's schema does not declare.",
    "enum_violation": "An argument value is outside the schema's allowed set.",
    "intent_drift": "Schema-valid but unfaithful to the request (e.g. right tool, wrong value). Semantic — needs a gold reference or a judge.",
}

_JSON_TYPE = {
    "string": lambda v: isinstance(v, str),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "array": lambda v: isinstance(v, list),
    "object": lambda v: isinstance(v, dict),
}


def _parse(artifact: Any) -> dict:
    return artifact if isinstance(artifact, dict) else json.loads(artifact)


def _structural(artifact, context) -> list[Verdict]:
    try:
        call = _parse(artifact)
    except Exception as exc:
        # A call that isn't even valid JSON fails the cheap gate outright.
        return [Verdict("parse", "wrong_tool", f"not valid JSON: {exc}")]
    name = call.get("tool")
    args = call.get("arguments") or {}
    tools = {t["name"]: t for t in (context or {}).get("tools", [])}
    if name not in tools:
        return [Verdict("unknown_tool", "wrong_tool", f"tool {name!r} not in catalog {list(tools)}")]
    schema = tools[name].get("parameters", {})
    props = schema.get("properties", {})
    required = schema.get("required", [])
    out: list[Verdict] = []
    for r in required:
        if r not in args:
            out.append(Verdict("required_arg", "missing_required_arg", f"missing required arg {r!r}"))
    for k, v in args.items():
        if k not in props:
            out.append(Verdict("unexpected_arg", "unexpected_arg", f"arg {k!r} not declared by {name!r}"))
            continue
        spec = props[k]
        t = spec.get("type")
        if t and t in _JSON_TYPE and not _JSON_TYPE[t](v):
            out.append(Verdict("arg_type", "wrong_arg_type", f"arg {k!r} expected {t}, got {type(v).__name__}"))
        if "enum" in spec and v not in spec["enum"]:
            out.append(Verdict("enum", "enum_violation", f"arg {k!r}={v!r} not in {spec['enum']}"))
    return out


def _reference_diff(candidate, gold, context) -> list[Verdict]:
    c, g = _parse(candidate), _parse(gold)
    if c.get("tool") != g.get("tool"):
        return [Verdict("tool_diff", "wrong_tool", f"tool {c.get('tool')!r} != gold {g.get('tool')!r}")]
    ca, ga = (c.get("arguments") or {}), (g.get("arguments") or {})
    out: list[Verdict] = []
    for k in sorted(set(ca) | set(ga)):
        if ca.get(k) != ga.get(k):
            out.append(Verdict("value_diff", "intent_drift", f"arg {k!r}={ca.get(k)!r} differs from gold {ga.get(k)!r}"))
    return out


def _build():
    from . import Domain, register
    return register(Domain(
        name="tool_call",
        failure_classes=FAILURE_CLASSES,
        structural=_structural,
        reference_diff=_reference_diff,
        semantic_class="intent_drift",
    ))


DOMAIN = _build()
