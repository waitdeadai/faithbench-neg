"""Per-failure-class catch-rate scoring — domain-agnostic.

For each checker, per failure class, report the fraction of KNOWN-unfaithful
negatives it correctly flags (catch-rate), plus a false-positive ('cry-wolf')
rate on the faithful artifacts. The headline is *divergence*: checkers with
similar aggregate numbers can have very different per-class blind spots.
"""
from __future__ import annotations

from .core import Item


def score(items: list[Item], checkers) -> dict:
    classes: dict[str, dict[str, list[int]]] = {}     # class -> checker -> [catches, total]
    fp: dict[str, list[int]] = {c.name: [0, 0] for c in checkers}
    for it in items:
        for ch in checkers:
            fp[ch.name][1] += 1
            if not ch.classify(it, it.faithful):
                fp[ch.name][0] += 1  # flagged a faithful artifact -> cry wolf
        for neg in it.negatives:
            row = classes.setdefault(neg.class_id, {})
            for ch in checkers:
                cell = row.setdefault(ch.name, [0, 0])
                cell[1] += 1
                if not ch.classify(it, neg.artifact):
                    cell[0] += 1  # correctly flagged unfaithful -> catch
    return {"classes": classes, "false_positive": fp, "checkers": [c.name for c in checkers]}


def _rate(cell: list[int]) -> float:
    c, t = cell
    return (c / t) if t else float("nan")


def aggregate(report: dict) -> dict:
    agg = {}
    for name in report["checkers"]:
        c = t = 0
        for row in report["classes"].values():
            if name in row:
                c += row[name][0]
                t += row[name][1]
        agg[name] = (c / t) if t else float("nan")
    return agg


def format_table(report: dict, class_order: list[str] | None = None) -> str:
    names = report["checkers"]
    classes = report["classes"]
    order = class_order or list(classes)
    label_w = max([len(k) for k in classes] + [len("cry-wolf (FP on faithful)")]) + 2
    head = "failure class".ljust(label_w) + "".join(f"{n:>14}" for n in names) + f"{'n':>6}"
    lines = [head, "-" * len(head)]
    for cid in order:
        row = classes.get(cid)
        if not row:
            continue
        n = max((row[nm][1] for nm in names if nm in row), default=0)
        cells = "".join(
            (f"{_rate(row[nm]) * 100:>13.0f}%" if nm in row else f"{'-':>14}") for nm in names
        )
        lines.append(cid.ljust(label_w) + cells + f"{n:>6}")
    agg = aggregate(report)
    fp = report["false_positive"]
    lines.append("-" * len(head))
    lines.append("AGGREGATE catch-rate".ljust(label_w) + "".join(f"{agg[n] * 100:>13.0f}%" for n in names))
    lines.append("cry-wolf (FP on faithful)".ljust(label_w) + "".join(f"{_rate(fp[n]) * 100:>13.0f}%" for n in names))
    return "\n".join(lines)
