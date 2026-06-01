#!/usr/bin/env python3
"""Generate self-verifying `code` domain seed items.

For each base task we mechanically derive one negative per failure class, then
VERIFY each generated item against the real domain (structural must catch the 5
structural classes, miss intent_drift; reference_diff must catch intent_drift;
faithful must stay clean). Mislabeled items abort the run — that is what makes
the data self-verifying and human-labeling-free.

Usage: python3 scripts/gen_code_seed.py   (writes data/seed_code/gen-*.json)
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from faithbench.domains import get_domain  # noqa: E402

OUT = ROOT / "data" / "seed_code"

# (entry, params, faithful_body, wrong_body, tests[(args,expected)], held_out[(args,expected)])
TASKS = [
    ("add", "a, b", "return a + b", "return a - b", [((2, 3), 5), ((-1, 1), 0)], [((10, 20), 30), ((7, 8), 15)]),
    ("mul", "a, b", "return a * b", "return a + b", [((2, 3), 6), ((4, 5), 20)], [((6, 7), 42), ((0, 9), 0)]),
    ("is_even", "n", "return n % 2 == 0", "return n % 2 == 1", [((4,), True), ((3,), False)], [((10,), True), ((7,), False)]),
    ("maximum", "a, b", "return a if a > b else b", "return a if a < b else b", [((2, 5), 5), ((9, 1), 9)], [((3, 8), 8), ((6, 6), 6)]),
    ("absolute", "n", "return n if n >= 0 else -n", "return n", [((-3,), 3), ((4,), 4)], [((-10,), 10), ((0,), 0)]),
    ("square", "n", "return n * n", "return n + n", [((3,), 9), ((5,), 25)], [((6,), 36), ((2,), 4)]),
    ("reverse_str", "s", "return s[::-1]", "return s", [(("abc",), "cba"), (("xy",), "yx")], [(("hello",), "olleh"), (("ab",), "ba")]),
    ("triple", "n", "return n * 3", "return n * 2", [((2,), 6), ((5,), 15)], [((10,), 30), ((4,), 12)]),
    ("last_char", "s", "return s[-1]", "return s[0]", [(("abc",), "c"), (("xy",), "y")], [(("hello",), "o"), (("zz",), "z")]),
    ("inc", "n", "return n + 1", "return n - 1", [((0,), 1), ((9,), 10)], [((41,), 42), ((-1,), 0)]),
]


def faithful_src(entry, params, body):
    return f"def {entry}({params}):\n    {body}\n"


def build_negatives(entry, params, body, wrong, tests):
    f = faithful_src(entry, params, body)
    # intent_drift: hardcode visible answers, wrong (None) on anything else
    keys = ", ".join(f"{tuple(a)!r}: {e!r}" for a, e in tests)
    drift = f"def {entry}(*args):\n    return {{{keys}}}.get(args, None)\n"
    return [
        ("syntax_error", f"def {entry}({params})\n    {body}\n"),
        ("wrong_signature", f"def _{entry}_renamed({params}):\n    {body}\n"),
        ("crashes", f"def {entry}({params}):\n    _ = undefined_name_xyz\n    {body}\n"),
        ("contract_violation", f"def {entry}({params}):\n    {wrong}\n"),
        ("forbidden_construct", f"def {entry}({params}):\n    _ = eval('1+1')\n    {body}\n"),
        ("intent_drift", drift),
    ]


def main():
    dom = get_domain("code")
    for old in OUT.glob("gen-*.json"):
        old.unlink()
    n = 0
    for entry, params, body, wrong, tests, held in TASKS:
        ctx = {"entrypoint": entry,
               "tests": [{"args": list(a), "expected": e} for a, e in tests],
               "held_out": [{"args": list(a), "expected": e} for a, e in held]}
        faithful = faithful_src(entry, params, body)
        negs = build_negatives(entry, params, body, wrong, tests)

        # SELF-VERIFY before writing
        assert dom.structural(faithful, ctx) == [], f"{entry}: faithful flagged (cry-wolf)"
        out_negs = []
        for cls, art in negs:
            fired = dom.structural(art, ctx)
            if cls == "intent_drift":
                assert fired == [], f"{entry}: intent_drift caught structurally (should be blind)"
                assert dom.reference_diff(art, faithful, ctx), f"{entry}: reference_diff missed intent_drift"
            else:
                assert fired, f"{entry}/{cls}: structural failed to catch"
            out_negs.append({"class": cls, "artifact": art})

        item = {"id": f"code-gen-{entry}", "domain": "code", "label_status": "machine_verified",
                "source": {"note": "generated + self-verified by scripts/gen_code_seed.py"},
                "intent": f"Implement `{entry}({params})` per its tests.",
                "context": ctx, "faithful": faithful, "negatives": out_negs}
        (OUT / f"gen-{entry}.json").write_text(json.dumps(item, indent=2) + "\n")
        n += 1
    print(f"wrote {n} self-verified code items to {OUT} (n={n} per class)")


if __name__ == "__main__":
    main()
