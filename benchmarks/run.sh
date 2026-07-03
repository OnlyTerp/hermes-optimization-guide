#!/usr/bin/env bash
# benchmarks/run.sh — reproducible cost/latency benchmark harness.
#
# Hermes has no `hermes evals` subcommand (see Part 20) — this is a plain
# curl harness against any OpenAI-compatible /chat/completions endpoint.
# Point it at OpenRouter (default), a provider directly, or your own proxy.
#
# Usage:
#   HERMES_BENCH_API_KEY=sk-... ./run.sh                     # all models x all tasks
#   HERMES_BENCH_API_KEY=sk-... ./run.sh --model zai/glm-5   # one model
#   HERMES_BENCH_API_KEY=sk-... ./run.sh --task T1_triage    # one task
#
# Env:
#   HERMES_BENCH_BASE_URL   default https://openrouter.ai/api/v1
#   HERMES_BENCH_API_KEY    required
#
# Output: results/results.csv — one row per (model, task, repeat) with
# latency and the token counts from the response `usage` field. Render the
# README tables from it with:  python3 render.py results/results.csv
#
# Requires: bash, curl, python3 (+PyYAML). No jq needed.
set -euo pipefail

cd "$(dirname "$0")"

BASE_URL="${HERMES_BENCH_BASE_URL:-https://openrouter.ai/api/v1}"
API_KEY="${HERMES_BENCH_API_KEY:-}"
ONLY_MODEL=""
ONLY_TASK=""

while [ $# -gt 0 ]; do
  case "$1" in
    --model) ONLY_MODEL="$2"; shift 2 ;;
    --task)  ONLY_TASK="$2";  shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

if [ -z "$API_KEY" ]; then
  echo "HERMES_BENCH_API_KEY is not set" >&2
  exit 2
fi

# Flatten matrix.yaml to TSV: model<TAB>context<TAB>task<TAB>repeats<TAB>temp<TAB>skip_lt
MATRIX_TSV=$(python3 - <<'PY'
import yaml
m = yaml.safe_load(open("matrix.yaml"))
for model in m["models"]:
    for task in m["tasks"]:
        print("\t".join(str(x) for x in (
            model["id"], model["context_tokens"], task["id"],
            task.get("repeats", 1), task.get("temperature", 0),
            task.get("skip_if_context_lt", 0),
        )))
PY
)

mkdir -p results
OUT="results/results.csv"
if [ ! -f "$OUT" ]; then
  echo "model,task,repeat,status,latency_s,prompt_tokens,completion_tokens,total_tokens" > "$OUT"
fi

while IFS=$'\t' read -r model context task repeats temp skip_lt; do
  [ -n "$ONLY_MODEL" ] && [ "$model" != "$ONLY_MODEL" ] && continue
  [ -n "$ONLY_TASK" ] && [ "$task" != "$ONLY_TASK" ] && continue

  if [ "$skip_lt" -gt 0 ] && [ "$context" -lt "$skip_lt" ]; then
    echo "skip  $model x $task (context $context < $skip_lt)"
    echo "$model,$task,0,skipped_context,,,," >> "$OUT"
    continue
  fi

  prompt_file="tasks/$task.md"
  if [ ! -f "$prompt_file" ]; then
    echo "missing $prompt_file" >&2
    exit 1
  fi

  for i in $(seq 1 "$repeats"); do
    echo "run   $model x $task ($i/$repeats)"
    payload=$(MODEL="$model" TEMP="$temp" PROMPT_FILE="$prompt_file" python3 - <<'PY'
import json, os
print(json.dumps({
    "model": os.environ["MODEL"],
    "temperature": float(os.environ["TEMP"]),
    "messages": [{"role": "user", "content": open(os.environ["PROMPT_FILE"]).read()}],
}))
PY
)
    start=$(date +%s.%N)
    response=$(curl -sS --max-time 600 \
      -H "Authorization: Bearer $API_KEY" \
      -H "Content-Type: application/json" \
      -d "$payload" \
      "$BASE_URL/chat/completions" || echo '{"error":{"message":"curl failed"}}')
    end=$(date +%s.%N)

    RESPONSE="$response" START="$start" END="$end" MODEL="$model" TASK="$task" REP="$i" \
      python3 - >> "$OUT" <<'PY'
import json, os
model, task, rep = os.environ["MODEL"], os.environ["TASK"], os.environ["REP"]
latency = float(os.environ["END"]) - float(os.environ["START"])
try:
    r = json.loads(os.environ["RESPONSE"])
except json.JSONDecodeError:
    r = {"error": {"message": "unparseable response"}}
if "error" in r or "usage" not in r:
    msg = r.get("error", {}).get("message", "no usage field")
    print(f"{model},{task},{rep},error,{latency:.2f},,,")
    import sys; print(f"      error: {msg}", file=sys.stderr)
else:
    u = r["usage"]
    print(f"{model},{task},{rep},ok,{latency:.2f},"
          f"{u.get('prompt_tokens','')},{u.get('completion_tokens','')},{u.get('total_tokens','')}")
PY
  done
done <<< "$MATRIX_TSV"

echo
echo "done — results in $OUT"
echo "render tables: python3 render.py $OUT"
