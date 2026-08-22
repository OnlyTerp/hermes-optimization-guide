import argparse
import re
import sys
import pathlib

repo = pathlib.Path(__file__).resolve().parent.parent

def load_real_commands(help_text):
    """Parse the subcommand brace list from `hermes --help` output."""
    m = re.search(r"\{(chat,model[^}]+)\}", help_text)
    if not m:
        return None
    cmds = {c for c in m.group(1).split(",") if c}
    # subcommands defined outside the argparse choices brace (verified v0.20.4)
    cmds |= {"photon"}
    return cmds

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--help-file", default=None,
                    help="Path to saved `hermes --help` output (CI-friendly). "
                         "Default: run `hermes --help` live.")
    ap.add_argument("--commands-file", default=None,
                    help="Path to a one-command-per-line list (e.g. output of "
                         "extract-upstream-commands.py). Overrides --help-file.")
    ap.add_argument("--slash-file", default=None,
                    help="Path to a one-slash-command-per-line list "
                         "(extract-upstream-surface.py slash-commands.txt).")
    ap.add_argument("--config-file", default=None,
                    help="Path to a one-config-key-path-per-line list; entries "
                         "ending in .* act as wildcards.")
    ap.add_argument("--exit-on-drift", action="store_true",
                    help="Exit non-zero if any referenced subcommand is missing.")
    args = ap.parse_args()

    if args.commands_file:
        with open(args.commands_file, encoding="utf-8") as fh:
            real = {ln.strip() for ln in fh if ln.strip()}
        source = args.commands_file
    elif args.help_file:
        with open(args.help_file, encoding="utf-8") as fh:
            real = load_real_commands(fh.read())
        source = args.help_file
    else:
        import subprocess
        out = subprocess.run(["hermes", "--help"], capture_output=True,
                             text=True, timeout=120).stdout
        real = load_real_commands(out)
        source = "hermes --help (live)"

    if real is None:
        print("FATAL: could not parse command list from", source)
        return 2

    pat = re.compile(r"(?:^|[^\w-])hermes\s+([a-zA-Z][a-zA-Z0-9-]{1,30})")
    quote_pat = re.compile(r"\"[^\"]*\"|'[^']*'")
    skip = {"--help", "--version", "|", "is", "the", "you", "run", "will", "user", "installer"}
    mentions = {}

    def code_lines(md_text):
        """Yield only code-context lines: fenced blocks + inline `code` spans."""
        in_fence = False
        for line in md_text.splitlines():
            stripped = line.lstrip()
            if stripped.startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence:
                yield line
            else:
                for span in re.findall(r"`([^`\n]+)`", line):
                    yield span

    for f in sorted(repo.glob("*.md")):
        if f.name in ("README-zh.md", "README-ja.md", "CHANGELOG.md"):
            continue
        text = f.read_text(encoding="utf-8")
        for line in code_lines(text):
            line = quote_pat.sub("", line)  # drop string literals
            for m in pat.finditer(line):
                cmd = m.group(1)
                if cmd in skip:
                    continue
                mentions.setdefault(cmd, set()).add(f.name)

    all_mentioned = set(mentions.keys())
    missing = sorted(m for m in all_mentioned if m not in real)

    print("Sources:", source)
    print("Real commands:", len(real))
    print("Distinct commands mentioned in guide:", len(all_mentioned))
    print()
    print("=== MENTIONED IN GUIDE BUT NOT IN REAL CLI (%d) ===" % len(missing))
    for m in missing:
        files = sorted(mentions[m])[:5]
        print("  %-18s -> %s" % (m, files))
    print()
    used_real = sorted(all_mentioned - set(missing))
    print("Real commands actually referenced:", len(used_real))
    drift_count = len(missing)

    # ---- slash-command audit ----
    if args.slash_file:
        with open(args.slash_file, encoding="utf-8") as fh:
            real_slash = {ln.strip() for ln in fh if ln.strip()}
        slash_pat = re.compile(r"`/([a-z][a-z0-9_-]{1,25})`")
        slash_mentions = {}
        # Known NON-Hermes slash tokens that legitimately appear in the guide.
        # Each documented so this list stays auditable.
        SLASH_SKIP = {
            # Telegram BotFather commands (part4/part27/part28), not Hermes.
            "newbot", "mybots", "revoke", "setuserpic", "setcommands",
            "setdescription", "setabouttext", "setprivacy", "setname",
            # Dashboard HTTP routes (part12) — verified present in
            # upstream hermes_cli/web_server.py, not CLI slash commands.
            "backup", "dump", "security-audit", "prompt-size", "chat", "import",
            # Provider/platform API endpoint paths (part9/part15).
            "messages", "models", "completions", "bluebubbles-webhook",
        }
        # skip common URL/path fragments that look like /word
        slash_skip = {"usr", "bin", "tmp", "etc", "opt", "home", "dev", "var",
                      "v1", "api", "com", "issues", "raw", "docs"} | SLASH_SKIP
        for f in sorted(repo.glob("*.md")):
            if f.name in ("README-zh.md", "README-ja.md", "CHANGELOG.md"):
                continue
            text = f.read_text(encoding="utf-8")
            in_fence = False
            for line in text.splitlines():
                stripped = line.lstrip()
                if stripped.startswith("```"):
                    in_fence = not in_fence
                    continue
                if in_fence:
                    continue  # /paths inside code blocks are usually paths/URLs
                for m in slash_pat.finditer(line):
                    cmd = m.group(1)
                    if cmd in slash_skip:
                        continue
                    slash_mentions.setdefault(cmd, set()).add(f.name)
        slash_missing = sorted(m for m in slash_mentions if m not in real_slash)
        print()
        print("=== SLASH: mentioned but NOT in upstream COMMAND_REGISTRY (%d) ==="
              % len(slash_missing))
        for m in slash_missing:
            print("  /%-16s -> %s" % (m, sorted(slash_mentions[m])[:5]))
        drift_count += len(slash_missing)
        print("Slash surface checked: %d real, %d referenced"
              % (len(real_slash), len(slash_mentions)))

    # ---- config-key audit ----
    if args.config_file:
        with open(args.config_file, encoding="utf-8") as fh:
            real_keys = {ln.strip() for ln in fh if ln.strip()}
        wildcards = {k[:-2] for k in real_keys if k.endswith(".*")}
        exact = {k for k in real_keys if not k.endswith(".*")}

        def key_is_real(k):
            if k in exact:
                return True
            return any(k == w or k.startswith(w + ".") for w in wildcards)

        # File-extension heuristic: a "config key" whose last segment is a
        # file extension is a filename (state.db, config.yaml, mcp.json),
        # not a config path.
        FILE_EXT = re.compile(r"\.(json|jsonl|ya?ml|py|db|cpp|gz|sh|service|sqlite|txt|md|log)$")
        # Curated false-positive skip-list. Each entry is NOT a Hermes config
        # key even though it looks like one. Reason documented inline so this
        # list stays honest and auditable.
        CFG_SKIP = {
            # OpenTelemetry / observability SPAN NAMES documented in part20,
            # not config keys.
            "agent.turn", "llm.call", "tool.call", "memory.search", "skill.load",
            "kanban.task", "kanban.worker", "browser_use.launch",
            # Explicit "these keys are NOT real — don't paste them" negations
            # (part20 / part19 teach readers what does NOT exist).
            "compression.auto.at_tokens", "preserve.tool_results_matching",
            "approval.require_approval", "secrets.scope",
            "network.egress_allowlist", "security.network.egress_allowlist",
            # OpenClaw SOURCE-side keys in part2's migration mapping table
            # (left column = where they come FROM, not Hermes keys).
            "agents.defaults.model", "agents.defaults.compaction.mode",
            "agents.defaults.verboseDefault", "agents.defaults.thinkingDefault",
            # Message-metadata field (part22 blueprints), not config.
            "metadata.hermes.blueprint",
            # Per-MCP-server tool knobs. Real keys, but written in BARE form
            # (tools.include / tools.exclude / ...) inside the per-server
            # context of part17/part19/part28 — the full path is
            # mcp_servers.<name>.tools.include (mcp_config.py reads all four).
            "tools.include", "tools.exclude", "tools.prompts", "tools.resources",
        }

        cfg_pat = re.compile(r"`((?:[a-z][a-z0-9_]*\.){1,4}[a-z][a-z0-9_.]*)`")
        cfg_mentions = {}
        scan_files = sorted(repo.glob("*.md")) + sorted((repo / "templates").rglob("*.yaml"))
        for f in scan_files:
            if f.name in ("README-zh.md", "README-ja.md", "CHANGELOG.md"):
                continue
            text = f.read_text(encoding="utf-8")
            relname = str(f.relative_to(repo)).replace("\\", "/")
            if f.suffix == ".yaml":
                # YAML templates: reconstruct dotted paths from indentation
                stack = []
                for line in text.splitlines():
                    if not line.strip() or line.lstrip().startswith("#"):
                        continue
                    indent = len(line) - len(line.lstrip())
                    m = re.match(r"\s*([a-z][a-zA-Z0-9_]*):", line)
                    if not m:
                        continue
                    while stack and stack[-1][0] >= indent:
                        stack.pop()
                    stack.append((indent, m.group(1)))
                    key = ".".join(seg for _, seg in stack).lower()
                    if FILE_EXT.search(key) or key in CFG_SKIP:
                        continue
                    cfg_mentions.setdefault(key, set()).add(relname)
            else:
                in_fence = False
                for line in text.splitlines():
                    stripped = line.lstrip()
                    if stripped.startswith("```"):
                        in_fence = not in_fence
                        continue
                    if not in_fence:
                        for span in re.findall(r"`([^`\n]+)`", line):
                            for m in cfg_pat.finditer("`" + span + "`"):
                                key = m.group(1)
                                if FILE_EXT.search(key) or key in CFG_SKIP:
                                    continue
                                cfg_mentions.setdefault(key, set()).add(relname)
        cfg_missing = sorted(k for k in cfg_mentions if not key_is_real(k))
        print()
        print("=== CONFIG: referenced but NOT in upstream DEFAULT_CONFIG (%d) ==="
              % len(cfg_missing))
        for k in cfg_missing:
            print("  %-34s -> %s" % (k, sorted(cfg_mentions[k])[:4]))
        drift_count += len(cfg_missing)
        print("Config surface checked: %d real paths (+%d wildcards), %d referenced"
              % (len(exact), len(wildcards), len(cfg_mentions)))

    print()
    if missing:
        print("DRIFT DETECTED:", drift_count, "non-existent reference(s)")
        if args.exit_on_drift:
            return 1
    elif drift_count:
        print("DRIFT DETECTED:", drift_count, "non-existent reference(s)")
        if args.exit_on_drift:
            return 1
    else:
        print("CLEAN: all referenced subcommands exist.")
    return 0

if __name__ == "__main__":
    sys.exit(main())