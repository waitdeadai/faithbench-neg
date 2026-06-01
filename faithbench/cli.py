"""faithbench-neg command line."""
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
    print(f"OK: {len(items)} items, {n_neg} negatives, taxonomy {TAXONOMY_VERSION}")
    return 0


def cmd_score(a) -> int:
    items = load_items(a.data_dir)
    checkers = build_checkers(a.checkers.split(","))
    print(format_table(score(items, checkers)))
    return 0


def cmd_mutate(a) -> int:
    d = json.loads(pathlib.Path(a.item).read_text(encoding="utf-8"))
    for neg in propose(_item_from_dict(d)):
        print(json.dumps(
            {"class": neg.class_id, "statement": neg.statement, "note": neg.note,
             "label_status": neg.label_status}, ensure_ascii=False))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="faithbench",
        description="Per-class faithfulness-negatives benchmark for Lean 4 statement autoformalization")
    sub = p.add_subparsers(dest="cmd", required=True)

    v = sub.add_parser("validate", help="schema-validate a data dir")
    v.add_argument("data_dir")
    v.set_defaults(fn=cmd_validate)

    s = sub.add_parser("score", help="print the per-class catch-rate table")
    s.add_argument("data_dir")
    s.add_argument("--checkers", default="type_check,mock_judge",
                   help=f"comma-separated, from {list(REGISTRY)}")
    s.set_defaults(fn=cmd_score)

    m = sub.add_parser("mutate", help="propose candidate negatives for an item (skeleton)")
    m.add_argument("item")
    m.set_defaults(fn=cmd_mutate)

    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
