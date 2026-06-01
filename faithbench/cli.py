"""faithbench command line (domain-agnostic)."""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

from .adapters import REGISTRY, build_checkers
from .core import TAXONOMY_VERSION, _item_from_dict, load_items
from .mutate import propose
from .scoring import format_table, score


def cmd_validate(a) -> int:
    items = load_items(a.data_dir)
    n_neg = sum(len(i.negatives) for i in items)
    domains = sorted({i.domain for i in items})
    print(f"OK: {len(items)} items, {n_neg} negatives, domains={domains}, taxonomy {TAXONOMY_VERSION}")
    return 0


def cmd_score(a) -> int:
    items = load_items(a.data_dir)
    checkers = build_checkers(a.checkers.split(","))
    from .domains import get_domain
    order = list(get_domain(items[0].domain).failure_classes) if items else None
    print(format_table(score(items, checkers), order))
    return 0


def cmd_mutate(a) -> int:
    d = json.loads(pathlib.Path(a.item).read_text(encoding="utf-8"))
    for neg in propose(_item_from_dict(d)):
        print(json.dumps(
            {"class": neg.class_id, "artifact": neg.artifact, "note": neg.note,
             "label_status": neg.label_status}, ensure_ascii=False))
    return 0


def cmd_lint(a) -> int:
    from .domains import get_domain
    artifact = a.artifact if a.artifact is not None else sys.stdin.read()
    context = json.loads(pathlib.Path(a.context).read_text(encoding="utf-8")) if a.context else {}
    verdicts = get_domain(a.domain).structural(artifact, context)
    for v in verdicts:
        print(json.dumps({"linter": v.linter, "class": v.class_id, "evidence": v.evidence}, ensure_ascii=False))
    return 2 if (verdicts and a.strict) else 0


def cmd_domains(a) -> int:
    from .domains import REGISTRY as DOMAINS
    for name, dom in DOMAINS.items():
        print(f"{name}: {len(dom.failure_classes)} classes (semantic: {dom.semantic_class}) "
              f"-> {', '.join(dom.failure_classes)}")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="faithbench",
                                description="Domain-agnostic per-class faithfulness-negatives benchmark")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("domains", help="list registered domains").set_defaults(fn=cmd_domains)

    v = sub.add_parser("validate", help="schema-validate a data dir")
    v.add_argument("data_dir")
    v.set_defaults(fn=cmd_validate)

    s = sub.add_parser("score", help="per-class catch-rate table (domain auto-detected from data)")
    s.add_argument("data_dir")
    s.add_argument("--checkers", default="type_check,faithlint",
                   help=f"comma-separated, from {list(REGISTRY)}")
    s.set_defaults(fn=cmd_score)

    m = sub.add_parser("mutate", help="propose candidate negatives for an item (lean_math skeleton)")
    m.add_argument("item")
    m.set_defaults(fn=cmd_mutate)

    li = sub.add_parser("lint", help="run a domain's deterministic structural checks on an artifact")
    li.add_argument("artifact", nargs="?", default=None, help="artifact string; if omitted, read stdin")
    li.add_argument("--domain", default="lean_math", help="domain name (see `faithbench domains`)")
    li.add_argument("--context", default=None, help="path to a JSON context file (e.g. tool schemas)")
    li.add_argument("--strict", action="store_true", help="exit 2 if any check fires (default: fail-open exit 0)")
    li.set_defaults(fn=cmd_lint)

    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
