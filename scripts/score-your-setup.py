"""Score your Hermes setup — a runnable self-audit.

Usage:
  python scripts/score-your-setup.py

Reads your local Hermes install (HERMES_HOME or ~/.hermes / %LOCALAPPDATA%\hermes)
and scores what is VERIFIABLE on disk. Never prints secrets — only checks
whether key material exists. No gamification: the number is the point, the
MISS lines are the to-do list.

Categories (50 points total) — every point maps to a check you can re-run:
   6  Install health        (on PATH, version parses)
   6  Config sanity         (config.yaml exists + parses + model/providers set)
   5  Provider wiring       (at least one API key present)
  14  Security posture      (approvals.mode set, allowlist/mention-gate,
                            secrets redaction on)
   8  Hygiene               (no plaintext API tokens in config.yaml)
   4  Memory in use         (memory store files exist with content)
   4  Skills loaded         (one or more SKILL.md on disk)
   3  Cost controls         (auxiliary/fallback models configured)

Deliberately NOT scored (surface area is not quality): number of platforms,
presence of cron jobs, "are you on the newest version". A hardened
single-Telegram box must be able to outscore a sloppy five-platform setup.
"""

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

CHECK_MARK = "[PASS]"
MISS_MARK = "[MISS]"

# Real values approvals.mode accepts (upstream hermes_cli/approval_mode.py).
REAL_APPROVAL_MODES = {"off", "manual", "smart", "strict"}


def hermes_home() -> Path:
    env = os.environ.get("HERMES_HOME")
    if env:
        return Path(env).expanduser()
    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA")
        if local:
            p = Path(local) / "hermes"
            if p.exists():
                return p
    return Path.home() / ".hermes"


def load_config(home: Path):
    cfg_path = home / "config.yaml"
    if not cfg_path.exists():
        return None, None
    try:
        import yaml
    except ImportError:
        text = cfg_path.read_text(encoding="utf-8", errors="replace")
        keys = re.findall(r"^([A-Za-z0-9_]+):", text, re.M)
        return cfg_path, {"_keys_only": keys}
    try:
        data = yaml.safe_load(cfg_path.read_text(encoding="utf-8", errors="replace")) or {}
        return cfg_path, data
    except Exception:
        return cfg_path, None


def flat_keys(obj, prefix=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from flat_keys(v, f"{prefix}.{k}" if prefix else str(k))
    else:
        yield prefix


def get_path(cfg, dotted):
    cur = cfg
    for seg in dotted.split("."):
        if not isinstance(cur, dict) or seg not in cur:
            return None
        cur = cur[seg]
    return cur


def main():
    home = hermes_home()
    total = 0
    lines = []

    def section(name, pts_max, checks):
        nonlocal total
        got = sum(p for ok, p, _ in checks if ok)
        total += got
        lines.append(f"[{got:>2}/{pts_max:>2}] {name}")
        for ok, p, label in checks:
            lines.append(f"        {CHECK_MARK if ok else MISS_MARK} {label} (+{p})")

    fk_cfg = None  # populated after config load

    # ---- 1. Install health (6) ----
    version_ok, version_str = False, ""
    hermes_bin = shutil.which("hermes")
    if hermes_bin:
        try:
            out = subprocess.run(
                [hermes_bin, "--version"], capture_output=True, text=True, timeout=30
            ).stdout
            m = re.search(r"v?(\d+\.\d+\.\d+)", out)
            if m:
                version_ok, version_str = True, m.group(1)
        except Exception:
            pass
    section("Install health", 6, [
        (bool(hermes_bin), 3, "hermes on PATH"),
        (version_ok, 3, f"version parses ({version_str or 'n/a'})"),
    ])

    # ---- 2. Config sanity (6) ----
    cfg_path, cfg = load_config(home)
    parsed = isinstance(cfg, dict) and cfg and "_keys_only" not in cfg
    if parsed:
        model_set = bool(get_path(cfg, "model")) or bool(get_path(cfg, "providers"))
    elif isinstance(cfg, dict) and "_keys_only" in cfg:
        model_set = any(k in ("model", "providers") for k in cfg["_keys_only"])
    else:
        model_set = False
    section("Config sanity", 6, [
        (cfg_path is not None and cfg_path.exists(), 2, "config.yaml exists"),
        (cfg is not None, 2, "config.yaml parses"),
        (model_set, 2, "model/providers configured"),
    ])

    # ---- 3. Provider wiring (5) ----
    key_envs = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY",
                "GROQ_API_KEY", "XAI_API_KEY", "ZAI_API_KEY"]
    env_keys = [k for k in key_envs if os.environ.get(k)]
    cfg_keys = bool(parsed) and any(k.endswith("api_key") for k in flat_keys(cfg))
    ok3 = bool(env_keys) or cfg_keys
    label3 = (f"provider key present ({len(env_keys)} env key(s))"
              if env_keys else "provider key present (config or env)")
    section("Provider wiring", 5, [(ok3, 5, label3)])

    # ---- 4. Security posture (14) ----
    fk = set(flat_keys(cfg)) if parsed else set()
    approval_mode = get_path(cfg, "approvals.mode") if parsed else None
    approvals_ok = isinstance(approval_mode, str) and approval_mode.lower() in REAL_APPROVAL_MODES
    gated = False
    if parsed:
        if get_path(cfg, "command_allowlist"):
            gated = True
        if get_path(cfg, "require_mention"):
            gated = True
        # any platform-level allowlist (telegram.allowed_users, discord.*, ...)
        gated = gated or any(re.search(r"(allowed_user|allowed_chat|allowed_channel|allowlist)", k)
                             for k in fk)
    redact = get_path(cfg, "security.redact_secrets") if parsed else None
    # Upstream default is ON when absent (config.py coerces None -> default);
    # explicit false is the only failing state.
    redact_ok = redact is not False
    redact_label = ("secrets redaction on (explicit)" if redact is True
                    else "secrets redaction on (upstream default)" if redact_ok
                    else "secrets redaction DISABLED")
    section("Security posture", 14, [
        (approvals_ok, 6, f"approvals.mode set to a real mode "
                          f"({approval_mode or 'unset'})"),
        (gated, 4, "allowlist / mention-gating configured"),
        (redact_ok, 4, redact_label),
    ])

    # ---- 5. Hygiene (8) ----
    leak = False
    if cfg_path and cfg_path.exists():
        text = cfg_path.read_text(encoding="utf-8", errors="replace")
        if re.search(r"(sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}|xox[baprs]-[A-Za-z0-9-]{10,})", text):
            leak = True
    section("Hygiene", 8, [
        (not leak, 8, "no plaintext API tokens visible in config.yaml"),
    ])

    # ---- 6. Memory in use (4) ----
    mem_files = []
    for d in (home / "memories", home / "memory"):
        if d.is_dir():
            mem_files = [f for f in d.rglob("*") if f.is_file() and f.stat().st_size > 20]
            if mem_files:
                break
    section("Memory in use", 4, [
        (len(mem_files) > 0, 4, f"memory store has content ({len(mem_files)} file(s))"),
    ])

    # ---- 7. Skills loaded (4) ----
    skills_dir = home / "skills"
    skill_count = len(list(skills_dir.rglob("SKILL.md"))) if skills_dir.is_dir() else 0
    section("Skills loaded", 4, [
        (skill_count > 0, 4, f"skills installed ({skill_count} found)"),
    ])

    # ---- 8. Cost controls (3) ----
    has_aux = any("auxiliary" in k or "fallback" in k for k in fk)
    section("Cost controls", 3, [
        (has_aux, 3, "auxiliary/fallback models configured (cost routing)"),
    ])

    # ---- summary ----
    gaps = [c[2] for sec in [] for c in []]  # placeholder, computed below
    print("HERMES SETUP AUDIT")
    print("=" * 46)
    print(f"Hermes home: {home}")
    print()
    print("\n".join(lines))
    print()
    misses = [l.strip()[len(MISS_MARK):].strip()
              for l in lines if MISS_MARK in l]
    print(f"TOTAL: {total}/50  ({len(misses)} gap(s))")
    if misses:
        print("Fix first:")
        for m in misses[:5]:
            print(f"  - {m}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
