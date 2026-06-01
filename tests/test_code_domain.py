import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from faithbench.adapters import FaithLint
from faithbench.core import load_items
from faithbench.domains import get_domain
from faithbench.scoring import aggregate, score

CODE = pathlib.Path(__file__).resolve().parents[1] / "data" / "seed_code"


def test_code_domain_registered():
    dom = get_domain("code")
    assert dom.semantic_class == "intent_drift"
    assert len(dom.failure_classes) == 6


def test_structural_catches_five_of_six_by_execution():
    items = load_items(CODE)
    rep = score(items, [FaithLint()])
    classes = rep["classes"]
    for cid in ["syntax_error", "wrong_signature", "crashes", "contract_violation", "forbidden_construct"]:
        cell = classes[cid]["faithlint"]
        assert cell[0] == cell[1] and cell[1] > 0, f"{cid} should be caught deterministically"
    # the overfit/Goodhart case passes the visible tests -> structural is blind
    assert classes["intent_drift"]["faithlint"][0] == 0
    # the correct function is not falsely flagged
    assert rep["false_positive"]["faithlint"][0] == 0


def test_reference_diff_catches_intent_drift():
    dom = get_domain("code")
    item = load_items(CODE)[0]
    overfit = next(n for n in item.negatives if n.class_id == "intent_drift")
    # structural sees nothing wrong (it passes the visible tests)
    assert dom.structural(overfit.artifact, item.context) == []
    # but held-out probes vs the gold oracle expose the drift
    verdicts = dom.reference_diff(overfit.artifact, item.faithful, item.context)
    assert any(v.class_id == "intent_drift" for v in verdicts)


def test_aggregate_reach_is_83pct():
    agg = aggregate(score(load_items(CODE), [FaithLint()]))
    assert 0.8 <= agg["faithlint"] <= 0.9  # 5/6 deterministic
