"""LLMJudge adapter: contract + the layering payoff.

We can't run a real model here (no API key), so we inject a mock judge callable
to verify (a) the adapter plumbing/parsing and (b) the key claim: a semantic judge
catches `intent_drift` — the class the deterministic structural gate is BLIND to.
Real-model accuracy is the open empirical question (the literature puts judges far
below perfect); this test proves the *wiring and the layering*, not judge quality.
"""
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from faithbench.adapters import FaithLint, LLMJudge
from faithbench.core import load_items
from faithbench.scoring import score

CODE = pathlib.Path(__file__).resolve().parents[1] / "data" / "seed_code"


def _item_with_drift():
    for it in load_items(CODE):
        for n in it.negatives:
            if n.class_id == "intent_drift":
                return it, n
    raise AssertionError("no intent_drift negative in seed_code")


def test_adapter_parsing_contract():
    item, _ = _item_with_drift()
    assert LLMJudge(call=lambda p: "FAITHFUL").classify(item, item.faithful) is True
    assert LLMJudge(call=lambda p: "UNFAITHFUL").classify(item, item.faithful) is False
    # default-faithful: judge must affirmatively object
    assert LLMJudge(call=lambda p: "not sure").classify(item, item.faithful) is True


def test_raises_when_no_judge_configured(monkeypatch):
    monkeypatch.delenv("FAITHBENCH_JUDGE_CMD", raising=False)
    with pytest.raises(NotImplementedError):
        LLMJudge().classify(*_item_with_drift()[:1], "x")


def test_judge_catches_intent_drift_that_structural_misses():
    item, drift = _item_with_drift()
    faithful = item.faithful
    # mock oracle: faithful iff the candidate matches the known-good artifact.
    oracle = (lambda prompt: "FAITHFUL" if faithful.strip() in prompt else "UNFAITHFUL")

    # structural gate is BLIND to intent_drift (it is schema/exec-valid)
    assert FaithLint().classify(item, drift.artifact) is True
    # the semantic judge CATCHES it
    assert LLMJudge(call=oracle).classify(item, drift.artifact) is False
    # and does not cry-wolf on the faithful artifact
    assert LLMJudge(call=oracle).classify(item, faithful) is True


def test_layered_score_table():
    items = load_items(CODE)
    faithfuls = {it.id: it.faithful for it in items}

    def oracle(prompt):
        return "FAITHFUL" if any(f.strip() in prompt for f in faithfuls.values()) else "UNFAITHFUL"

    rep = score(items, [FaithLint(), LLMJudge(call=oracle)])
    drift = rep["classes"]["intent_drift"]
    # the whole point: structural 0% on intent_drift, judge layer recovers it
    assert drift["faithlint"][0] == 0
    assert drift["llm_judge"][0] == drift["llm_judge"][1] and drift["llm_judge"][1] > 0
