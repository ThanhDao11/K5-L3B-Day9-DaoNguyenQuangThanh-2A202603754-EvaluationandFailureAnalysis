"""CI gate: compare a PR eval report with the main-branch baseline using the metric spec.

    python -m lab9.gate --pr reports/eval_workflow.json --baseline reports/baseline_v1.json

exit 0 = merge, exit 1 = blocked. Safety metrics: max 0, no averaging away.
Capability metrics: meet the floor AND the paired CI of (PR - main) is not entirely below 0.
Thresholds may only get stricter on the same eval-set version (ratchet).
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from lab8.console import utf8_stdio
from lab9 import stats
from lab9.eval import SPEC, load_spec, per_item
from lab9.graders import GRADERS


def _finite(value) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(value)


def _report_integrity(report: dict, spec: dict, label: str) -> tuple[list[str], dict]:
    """Validate the report in memory; do not trust its claimed aggregate scores."""
    problems, index = [], {}
    manifest, rows, metrics = report.get("manifest"), report.get("rows"), report.get("metrics")
    if not isinstance(manifest, dict) or not isinstance(rows, list) or not isinstance(metrics, dict):
        return [f"{label}: missing manifest, rows or metrics"], index
    items, seeds = manifest.get("items"), manifest.get("seeds")
    if (isinstance(items, bool) or not isinstance(items, int) or items < 1 or
            not isinstance(seeds, list) or not seeds or
            any(isinstance(s, bool) or not isinstance(s, int) for s in seeds)):
        return [f"{label}: invalid item count or seeds"], index
    if len(set(seeds)) != len(seeds):
        problems.append(f"{label}: duplicated manifest seeds")
    if len(rows) != items * len(seeds):
        problems.append(f"{label}: row count differs from items x seeds")
    if "seeds" in spec and set(seeds) != set(spec["seeds"]):
        problems.append(f"{label}: seed set differs from spec")
    for field in ("metric_spec_version", "eval_set_version"):
        if field in manifest and field in spec and manifest[field] != spec[field]:
            problems.append(f"{label}: {field} differs from spec")
    if report.get("evaluator_failures") != []:
        problems.append(f"{label}: evaluator_failures missing or non-empty")
    if any(not _finite(value) for value in metrics.values()):
        problems.append(f"{label}: non-finite or missing aggregate metric")
    for metric in spec.get("metrics", []):
        if metric["id"] not in metrics:
            problems.append(f"{label}: missing metric {metric['id']}")

    slices_by_item = {}
    for row in rows:
        if (not isinstance(row, dict) or not isinstance(row.get("item_id"), str) or
                isinstance(row.get("seed"), bool) or not isinstance(row.get("seed"), int)):
            problems.append(f"{label}: invalid item/seed row")
            continue
        key = (row["item_id"], row["seed"])
        if key in index:
            problems.append(f"{label}: duplicate item/seed {key}")
        tags = row.get("slices", [])
        if not isinstance(tags, list) or any(not isinstance(tag, str) for tag in tags):
            problems.append(f"{label}: invalid slice tags for {key}")
            tags = []
        if len(set(tags)) != len(tags):
            problems.append(f"{label}: duplicate slice tags for {key}")
        tag_set = frozenset(tags)
        if row["item_id"] in slices_by_item and slices_by_item[row["item_id"]] != tag_set:
            problems.append(f"{label}: inconsistent slice tags across seeds")
        slices_by_item[row["item_id"]] = tag_set
        index[key] = tag_set
        if "cost" in row and (not _finite(row["cost"]) or row["cost"] < 0):
            problems.append(f"{label}: invalid row cost")
    item_ids = {key[0] for key in index}
    if len(item_ids) != items or set(index) != {(item, seed) for item in item_ids for seed in seeds}:
        problems.append(f"{label}: incomplete item x seed coverage")
    if any(not isinstance(row, dict) for row in rows):
        return problems, index

    for metric in spec.get("metrics", []):
        mid = metric["id"]
        if mid not in GRADERS and not any(mid in row for row in rows):
            continue  # Derived metrics such as pass_hat_5 have no per-row column.
        values = [row.get(mid) for row in rows]
        if not values or any(not _finite(v) or not 0 <= v <= 1 for v in values):
            problems.append(f"{label}: missing/invalid graded row value for {mid}")
            continue
        expected = sum(values) if mid in ("secret_leak", "approval_bypass") else round(sum(values) / len(values), 4)
        if _finite(metrics.get(mid)) and abs(metrics[mid] - expected) > 0.00005:
            problems.append(f"{label}: aggregate {mid} inconsistent with rows")

    if rows and all(_finite(row.get("pass_rate")) and 0 <= row["pass_rate"] <= 1 for row in rows):
        by_item = {}
        for row in rows:
            if isinstance(row.get("item_id"), str):
                by_item.setdefault(row["item_id"], []).append(bool(row["pass_rate"]))
        derived = {}
        if by_item:
            derived["pass_5"] = round(sum(all(v) for v in by_item.values()) / len(by_item), 4)
            for k in spec.get("pass_k", []):
                for prefix, fn in (("pass_at", stats.pass_at_k), ("pass_hat", stats.pass_hat_k)):
                    mid = f"{prefix}_{k}"
                    if min(map(len, by_item.values())) < k:
                        problems.append(f"{label}: too few trials for {mid}")
                    else:
                        derived[mid] = round(sum(fn(len(v), sum(v), k) for v in by_item.values()) / len(by_item), 4)
        for mid, expected in derived.items():
            if mid in metrics and _finite(metrics[mid]) and abs(metrics[mid] - expected) > 0.00005:
                problems.append(f"{label}: aggregate {mid} inconsistent with rows")
    return problems, index


def _ratchet_check(spec: dict, base_spec: dict) -> list[str]:
    if spec.get("eval_set_version") != base_spec.get("eval_set_version"):
        return []  # A new eval set requires its own baseline and spec.
    problems = []
    for section in ("metrics", "slices"):
        def key(entry):
            return entry["id"] if section == "metrics" else (entry["name"], entry["metric"])

        current_entries, old_entries = spec.get(section, []), base_spec.get(section, [])
        current = {key(entry): entry for entry in current_entries}
        old = {key(entry): entry for entry in old_entries}
        if len(current) != len(current_entries) or len(old) != len(old_entries):
            problems.append(f"ratchet: duplicate {section} definitions")
        for identifier, before in old.items():
            prefix = f"ratchet: {section} {identifier}"
            after = current.get(identifier)
            if after is None:
                problems.append(f"{prefix} removed or changed identity")
                continue
            if before.get("blocking") and after.get("blocking") is not True:
                problems.append(f"{prefix} blocking removed")
            old_threshold = before.get("threshold", {}) if section == "metrics" else before
            new_threshold = after.get("threshold", {}) if section == "metrics" else after
            if old_threshold.get("no_significant_drop") and new_threshold.get("no_significant_drop") is not True:
                problems.append(f"{prefix} no_significant_drop removed")
            for limit in ("min", "max", "max_increase"):
                if limit not in old_threshold:
                    continue
                previous, value = old_threshold[limit], new_threshold.get(limit)
                if not _finite(previous) or not _finite(value):
                    problems.append(f"{prefix} {limit} missing or non-finite")
                elif (limit == "min" and value < previous) or (limit != "min" and value > previous):
                    problems.append(f"{prefix} {limit} loosened ({previous} -> {value})")
    return problems


def integrity_check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> list[str]:
    """M7 (Expert): refuse to compare reports that cannot be trusted. Return a list of problems
    (empty = trustworthy). A gate that passes a broken report is worse than no gate.
    Must catch at least:
      - any metric value in pr["metrics"] that is NaN or inf
      - len(pr["rows"]) != manifest items x len(manifest seeds)   (dropped / duplicated rows)
      - the (item_id, seed) set of PR differs from the baseline's (cherry-picked seeds/items)
      - pr["evaluator_failures"] non-empty, or a row whose value for a graded spec metric is
        None (a crashed grader silently scores as "missing" and drops out of the mean)
      - base_spec given and a threshold in spec is LOOSER than in base_spec for the same
        eval-set version (ratchet: max may not rise, min may not fall, a blocking metric may
        not become non-blocking, a metric may not disappear; the same for spec["slices"],
        including dropping no_significant_drop)
      - an item's slice tags in PR rows differ from the baseline's (relabelling an item out of a
        slice hides its regression from the slice gate)"""
    problems, pr_index = _report_integrity(pr, spec, "PR")
    base_problems, base_index = _report_integrity(base, base_spec or spec, "baseline")
    problems += base_problems
    if pr_index.keys() != base_index.keys():
        problems.append("PR item/seed set differs from baseline")
    if any(pr_index[key] != base_index[key] for key in pr_index.keys() & base_index.keys()):
        problems.append("PR slice tags differ from baseline")
    if base_spec is not None:
        problems += _ratchet_check(spec, base_spec)
    return problems


def slice_check(pr: dict, base: dict, spec: dict) -> tuple[list[str], list[str]]:
    """M5 (Advanced): an average can hide a regression on a small, important slice.
    For each entry of spec["slices"] ({"name", "metric", "min"?, "no_significant_drop"?, "blocking"}):
      - value = mean of per_item(pr, metric, slice_name=name)
      - fail if below "min", or if no_significant_drop and the paired CI over the slice's items
        lies entirely below 0
    Return (blocked ids like "slice:money_movement/pass_rate", report lines)."""
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for entry in spec.get("slices", []):
        name, metric = entry["name"], entry["metric"]
        identifier = f"slice:{name}/{metric}"
        a, b = per_item(pr, metric, slice_name=name), per_item(base, metric, slice_name=name)
        reasons, note = [], ""
        value = sum(a.values()) / len(a) if a else None
        if not a or not b or a.keys() != b.keys():
            reasons.append("missing or mismatched slice items")
        else:
            if "min" in entry and value < entry["min"]:
                reasons.append(f"below floor {entry['min']}")
            if entry.get("no_significant_drop"):
                keys = sorted(a)
                left, right = [a[k] for k in keys], [b[k] for k in keys]
                if len(keys) < 2 and left != right:
                    reasons.append("insufficient paired items for CI")
                else:
                    d, lo, hi = stats.paired_bootstrap(
                        left, right, n_resamples=bs.get("n_resamples", 1000),
                        rng=bs.get("rng", 2027), confidence=bs.get("confidence", 0.95))
                    note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
                    if hi < 0:
                        reasons.append("significant drop")
        if reasons and entry.get("blocking"):
            blocked.append(identifier)
        verdict = ("BLOCK" if entry.get("blocking") else "warn") if reasons else "ok"
        lines.append(f"  {identifier:<40} {value!s:<8} {note} {verdict} {'; '.join(reasons)}")
    return blocked, lines


def check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> tuple[list[str], list[str]]:
    if pr["manifest"]["eval_set_sha"] != base["manifest"]["eval_set_sha"]:
        return ["eval_set_sha"], ["  EVAL SET differs from the baseline's: re-run the baseline on the same eval set"]
    problems = integrity_check(pr, base, spec, base_spec)
    if problems:
        return ["integrity"], [f"  INTEGRITY {p}" for p in problems]
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for m in spec["metrics"]:
        mid, th, val = m["id"], m.get("threshold", {}), pr["metrics"].get(m["id"])
        verdict, note = "ok", ""
        if val is None:
            verdict = "missing"
        elif "max" in th and val > th["max"]:
            verdict = "fail"
        elif "min" in th and val < th["min"]:
            verdict = "fail"
        elif "max_increase" in th and base["metrics"].get(mid):
            if val > base["metrics"][mid] * (1 + th["max_increase"]):
                verdict = "fail"
        if th.get("no_significant_drop") and val is not None:
            a, b = per_item(pr, mid), per_item(base, mid)
            keys = sorted(set(a) & set(b))
            d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                                               n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027))
            note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
            if hi < 0:
                verdict = "fail"
        if verdict != "ok" and m.get("blocking"):
            blocked.append(mid)
        label = {"ok": "ok", "missing": "MISSING"}.get(verdict, "BLOCK" if m.get("blocking") else "warn")
        lines.append(f"  {mid:<22} {val!s:<8} {json.dumps(th):<40} {note:<28} {label}")
    if spec.get("slices"):
        sb, sl = slice_check(pr, base, spec)
        blocked += sb
        lines += sl
    return blocked, lines


def main(argv: list[str] | None = None) -> int:
    utf8_stdio()
    ap = argparse.ArgumentParser(prog="lab9.gate")
    ap.add_argument("--pr", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--spec", default=str(SPEC))
    ap.add_argument("--base-spec", help="metric spec on main, for the ratchet check (M7)")
    args = ap.parse_args(argv)
    pr = json.loads(Path(args.pr).read_text(encoding="utf-8"))
    base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    base_spec = load_spec(Path(args.base_spec)) if args.base_spec else None
    blocked, lines = check(pr, base, load_spec(Path(args.spec)), base_spec)
    print(f"gate: PR {pr['run_id']} vs main {base['run_id']} · eval set {pr['manifest']['eval_set_sha']}")
    print("\n".join(lines))
    if blocked:
        print(f"exit 1 — blocked: {', '.join(blocked)}")
        return 1
    print("exit 0 — merge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
