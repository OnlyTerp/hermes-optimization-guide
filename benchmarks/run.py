#!/usr/bin/env python3
"""run.py — cross-platform, dependency-light benchmark harness.

Same contract as run.sh (which targets Linux/macOS) but runs anywhere Python
runs, with no bash, no `date`, no shell-CSV quirks. This is the canonical
harness for producing the dated results snapshots.

Usage:
  HERMES_BENCH_API_KEY=*** python run.py                      # all models x all tasks
  HERMES_BENCH_API_KEY=*** python run.py --model Kimi-K3       # one model
  HERMES_BENCH_API_KEY=*** python run.py --task T1_triage       # one task

Env:
  HERMES_BENCH_BASE_URL    default https://openrouter.ai/api/v1
  HERMES_BENCH_API_KEY     required
  HERMES_BENCH_MATRIX      default matrix.yaml
  HERMES_BENCH_OUT         default results/results.csv

Output: one CSV row per (model, task, repeat) with wall-clock latency and the
token counts from the response `usage` field. Render README tables from it:
  python render.py results/2026-08-22-wafer.csv matrix-wafer.yaml

Requires only the Python stdlib + PyYAML (for the matrix file).
"""
from __future__ import annotations

import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.request

import yaml

HERE = pathlib.Path(__file__).resolve().parent


def main() -> int:
    base_url = os.environ.get("HERMES_BENCH_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
    api_key = os.environ.get("HERMES_BENCH_API_KEY", "")
    matrix_file = os.environ.get("HERMES_BENCH_MATRIX", "matrix.yaml")
    out_file = os.environ.get("HERMES_BENCH_OUT", "results/results.csv")

    only_model, only_task = "", ""
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--model":
            only_model = args[i + 1]; i += 2
        elif args[i] == "--task":
            only_task = args[i + 1]; i += 2
        else:
            print(f"unknown arg: {args[i]}", file=sys.stderr); return 2

    if not api_key:
        print("HERMES_BENCH_API_KEY is not set", file=sys.stderr)
        return 2

    matrix = yaml.safe_load((HERE / matrix_file).read_text(encoding="utf-8"))
    models = matrix["models"]
    tasks = matrix["tasks"]

    out_path = HERE / out_file
    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not out_path.exists()
    fh = open(out_path, "a", encoding="utf-8", newline="")
    if write_header:
        fh.write("model,task,repeat,status,latency_s,prompt_tokens,completion_tokens,total_tokens\n")

    total = 0
    for model in models:
        mid = model["id"]
        if only_model and mid != only_model:
            continue
        context = int(model.get("context_tokens", 0))
        for task in tasks:
            tid = task["id"]
            if only_task and tid != only_task:
                continue
            repeats = int(task.get("repeats", 1))
            temp = float(task.get("temperature", 0))
            skip_lt = int(task.get("skip_if_context_lt", 0))

            prompt_path = HERE / "tasks" / f"{tid}.md"
            if not prompt_path.exists():
                print(f"missing {prompt_path}", file=sys.stderr)
                return 1

            if skip_lt and context < skip_lt:
                print(f"skip  {mid} x {tid} (context {context} < {skip_lt})")
                fh.write(f"{mid},{tid},0,skipped_context,,,,\n")
                continue

            prompt = prompt_path.read_text(encoding="utf-8")
            payload = json.dumps({
                "model": mid,
                "temperature": temp,
                "messages": [{"role": "user", "content": prompt}],
            }).encode("utf-8")

            for rep in range(1, repeats + 1):
                total += 1
                print(f"run   {mid} x {tid} ({rep}/{repeats})")
                req = urllib.request.Request(
                    f"{base_url}/chat/completions",
                    data=payload,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    method="POST",
                )
                start = time.perf_counter()
                try:
                    with urllib.request.urlopen(req, timeout=600) as resp:
                        body = resp.read().decode("utf-8")
                    latency = time.perf_counter() - start
                    try:
                        r = json.loads(body)
                    except json.JSONDecodeError:
                        r = {"error": {"message": "unparseable response"}}
                    if "error" in r or "usage" not in r:
                        msg = r.get("error", {}).get("message", "no usage field")
                        fh.write(f"{mid},{tid},{rep},error,{latency:.2f},,,\n")
                        print(f"      error: {msg}", file=sys.stderr)
                    else:
                        u = r["usage"]
                        fh.write(
                            f"{mid},{tid},{rep},ok,{latency:.2f},"
                            f"{u.get('prompt_tokens','')},{u.get('completion_tokens','')},{u.get('total_tokens','')}\n"
                        )
                except urllib.error.HTTPError as e:
                    latency = time.perf_counter() - start
                    fh.write(f"{mid},{tid},{rep},error,{latency:.2f},,,\n")
                    print(f"      HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:200]}", file=sys.stderr)
                except Exception as e:
                    latency = time.perf_counter() - start
                    fh.write(f"{mid},{tid},{rep},error,{latency:.2f},,,\n")
                    print(f"      {type(e).__name__}: {e}", file=sys.stderr)
                fh.flush()

    fh.close()
    print(f"\ndone — {total} runs in {out_file}")
    print(f"render tables: python render.py {out_file} {matrix_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
