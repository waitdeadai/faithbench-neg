"""Core data model + the (math) failure-class taxonomy.

faithbench is domain-pluggable: an *item* is one intent (a request / informal
problem), one faithful *artifact* (the correct rendering — a Lean statement, a
tool call, …), and a set of *negatives* (artifacts that pass the domain's cheap
validity gate but are unfaithful), each tagged with a failure class from the
item's domain taxonomy. See `faithbench.domains`.

`FAILURE_CLASSES` here is the `lean_math` taxonomy, kept at module level for
back-compat; other domains define their own.
"""
from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass, field
from typing import Any

TAXONOMY_VERSION = "0.1.0"

FAILURE_CLASSES: dict[str, str] = {
    "vacuous": "Trivially true — goal is `True`, or a hypothesis is contradictory — so any proof is meaningless.",
    "answer_leaking": "The to-be-determined value is baked into the statement, so it no longer asks what the problem asks.",
    "quantifier_swapped": "Quantifier kind/order wrong (∀/∃ swapped, bounded vs unbounded, reordered binders).",
    "premise_mistranslated": "A hypothesis is dropped, weakened, strengthened, or altered vs the informal problem.",
    "conclusion_as_axiom": "The goal is asserted as a hypothesis (or otherwise assumed), making the theorem circular.",
    "domain_type_mismatch": "Wrong type/domain or boundary (ℕ vs ℤ, < vs ≤, off-by-one bounds, …).",
}

VALID_LABEL = {"UNVERIFIED_EXAMPLE", "human_verified", "machine_verified", "machine_proposed"}

DEFAULT_DOMAIN = "lean_math"


@dataclass
class Negative:
    class_id: str
    artifact: str
    note: str = ""
    label_status: str = "UNVERIFIED_EXAMPLE"

    @property
    def statement(self) -> str:  # back-compat alias
        return self.artifact


@dataclass
class Item:
    id: str
    intent: str
    faithful: str
    negatives: list[Negative] = field(default_factory=list)
    domain: str = DEFAULT_DOMAIN
    context: dict[str, Any] = field(default_factory=dict)
    source: dict[str, Any] = field(default_factory=dict)
    label_status: str = "UNVERIFIED_EXAMPLE"

    @property
    def nl_problem(self) -> str:  # back-compat alias
        return self.intent

    @property
    def faithful_statement(self) -> str:  # back-compat alias
        return self.faithful


def _domain_classes(domain: str) -> dict[str, str]:
    from .domains import get_domain  # late import to avoid a cycle
    return get_domain(domain).failure_classes


def validate_item(d: dict) -> list[str]:
    """Return a list of human-readable problems; empty list means valid."""
    errs: list[str] = []
    domain = d.get("domain", DEFAULT_DOMAIN)
    try:
        classes = _domain_classes(domain)
    except Exception as exc:  # unknown domain
        return [f"unknown domain {domain!r}: {exc}"]
    intent_ok = "intent" in d or "nl_problem" in d
    faithful_ok = "faithful" in d or "faithful_statement" in d
    if "id" not in d:
        errs.append("missing required field: id")
    if not intent_ok:
        errs.append("missing required field: intent (or nl_problem)")
    if not faithful_ok:
        errs.append("missing required field: faithful (or faithful_statement)")
    negs = d.get("negatives")
    if not isinstance(negs, list):
        errs.append("negatives must be a list")
    else:
        for i, n in enumerate(negs):
            if n.get("class") not in classes:
                errs.append(f"negatives[{i}]: class {n.get('class')!r} not in {domain} taxonomy ({', '.join(classes)})")
            if "artifact" not in n and "statement" not in n:
                errs.append(f"negatives[{i}]: missing 'artifact' (or 'statement')")
    if d.get("label_status") and d["label_status"] not in VALID_LABEL:
        errs.append(f"bad label_status {d['label_status']!r}")
    return errs


def _item_from_dict(d: dict) -> Item:
    return Item(
        id=d["id"],
        intent=d.get("intent", d.get("nl_problem", "")),
        faithful=d.get("faithful", d.get("faithful_statement", "")),
        negatives=[
            Negative(class_id=n["class"], artifact=n.get("artifact", n.get("statement", "")),
                     note=n.get("note", ""), label_status=n.get("label_status", "UNVERIFIED_EXAMPLE"))
            for n in d.get("negatives", [])
        ],
        domain=d.get("domain", DEFAULT_DOMAIN),
        context=d.get("context", {}),
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
