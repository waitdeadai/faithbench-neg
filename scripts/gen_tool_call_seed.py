#!/usr/bin/env python3
"""Generate self-verifying `tool_call` domain seed items.

Each base task -> one negative per failure class, mechanically derived and then
VERIFIED against the real domain (structural catches the 5 structural classes,
misses intent_drift; reference_diff catches intent_drift; faithful stays clean).
Mislabeled items abort. Self-verifying, no human labeling.

Usage: python3 scripts/gen_tool_call_seed.py
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from faithbench.domains import get_domain  # noqa: E402

OUT = ROOT / "data" / "seed_tool_call"

# (tool, intent, s_arg, s_val, s_drift, e_arg, enum, e_val)
TASKS = [
    ("get_weather", "Weather in Paris in celsius", "location", "Paris", "London", "unit", ["celsius", "fahrenheit"], "celsius"),
    ("convert_currency", "Convert into EUR", "currency", "EUR", "GBP", "mode", ["spot", "forward"], "spot"),
    ("send_email", "Email alice@x.com", "to", "alice@x.com", "bob@x.com", "priority", ["low", "normal", "high"], "normal"),
    ("search_docs", "Search 'auth flow'", "query", "auth flow", "billing flow", "scope", ["repo", "org", "global"], "repo"),
    ("create_event", "Event 'Standup'", "title", "Standup", "Retro", "visibility", ["public", "private"], "private"),
    ("translate", "Translate to French", "target_lang", "French", "German", "formality", ["formal", "informal"], "formal"),
    ("set_timer", "Timer labeled 'Tea'", "label", "Tea", "Coffee", "sound", ["chime", "bell", "silent"], "chime"),
    ("book_flight", "Flight to Tokyo", "destination", "Tokyo", "Osaka", "cabin", ["economy", "business", "first"], "economy"),
]


def main():
    dom = get_domain("tool_call")
    for old in OUT.glob("gen-*.json"):
        old.unlink()
    n = 0
    for tool, intent, s_arg, s_val, s_drift, e_arg, enum, e_val in TASKS:
        schema = {"type": "object",
                  "properties": {s_arg: {"type": "string"}, e_arg: {"type": "string", "enum": enum}},
                  "required": [s_arg]}
        ctx = {"tools": [{"name": tool, "parameters": schema}]}
        faithful = {"tool": tool, "arguments": {s_arg: s_val, e_arg: e_val}}

        negs = [
            ("wrong_tool", {"tool": "__nonexistent_tool__", "arguments": {s_arg: s_val, e_arg: e_val}}),
            ("missing_required_arg", {"tool": tool, "arguments": {e_arg: e_val}}),
            ("wrong_arg_type", {"tool": tool, "arguments": {s_arg: 123, e_arg: e_val}}),
            ("unexpected_arg", {"tool": tool, "arguments": {s_arg: s_val, e_arg: e_val, "__extra__": 1}}),
            ("enum_violation", {"tool": tool, "arguments": {s_arg: s_val, e_arg: "__bad__"}}),
            ("intent_drift", {"tool": tool, "arguments": {s_arg: s_drift, e_arg: e_val}}),
        ]

        assert dom.structural(faithful, ctx) == [], f"{tool}: faithful flagged (cry-wolf)"
        out_negs = []
        for cls, art in negs:
            fired = dom.structural(art, ctx)
            if cls == "intent_drift":
                assert fired == [], f"{tool}: intent_drift caught structurally (should be blind)"
                assert dom.reference_diff(art, faithful, ctx), f"{tool}: reference_diff missed intent_drift"
            else:
                assert fired, f"{tool}/{cls}: structural failed to catch"
            out_negs.append({"class": cls, "artifact": art})

        item = {"id": f"tc-gen-{tool}", "domain": "tool_call", "label_status": "machine_verified",
                "source": {"note": "generated + self-verified by scripts/gen_tool_call_seed.py"},
                "intent": intent, "context": ctx, "faithful": faithful, "negatives": out_negs}
        (OUT / f"gen-{tool}.json").write_text(json.dumps(item, indent=2) + "\n")
        n += 1
    print(f"wrote {n} self-verified tool_call items to {OUT} (n={n} per class)")


if __name__ == "__main__":
    main()
