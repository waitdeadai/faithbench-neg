import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from faithbench.adapters import MockJudge, TypeCheckOnly
from faithbench.core import FAILURE_CLASSES, load_items
from faithbench.scoring import aggregate, score

DATA = pathlib.Path(__file__).resolve().parents[1] / "data" / "seed"


def test_seed_loads_and_validates():
    items = load_items(DATA)
    assert len(items) >= 2
    for it in items:
        assert it.negatives
        for n in it.negatives:
            assert n.class_id in FAILURE_CLASSES


def test_type_check_only_is_blind():
    # Every negative type-checks by construction, so a compile-only gate must
    # catch nothing. This is the headline blind spot the benchmark exists to show.
    rep = score(load_items(DATA), [TypeCheckOnly()])
    assert aggregate(rep)["type_check"] == 0.0


def test_mock_judge_has_per_class_divergence():
    rep = score(load_items(DATA), [MockJudge()])
    classes = rep["classes"]
    vac = classes["vacuous"]["mock_judge"]
    assert vac[0] == vac[1] and vac[1] > 0  # catches every vacuous negative
    missed = [cid for cid, row in classes.items()
              if cid != "vacuous" and row["mock_judge"][0] == 0]
    assert missed, "expected mock_judge to have >=1 per-class blind spot (the point)"


def test_no_cry_wolf_on_faithful_for_baselines():
    rep = score(load_items(DATA), [TypeCheckOnly(), MockJudge()])
    fp = rep["false_positive"]
    assert fp["type_check"][0] == 0
    assert fp["mock_judge"][0] == 0
