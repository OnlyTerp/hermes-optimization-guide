"""Score your Hermes setup — a shareable self-audit.

Usage:
  python scripts/score-your-setup.py

Reads your local Hermes install (HERMES_HOME or ~/.hermes / %LOCALAPPDATA%\\hermes)
and scores it across 10 categories. Never prints secrets — only checks whether
keys exist. Screenshot your total and share it: "hermes score 41/50".

Categories (50 points total):
   8  Install health        (on PATH, version parses, on the current wave)
   4  Config sanity         (config.yaml exists + parses + model set)
   5  Provider wiring       (at least one API key reachable)
  10  Security posture      (approvals / gateway allowlists present)
   7  Hygiene               (no obvious plaintext secrets in config.yaml)
   4  Memory in use         (memory store files exist with content)
   4  Skills loaded         (one or more custom skills on disk)
   4  Multi-platform        (one or more gateway platforms configured)
   2  Scheduled work        (at least one cron job)
   2  Cost controls         (auxiliary/fallback models configured)
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

# Platform section names observed in Hermes configs (v0.19/v0.20 wave).
# Configs keep auth in .env (correctly), so presence of the section itself —
# not a token — is the signal. False negatives cost points, never fake passes.
KNOWN_PLATFORMS = {
    "telegram", "discord", "slack", "whatsapp", "signal", "matrix", "teams",
    "homeassistant", "line", "viber", "dingtalk", "feishu", "wechat",
    "email", "sms", "mattermost", "rocketchat", "zulip", "nextcloud",
    "twitch", "kick", "nostr", "xmpp", "photon", "irc", "messenger",
}


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


def configured_platforms(cfg):
    """Union of gateway.platforms.* and known top-level platform sections."""
    names = set()
    if not isinstance(cfg, dict) or "_keys_only" in cfg:
        return names
    gw = cfg.get("gateway", {})
    if isinstance(gw, dict):
        plats = gw.get("platforms", {})
        if isinstance(plats, dict):
            for name, pconf in plats.items():
                if isinstance(pconf, dict) and pconf.get("enabled") is not False:
                    names.add(name)
    for name, val in cfg.items():
        if name in KNOWN_PLATFORMS and isinstance(val, dict):
            if val.get("enabled") is not False:
                names.add(name)
    return names


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

    # ---- 1. Install health (8) ----
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
    section("Install health", 8, [
        (bool(hermes_bin), 3, "hermes on PATH"),
        (version_ok, 3, f"version parses ({version_str or 'n/a'})"),
        (version_ok and version_str >= "0.20.0", 2, "on the current wave (>= 0.20)"),
    ])

    # ---- 2. Config sanity (4) ----
    cfg_path, cfg = load_config(home)
    model_set = False
    if isinstance(cfg, dict) and cfg and "_keys_only" not in cfg:
        model_set = any(k.startswith("model") or k.startswith("providers")
                        for k in flat_keys(cfg))
    elif isinstance(cfg, dict) and "_keys_only" in cfg:
        model_set = any(k in ("model", "providers") for k in cfg["_keys_only"])
    section("Config sanity", 4, [
        (cfg_path is not None and cfg_path.exists(), 1, "config.yaml exists"),
        (cfg is not None, 1, "config.yaml parses"),
        (model_set, 2, "model/providers configured"),
    ])

    # ---- 3. Provider wiring (5) ----
    key_envs = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY",
                "GROQ_API_KEY", "XAI_API_KEY", "ZAI_API_KEY"]
    env_keys = [k for k in key_envs if os.environ.get(k)]
    cfg_keys = False
    if isinstance(cfg, dict) and cfg and "_keys_only" not in cfg:
        cfg_keys = any(k.endswith("api_key") for k in flat_keys(cfg))
    ok3 = bool(env_keys) or cfg_keys
    label3 = (f"provider key reachable ({len(env_keys)} env key(s))"
              if env_keys else "provider key reachable (config or env)")
    section("Provider wiring", 5, [(ok3, 5, label3)])

    # ---- 4. Security posture (10) ----
    fk = set(flat_keys(cfg)) if isinstance(cfg, dict) and cfg and "_keys_only" not in cfg else set()
    has_approvals = any("approvals" in k for k in fk)
    has_allowlist = any("allowlist" in k or "allowed_user" in k
                        or "allowed_chats" in k or "allowed_channels" in k
                        or "require_mention" in k for k in fk)
    section("Security posture", 10, [
        (has_approvals, 6, "approvals section configured"),
        (has_allowlist, 4, "gateway allowlist / mention-gating configured"),
    ])

    # ---- 5. Hygiene (7) ----
    leak = False
    if cfg_path and cfg_path.exists():
        text = cfg_path.read_text(encoding="utf-8", errors="replace")
        if re.search(r"(sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}|xox[baprs]-[A-Za-z0-9-]{10,})", text):
            leak = True
    section("Hygiene", 7, [
        (not leak, 7, "no plaintext API tokens visible in config.yaml"),
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
        (skill_count > 0, 4, f"custom skills installed ({skill_count} found)"),
    ])

    # ---- 8. Multi-platform (4) ----
    plats = configured_platforms(cfg)
    section("Multi-platform", 4, [
        (len(plats) >= 1, 2, f"gateway platforms configured ({len(plats)}: "
                              f"{', '.join(sorted(plats)) or 'none'})"),
        (len(plats) >= 2, 2, "two or more platforms (cross-poster ready)"),
    ])

    # ---- 9. Scheduled work (2) ----
    cron_dir = home / "cron"
    cron_jobs = 0
    if cron_dir.is_dir():
        for f in cron_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                cron_jobs += len(data) if isinstance(data, list) else 1
            except Exception:
                pass
    section("Scheduled work", 2, [
        (cron_jobs > 0, 2, f"cron jobs defined ({cron_jobs})"),
    ])

    # ---- 10. Cost controls (2) ----
    has_aux = any("auxiliary" in k or "fallback" in k for k in fk)
    section("Cost controls", 2, [
        (has_aux, 2, "auxiliary/fallback models configured (cost routing)"),
    ])

    # ---- verdict ----
    if total >= 43:
        verdict = "WAR-DESK GRADE"
    elif total >= 31:
        verdict = "SEASONED OPERATOR"
    elif total >= 16:
        verdict = "WIRING PHASE"
    else:
        verdict = "FRESH SPAWN"

    print("HERMES SETUP SCORECARD")
    print("=" * 46)
    print(f"Hermes home: {home}")
    print()
    print("\n".join(lines))
    print()
    print(f"TOTAL: {total}/50  ->  {verdict}")
    print()
    print(f'Share it: "hermes score {total}/50 ({verdict})"')
    return 0


if __name__ == "__main__":
    sys.exit(main())
