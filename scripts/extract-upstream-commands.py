"""Extract the real Hermes CLI command surface from an upstream source checkout.

Usage:
  python scripts/extract-upstream-commands.py /path/to/hermes-agent [--output FILE]

Reads `_BUILTIN_SUBCOMMANDS` from hermes_cli/main.py (via ast, so comment
churn can't break it) and adds plugin-registered commands found under
plugins/** (register_cli_command(name="...")). Prints one command per line.
"""
import ast
import re
import sys
import pathlib


def extract_builtin(source_root):
    main_py = source_root / "hermes_cli" / "main.py"
    if not main_py.exists():
        sys.exit("ERROR: %s not found — is this a hermes-agent checkout?" % main_py)
    tree = ast.parse(main_py.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name) and tgt.id == "_BUILTIN_SUBCOMMANDS":
                    value = node.value
                    # frozenset({...}) parses as a Call wrapping a Set
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


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    root = pathlib.Path(sys.argv[1])
    out_file = None
    if "--output" in sys.argv:
        i = sys.argv.index("--output")
        out_file = sys.argv[i + 1]
    cmds = extract_builtin(root) | extract_plugin_commands(root)
    cmds.discard("help")
    text = "".join("%s\n" % c for c in sorted(cmds))
    if out_file:
        pathlib.Path(out_file).write_text(text, encoding="utf-8")
        print("wrote %d commands to %s" % (len(cmds), out_file), file=sys.stderr)
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()