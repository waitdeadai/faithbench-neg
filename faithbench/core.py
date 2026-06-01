"""Core data model + the frozen failure-class taxonomy.

A benchmark *item* is one informal problem, one human-verified FAITHFUL Lean 4
statement, and a set of *negatives*: plausible Lean statements that type-check
but are unfaithful renderings of the problem, each tagged with the failure class
it exemplifies. The taxonomy is the defensible core of this project — it is
versioned and changes are breaking.
"""
from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass, field
from typing import Any

TAXONOMY_VERSION = "0.1.0"

# Ordered: the table renders classes in this order.
FAILURE_CLASSES: dict[str, str] = {
    "vacuous": "Trivially true — goal is `True`, or a hypothesis is contradictory — so any proof is meaningless.",
    "answer_leaking": "The to-be-determined value is baked into the statement, so it no longer asks what the problem asks.",
    "quantifier_swapped": "Quantifier kind/order wrong (∀/∃ swapped, bounded vs unbounded, reordered binders).",
    "premise_mistranslated": "A hypothesis is dropped, weakened, strengthened, or altered vs the informal problem.",
    "conclusion_as_axiom": "The goal is asserted as a hypothesis (or otherwise assumed), making the theorem circular.",
    "domain_type_mismatch": "Wrong type/domain or boundary (ℕ vs ℤ, < vs ≤, off-by-one bounds, …).",
}

VALID_LABEL = {"UNVERIFIED_EXAMPLE", "human_verified", "machine_proposed"}


@dataclass
class Negative:
    class_id: str
    statement: str
    note: str = ""
    label_status: str = "UNVERIFIED_EXAMPLE"


@dataclass
class Item:
    id: str
    nl_problem: str
    faithful_statement: str
    negatives: list[Negative] = field(default_factory=list)
    source: dict[str, Any] = field(default_factory=dict)
    label_status: str = "UNVERIFIED_EXAMPLE"


def validate_item(d: dict) -> list[str]:
    """Return a list of human-readable problems; empty list means valid."""
    errs: list[str] = []
    for k in ("id", "nl_problem", "faithful_statement", "negatives"):
        if k not in d:
            errs.append(f"missing required field: {k}")
    negs = d.get("negatives")
    if negs is not None:
        if not isinstance(negs, list):
            errs.append("negatives must be a list")
        else:
            for i, n in enumerate(negs):
                if n.get("class") not in FAILURE_CLASSES:
                    errs.append(f"negatives[{i}]: unknown class {n.get('class')!r} "
                                f"(taxonomy {TAXONOMY_VERSION}: {', '.join(FAILURE_CLASSES)})")
                if "statement" not in n:
                    errs.append(f"negatives[{i}]: missing 'statement'")
    if d.get("label_status") and d["label_status"] not in VALID_LABEL:
        errs.append(f"bad label_status {d['label_status']!r} (allowed: {', '.join(VALID_LABEL)})")
    return errs


def _item_from_dict(d: dict) -> Item:
    return Item(
        id=d["id"],
        nl_problem=d["nl_problem"],
        faithful_statement=d["faithful_statement"],
        negatives=[
            Negative(class_id=n["class"], statement=n["statement"],
                     note=n.get("note", ""), label_status=n.get("label_status", "UNVERIFIED_EXAMPLE"))
            for n in d.get("negatives", [])
        ],
        source=d.get("source", {}),
        label_status=d.get("label_status", "UNVERIFIED_EXAMPLE"),
    )


def load_items(data_dir: str | pathlib.Path) -> list[Item]:
    items: list[Item] = []
    for p in sorted(pathlib.Path(data_dir).glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        errs = validate_item(d)
        if errs:
            raise ValueError(f"{p.name}: " + "; ".join(errs))
        items.append(_item_from_dict(d))
    return items
