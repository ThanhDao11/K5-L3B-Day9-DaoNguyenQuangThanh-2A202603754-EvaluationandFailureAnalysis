"""M5 slice floors, paired CIs and negative controls."""
import copy

import pytest

from lab9.gate import slice_check

pytestmark = pytest.mark.student


def report(values, tag="money_movement"):
    return {"rows": [{"item_id": f"E-{i}", "seed": seed, "slices": [tag],
                      "pass_rate": value} for i, value in enumerate(values) for seed in (11, 22)]}


def spec(**overrides):
    return {"bootstrap": {"n_resamples": 1000, "rng": 2027, "confidence": 0.95},
            "slices": [{"name": "money_movement", "metric": "pass_rate", "min": 0.8,
                        "no_significant_drop": True, "blocking": True, **overrides}]}


def test_significant_slice_drop_blocks_even_above_floor():
    blocked, lines = slice_check(report([0.9] * 4), report([1.0] * 4), spec())
    assert blocked == ["slice:money_movement/pass_rate"]
    assert any("CI" in line for line in lines)


def test_slice_pairs_by_item_id_not_row_order():
    base = report([0.6, 0.8, 1.0, 1.0])
    pr = copy.deepcopy(base)
    pr["rows"].reverse()
    assert slice_check(pr, base, spec())[0] == []


def test_nonblocking_slice_warns_without_blocking():
    blocked, lines = slice_check(report([0.0] * 4), report([1.0] * 4), spec(blocking=False))
    assert blocked == []
    assert any("warn" in line for line in lines)


def test_slice_missing_from_pr_cannot_silently_pass():
    pr = report([1.0] * 4, tag="other")
    assert slice_check(pr, report([1.0] * 4), spec())[0] == ["slice:money_movement/pass_rate"]


def test_slice_floor_weights_items_equally():
    pr = report([0.0, 1.0])
    # Unequal seed counts must not let the second item dominate the slice mean.
    pr["rows"] += [dict(pr["rows"][-1], seed=i) for i in range(100, 110)]
    assert slice_check(pr, report([1.0, 1.0]), spec(no_significant_drop=False))[0]
