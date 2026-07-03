#!/usr/bin/env python3
"""render.py — turn results/results.csv into the markdown tables used in
benchmarks/README.md.

Usage:
    python3 render.py results/results.csv > snapshot.md

Reads matrix.yaml (in the same directory as this script) for prices, and
computes per-(model, task):
    Cost  — mean of (prompt_tokens * in_price + completion_tokens * out_price)
    p50 / p95 latency — over the ok repeats
    Runs  — ok/total (quality pass/fail stays a human+rubric judgment;
            this script reports run health, not quality)

Skipped cells (skip_if_context_lt) are listed explicitly so the narrative
can say who sat out.
"""
from __future__ import annotations

import csv
import pathlib
import statistics
import sys

import yaml

HERE = pathlib.Path(__file__).resolve().parent


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return float("nan")
    values = sorted(values)
    k = (len(values) - 1) * pct
    lo, hi = int(k), min(int(k) + 1, len(values) - 1)
    return values[lo] + (values[hi] - values[lo]) * (k - lo)


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2

    matrix = yaml.safe_load((HERE / "matrix.yaml").read_text())
    prices = {
        m["id"]: (m["price_per_mtok_in"], m["price_per_mtok_out"])
        for m in matrix["models"]
    }
    task_ids = [t["id"] for t in matrix["tasks"]]

    rows: dict[tuple[str, str], list[dict]] = {}
    skipped: list[tuple[str, str]] = []
    with open(sys.argv[1], newline="") as f:
        for row in csv.DictReader(f):
            key = (row["model"], row["task"])
            if row["status"] == "skipped_context":
                skipped.append(key)
            else:
                rows.setdefault(key, []).append(row)

    print(f"## Results snapshot — rendered from {sys.argv[1]}\n")

    for task in task_ids:
        print(f"### {task}\n")
        print("| Model | Cost | p50 | p95 | Runs ok |")
        print("|---|---:|---:|---:|---:|")
        for model in prices:
            key = (model, task)
            if key in skipped:
                continue
            runs = rows.get(key, [])
            if not runs:
                continue
            ok = [r for r in runs if r["status"] == "ok"]
            lat = [float(r["latency_s"]) for r in ok]
            in_p, out_p = prices[model]
            costs = [
                int(r["prompt_tokens"]) / 1e6 * in_p
                + int(r["completion_tokens"]) / 1e6 * out_p
                for r in ok
                if r["prompt_tokens"] and r["completion_tokens"]
            ]
            cost = f"${statistics.mean(costs):.4f}" if costs else "—"
            p50 = f"{percentile(lat, 0.50):.1f}s" if lat else "—"
            p95 = f"{percentile(lat, 0.95):.1f}s" if lat else "—"
            print(f"| {model} | {cost} | {p50} | {p95} | {len(ok)}/{len(runs)} |")
        excluded = sorted(m for (m, t) in skipped if t == task)
        if excluded:
            print(f"\n_Excluded by `skip_if_context_lt`: {', '.join(excluded)}_")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
