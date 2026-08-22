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
    if missing:
        print("DRIFT DETECTED:", len(missing), "non-existent subcommand(s)")
        if args.exit_on_drift:
            return 1
    else:
        print("CLEAN: all referenced subcommands exist.")
    return 0

if __name__ == "__main__":
    sys.exit(main())