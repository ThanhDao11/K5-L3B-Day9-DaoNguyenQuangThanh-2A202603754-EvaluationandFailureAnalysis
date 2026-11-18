"""M7 checks distinguish untrustworthy reports from honest regressions."""
import copy

import pytest

from lab9.gate import check, integrity_check

pytestmark = pytest.mark.student


@pytest.fixture
def baseline():
    return {"manifest": {"items": 2, "seeds": [11, 22], "eval_set_sha": "same"},
            "rows": [{"item_id": item, "seed": seed, "pass_rate": True, "slices": ["money"]}
                     for item in ("E-1", "E-2") for seed in (11, 22)],
            "metrics": {"pass_rate": 1.0}, "evaluator_failures": []}


@pytest.fixture
def spec():
    return {"eval_set_version": "v2", "seeds": [11, 22],
            "metrics": [{"id": "pass_rate", "blocking": True, "threshold": {"min": 0.8}}],
            "slices": [{"name": "money", "metric": "pass_rate", "min": 0.8,
                        "blocking": True, "no_significant_drop": True}]}


@pytest.mark.parametrize("damage", [
    "duplicate", "dropped", "changed_seed", "duplicate_seed_manifest", "changed_item_count",
    "row_none", "row_nan", "metric_nan", "metric_inf", "missing_metric",
    "evaluator_failure", "changed_slice", "inconsistent_slice", "forged_mean",
])
def test_damaged_reports_are_integrity_failures(baseline, spec, damage):
    pr = copy.deepcopy(baseline)
    if damage == "duplicate": pr["rows"][-1] = copy.deepcopy(pr["rows"][0])
    elif damage == "dropped": pr["rows"].pop()
    elif damage == "changed_seed": pr["rows"][0]["seed"] = 99
    elif damage == "duplicate_seed_manifest": pr["manifest"]["seeds"] = [11, 11]
    elif damage == "changed_item_count": pr["manifest"]["items"] = 1
    elif damage == "row_none": pr["rows"][0]["pass_rate"] = None
    elif damage == "row_nan": pr["rows"][0]["pass_rate"] = float("nan")
    elif damage == "metric_nan": pr["metrics"]["pass_rate"] = float("nan")
    elif damage == "metric_inf": pr["metrics"]["other"] = float("inf")
    elif damage == "missing_metric": pr["metrics"].pop("pass_rate")
    elif damage == "evaluator_failure": pr["evaluator_failures"] = ["grader crashed despite green metrics"]
    elif damage == "changed_slice":
        for row in pr["rows"]: row["slices"] = []
    elif damage == "inconsistent_slice": pr["rows"][0]["slices"] = []
    elif damage == "forged_mean": pr["rows"][0]["pass_rate"] = False
    blocked, lines = check(pr, baseline, spec)
    assert blocked == ["integrity"]
    assert lines and all("INTEGRITY" in line for line in lines)


def test_baseline_and_reordered_honest_report_are_valid(baseline, spec):
    pr = copy.deepcopy(baseline)
    pr["rows"].reverse()
    pr["manifest"]["seeds"].reverse()
    assert integrity_check(baseline, baseline, spec, spec) == []
    assert check(pr, baseline, spec, spec)[0] == []


def test_honest_regression_is_not_an_integrity_error(baseline, spec):
    pr = copy.deepcopy(baseline)
    pr["rows"][0]["pass_rate"] = False
    pr["metrics"]["pass_rate"] = 0.75
    assert integrity_check(pr, baseline, spec) == []
    assert "pass_rate" in check(pr, baseline, spec)[0]


@pytest.mark.parametrize("change", ["min", "max", "max_increase", "blocking", "drop_metric",
                                   "drop_threshold", "drop_ci", "drop_slice", "slice_min",
                                   "slice_blocking", "slice_ci", "slice_metric"])
def test_same_version_ratchet_rejects_weakening(baseline, spec, change):
    base_spec = copy.deepcopy(spec)
    base_spec["metrics"][0]["threshold"].update(max=1.0, max_increase=0.1, no_significant_drop=True)
    loose = copy.deepcopy(base_spec)
    metric, threshold = loose["metrics"][0], loose["metrics"][0]["threshold"]
    if change == "min": threshold["min"] = 0.5
    elif change == "max": threshold["max"] = 2.0
    elif change == "max_increase": threshold["max_increase"] = 0.5
    elif change == "blocking": metric["blocking"] = False
    elif change == "drop_metric": loose["metrics"] = []
    elif change == "drop_threshold": threshold.pop("min")
    elif change == "drop_ci": threshold.pop("no_significant_drop")
    elif change == "drop_slice": loose["slices"] = []
    elif change == "slice_min": loose["slices"][0]["min"] = 0.5
    elif change == "slice_blocking": loose["slices"][0]["blocking"] = False
    elif change == "slice_ci": loose["slices"][0].pop("no_significant_drop")
    elif change == "slice_metric": loose["slices"][0]["metric"] = "other"
    problems = integrity_check(baseline, baseline, loose, base_spec)
    assert any("ratchet" in p.lower() for p in problems)


def test_ratchet_accepts_stricter_limits(baseline, spec):
    stricter = copy.deepcopy(spec)
    stricter["metrics"][0]["threshold"]["min"] = 0.9
    stricter["slices"][0]["min"] = 0.9
    assert integrity_check(baseline, baseline, stricter, spec) == []
