import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from faithbench.adapters import FaithLint
from faithbench.core import load_items
from faithbench.domains import REGISTRY, get_domain
from faithbench.scoring import aggregate, score

TC = pathlib.Path(__file__).resolve().parents[1] / "data" / "seed_tool_call"


def test_domains_registered():
    assert {"lean_math", "tool_call"} <= set(REGISTRY)
    assert get_domain("tool_call").semantic_class == "intent_drift"
    assert get_domain("lean_math").semantic_class == "answer_leaking"


def test_tool_call_structural_catches_five_of_six():
    items = load_items(TC)
    rep = score(items, [FaithLint()])
    classes = rep["classes"]
    structural = ["wrong_tool", "missing_required_arg", "wrong_arg_type", "unexpected_arg", "enum_violation"]
    for cid in structural:
        cell = classes[cid]["faithlint"]
        assert cell[0] == cell[1] and cell[1] > 0, f"{cid} should be 100% caught"
    # the irreducibly-semantic class is blind to the deterministic gate
    drift = classes["intent_drift"]["faithlint"]
    assert drift[0] == 0, "intent_drift must NOT be caught structurally"
    # and no cry-wolf on the faithful call
    assert rep["false_positive"]["faithlint"][0] == 0


def test_tool_call_reference_diff_catches_intent_drift():
    dom = get_domain("tool_call")
    faithful = {"tool": "get_weather", "arguments": {"location": "Paris", "unit": "celsius"}}
    drift = {"tool": "get_weather", "arguments": {"location": "London", "unit": "celsius"}}
    verdicts = dom.reference_diff(drift, faithful, {})
    assert any(v.class_id == "intent_drift" for v in verdicts)
    # structural alone sees nothing wrong (it is schema-valid)
    ctx = load_items(TC)[0].context
    assert dom.structural(drift, ctx) == []


def test_tool_call_aggregate_reach():
    items = load_items(TC)
    agg = aggregate(score(items, [FaithLint()]))
    # 5 of 6 classes caught deterministically -> ~83% aggregate on this seed
    assert 0.8 <= agg["faithlint"] <= 0.9
