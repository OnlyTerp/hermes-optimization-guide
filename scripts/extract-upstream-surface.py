"""Extract the FULL Hermes command/config surface from an upstream checkout.

Usage:
  python scripts/extract-upstream-surface.py /path/to/hermes-agent --out-dir DIR

Writes three files into DIR:
  commands.txt       one CLI subcommand per line
                     (_BUILTIN_SUBCOMMANDS + plugin registrations)
  slash-commands.txt one slash command per line, aliases included
                     (COMMAND_REGISTRY in hermes_cli/commands.py)
  config-keys.txt    one dotted config path per line from DEFAULT_CONFIG
                     (hermes_cli/config_defaults.py); dynamic namespaces
                     appear as `prefix.*` wildcards

Everything is AST/regex-parsed from source — no Hermes install needed, which
is what lets the drift-guard CI job run it against a pinned upstream tag.
"""
import ast
import re
import sys
import pathlib

# Namespaces whose children are operator/platform-defined, not fixed schema.
# Anything under them is allowed by wildcard instead of enumerated.
WILDCARD_PREFIXES = (
    "gateway.platforms", "providers", "credential_pool_strategies",
    # Dynamic / user-extensible sections that are valid config but whose
    # children aren't a fixed enumeration:
    "model",          # model.default / model.provider / model.context_length ...
    "model_aliases",  # model_aliases.<name>.model / .provider (model_switch.py)
    "mcp_servers",    # mcp_servers.<name>.command / .args / .tools.include ...
    "platforms",      # top-level per-platform map merged by gateway/config.py
)
MAX_DEPTH = 4

# Keys that are read/written by Hermes but live OUTSIDE both DEFAULT_CONFIG
# and _EXTRA_KNOWN_ROOT_KEYS (extra roots parsed from config.py below).
# Each is verified against the upstream source at the tag being audited.
CURATED_REAL_KEYS = {
    "model_catalog.excluded_providers",  # hermes_cli/inventory.py reads it
    "delegation.command",                # tools/delegate_tool.py validates it
    "delegation.args",                   # tools/delegate_tool.py passes it
    "agent.verbose",                     # openclaw migration writes it
    "agent.reasoning_effort",            # cli_commands_mixin writes; config.py docstring
}


def extract_builtin_commands(source_root):
    main_py = source_root / "hermes_cli" / "main.py"
    if not main_py.exists():
        sys.exit("ERROR: %s not found — is this a hermes-agent checkout?" % main_py)
    tree = ast.parse(main_py.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name) and tgt.id == "_BUILTIN_SUBCOMMANDS":
                    value = node.value
                    if isinstance(value, ast.Call) and value.args:
                        value = value.args[0]
                    if isinstance(value, ast.Set):
                        vals = set()
                        for elt in value.elts:
                            if isinstance(elt, ast.Constant):
                                vals.add(elt.value)
                        if vals:
                            return vals
    sys.exit("ERROR: _BUILTIN_SUBCOMMANDS not found in %s" % main_py)


def extract_plugin_commands(source_root):
    pat = re.compile(r'register_cli_command\(\s*name\s*=\s*"([a-z][a-z0-9-]*)"')
    cmds = set()
    plugins = source_root / "plugins"
    if plugins.exists():
        for f in plugins.rglob("*.py"):
            try:
                cmds |= set(pat.findall(f.read_text(encoding="utf-8", errors="replace")))
            except OSError:
                pass
    return cmds


def extract_slash_commands(source_root):
    """Names + aliases from COMMAND_REGISTRY in hermes_cli/commands.py."""
    commands_py = source_root / "hermes_cli" / "commands.py"
    if not commands_py.exists():
        sys.exit("ERROR: %s not found" % commands_py)
    src = commands_py.read_text(encoding="utf-8")
    names = set(re.findall(r'CommandDef\(\s*"([a-z0-9_-]+)"', src))
    aliases = set()
    for chunk in re.findall(r"aliases=\(([^)]*)\)", src):
        aliases |= set(re.findall(r'"([a-z0-9_-]+)"', chunk))
    return names | aliases


def _walk_config(d, prefix, depth, out):
    for k, v in d.items():
        p = f"{prefix}.{k}" if prefix else str(k)
        if any(p == w or p.startswith(w + ".") for w in WILDCARD_PREFIXES):
            # entered a dynamic namespace — emit wildcard once, don't enumerate
            w = next(w for w in WILDCARD_PREFIXES if p == w or p.startswith(w + "."))
            out.add(w + ".*")
            continue
        if isinstance(v, dict):
            if not v or depth >= MAX_DEPTH:
                out.add(p + ".*")
            else:
                out.add(p)  # the section key itself is referenceable too
                _walk_config(v, p, depth + 1, out)
        else:
            out.add(p)


def extract_config_keys(source_root):
    defaults_py = source_root / "hermes_cli" / "config_defaults.py"
    if not defaults_py.exists():
        sys.exit("ERROR: %s not found" % defaults_py)
    tree = ast.parse(defaults_py.read_text(encoding="utf-8"))
    config_node = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name) and tgt.id == "DEFAULT_CONFIG":
                    config_node = node.value
    if config_node is None:
        sys.exit("ERROR: DEFAULT_CONFIG not found in %s" % defaults_py)

    out = set()
    # Evaluate the dict literal safely via ast.literal_eval where possible;
    # fall back to structural walking for non-literal values.
    def walk_node(node, prefix, depth):
        if isinstance(node, ast.Dict):
            for k, v in zip(node.keys, node.values):
                if not isinstance(k, ast.Constant):
                    continue
                p = f"{prefix}.{k.value}" if prefix else str(k.value)
                if any(p == w or p.startswith(w + ".") for w in WILDCARD_PREFIXES):
                    w = next(w for w in WILDCARD_PREFIXES if p == w or p.startswith(w + "."))
                    out.add(w + ".*")
                    continue
                if isinstance(v, ast.Dict):
                    if not v.keys or depth >= MAX_DEPTH:
                        out.add(p + ".*")
                    else:
                        out.add(p)
                        walk_node(v, p, depth + 1)
                else:
                    out.add(p)
    walk_node(config_node, "", 1)
    # WILDCARD_PREFIXES may never be walked (absent from DEFAULT_CONFIG,
    # e.g. model_aliases, gateway.platforms) — emit them unconditionally.
    out |= {w + ".*" for w in WILDCARD_PREFIXES}
    return out


def extract_extra_root_keys(source_root):
    """Parse _EXTRA_KNOWN_ROOT_KEYS from hermes_cli/config.py.

    These are roots that are valid in config.yaml but intentionally absent
    from DEFAULT_CONFIG (mcp_servers, group_sessions_per_user, signal, ...).
    Each gets a .* wildcard since their children are dynamic.
    """
    config_py = source_root / "hermes_cli" / "config.py"
    if not config_py.exists():
        return set()
    src = config_py.read_text(encoding="utf-8")
    # NB: match to a line-start `}` — inline comments contain {} literals
    # (e.g. "providers: {}") that would truncate a naive [^}]* scan.
    m = re.search(r"_EXTRA_KNOWN_ROOT_KEYS\s*=\s*\{(.*?)^\}", src, re.S | re.M)
    if not m:
        return set()
    keys = set(re.findall(r'"([a-z][a-z0-9_]*)"', m.group(1)))
    return {k + ".*" for k in keys}


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    root = pathlib.Path(sys.argv[1])
    out_dir = pathlib.Path("surface-out")
    if "--out-dir" in sys.argv:
        out_dir = pathlib.Path(sys.argv[sys.argv.index("--out-dir") + 1])
    out_dir.mkdir(parents=True, exist_ok=True)

    cmds = extract_builtin_commands(root) | extract_plugin_commands(root)
    cmds.discard("help")
    (out_dir / "commands.txt").write_text(
        "".join("%s\n" % c for c in sorted(cmds)), encoding="utf-8")

    slash = extract_slash_commands(root)
    (out_dir / "slash-commands.txt").write_text(
        "".join("%s\n" % c for c in sorted(slash)), encoding="utf-8")

    keys = extract_config_keys(root) | extract_extra_root_keys(root) | CURATED_REAL_KEYS
    (out_dir / "config-keys.txt").write_text(
        "".join("%s\n" % k for k in sorted(keys)), encoding="utf-8")

    print("wrote %d CLI commands, %d slash commands, %d config key paths to %s"
          % (len(cmds), len(slash), len(keys), out_dir), file=sys.stderr)


if __name__ == "__main__":
    main()
