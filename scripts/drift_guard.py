#!/usr/bin/env python3
"""Drift guard: verify the guide against a pinned Hermes Agent release.

Hermes moves fast. This script keeps the guide honest by checking every
command, flag, slash command, config key, and environment variable the guide
mentions against the real upstream code at the tag the guide is pinned to.

Two steps:

  1. extract  -- run inside a Python env where the pinned hermes-agent checkout
                 is installed (``pip install -e .``). Builds ``surface.json``:
                   * the full ``hermes`` argparse tree (every subcommand + flag)
                   * slash commands (COMMAND_REGISTRY names + aliases)
                   * config key paths (DEFAULT_CONFIG + extra roots + dynamic maps)
                   * known environment variables
                   * bundled/optional skill names (valid as /<skill> commands)

  2. check    -- pure-stdlib + PyYAML. Scans README.md, guide/, templates/ and
                 skills/ and reports anything that doesn't exist upstream.

Usage:
  python scripts/drift_guard.py extract --upstream ../hermes-agent --out surface.json
  python scripts/drift_guard.py check --surface surface.json

What gets checked (only code contexts, never prose):
  * ``hermes ...`` invocations in fenced shell blocks and inline code spans
  * ``/slash`` commands in inline code spans and in ```text / ```chat blocks
  * config keys in ```yaml blocks whose top-level keys are Hermes config roots,
    in ``hermes config set|get|unset <key>``, and in inline spans like
    ``compression.threshold``
  * templates/config/*.yaml (every key path) and skills/**/SKILL.md frontmatter
  * UPPER_SNAKE env vars in code contexts

Escape hatches:
  * ``<!-- drift-guard: ignore -->`` on the line immediately before a fenced
    block skips that block (non-Hermes YAML such as compose files).
  * ``<!-- drift-guard: ignore-line -->`` anywhere on a line skips that line
    (for deliberately wrong examples, e.g. a table of myths).
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import shlex
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent

# Namespaces whose children are user-defined (names of providers, servers,
# platforms, personalities, ...). Any child path is accepted.
DYNAMIC_PREFIXES = (
    "providers", "credential_pool_strategies", "model_overrides", "personalities",
    "quick_commands", "platform_hints", "hooks", "mcp_servers", "custom_providers",
    "fallback_providers", "fallback_model", "platform_toolsets", "known_plugin_toolsets",
    "known_builtin_toolsets", "plugins", "platforms", "profile_routes", "honcho",
    "whatsapp", "signal", "image_gen", "video_gen", "smart_model_routing", "timeouts",
    "agent.reasoning_overrides", "compression.model_thresholds", "moa.presets",
    "lsp.servers", "status_phrases", "display.status_phrases", "display.platforms",
    "telegram.channel_prompts", "discord.channel_prompts", "slack.channel_prompts",
    "mattermost.channel_prompts", "web.provider_tier", "model_catalog.providers",
    "secrets.onepassword.env", "terminal.docker_env", "monitoring.export.otlp.headers_env",
    "dashboard.oauth", "onboarding.seen", "auxiliary",  # auxiliary.<task>.* is open-ended
    "model_aliases", "model.aliases",  # documented in user-guide/configuring-models.md
    "agent.personalities",            # user-defined names (features/personality.md)
    "provider_routing.models",        # per-model pins keyed by model ID (features/provider-routing.md)
)

# ``model:`` is a scalar in DEFAULT_CONFIG but a mapping in every real config.
# These children are documented in cli-config.yaml.example / configuration docs.
MODEL_KEYS = {
    "model.default", "model.model", "model.provider", "model.base_url", "model.api_key",
    "model.api_mode", "model.context_length", "model.ollama_num_ctx", "model.streaming",
    "model.default_headers", "model.extra_headers", "model.extra_body", "model.auth_mode",
    "model.entra", "model.entra.scope", "model.key_env",
}

# Paths read by Hermes but not present in DEFAULT_CONFIG. Each entry must be
# justified by upstream source or docs at the pinned tag.
CURATED_KEYS = {
    "agent.reasoning_effort",   # --reasoning help: "Overrides agent.reasoning_effort in config.yaml"
    "database.synchronous",     # cli-config.yaml.example (database section)
}

GENERIC_ENV = {
    "PATH", "HOME", "USER", "SHELL", "EDITOR", "VISUAL", "LANG", "LC_ALL", "TERM", "TZ",
    "PWD", "TMPDIR", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "HTTP_PROXY", "HTTPS_PROXY",
    "NO_PROXY", "SSH_AUTH_SOCK", "LOCALAPPDATA", "APPDATA", "USERPROFILE", "PYTHONPATH",
    "VIRTUAL_ENV", "CUDA_VISIBLE_DEVICES", "OLLAMA_HOST", "OLLAMA_CONTEXT_LENGTH",
    "OLLAMA_KEEP_ALIVE", "OLLAMA_NUM_PARALLEL", "OLLAMA_MAX_LOADED_MODELS",
    "OLLAMA_FLASH_ATTENTION", "OLLAMA_KV_CACHE_TYPE", "DEBIAN_FRONTEND", "SUDO_USER",
    "GITHUB_TOKEN", "GH_TOKEN", "DOCKER_HOST", "COMPOSE_PROJECT_NAME",
}

SHELL_LANGS = {"bash", "sh", "shell", "console", "zsh", "powershell", "ps1", "pwsh", "fish", ""}
CHAT_LANGS = {"text", "chat"}
PATH_ROOTS = {
    "tmp", "etc", "usr", "var", "opt", "home", "root", "dev", "proc", "bin", "sbin", "lib",
    "mnt", "srv", "run", "sys", "boot", "media", "snap", "private", "volumes", "users",
    "workspace", "data", "api", "v1", "docs", "health", "healthz", "metrics",
}
# Slash commands that belong to other products (BotFather, Slack, Discord, ...)
# and appear in setup instructions. They are not Hermes commands.
FOREIGN_SLASH = {
    "newbot", "mybots", "setprivacy", "setjoingroups", "setcommands", "token", "revoke",
    "setname", "setdescription", "setuserpic", "deletebot",          # Telegram @BotFather
    "invite", "remind", "apps",                                      # Slack
}
FILE_EXT = re.compile(r"\.(md|ya?ml|json|py|sh|db|txt|toml|env|log|lock|ps1|js|ts|html|css|zip|gz)$")


# --------------------------------------------------------------------------- extract

def _capture_parser():
    """Build the real `hermes` argparse tree by intercepting parse_args in main()."""
    captured: dict = {}

    class _Captured(BaseException):
        pass

    for meth in ("parse_args", "parse_known_args", "parse_intermixed_args",
                 "parse_known_intermixed_args"):
        orig = getattr(argparse.ArgumentParser, meth)

        def make(orig):
            def fake(self, *a, **k):
                if self.prog == "hermes" and "p" not in captured:
                    captured["p"] = self
                    raise _Captured()
                return orig(self, *a, **k)
            return fake
        setattr(argparse.ArgumentParser, meth, make(orig))

    saved_argv = sys.argv
    sys.argv = ["hermes", "doctor"]
    try:
        from hermes_cli.main import main  # type: ignore
        main()
    except _Captured:
        pass
    finally:
        sys.argv = saved_argv
    if "p" not in captured:
        sys.exit("ERROR: could not capture the hermes argparse parser")
    return captured["p"]


def _walk_parser(parser, path, out):
    flags, value_flags = set(), set()
    subs = {}
    positionals = []
    for a in parser._actions:
        if isinstance(a, argparse._SubParsersAction):
            subs.update(a.choices)
        elif a.option_strings:
            flags.update(a.option_strings)
            if a.nargs != 0:
                value_flags.update(a.option_strings)
        else:
            positionals.append(a.dest)
    out[" ".join(path)] = {
        "flags": sorted(flags),
        "value_flags": sorted(value_flags),
        "subcommands": sorted(subs),
        "positionals": positionals,
    }
    for name, sp in subs.items():
        _walk_parser(sp, path + [name], out)


def _flatten(d, prefix, out):
    for k, v in d.items():
        p = f"{prefix}.{k}" if prefix else str(k)
        out.add(p)
        if isinstance(v, dict):
            _flatten(v, p, out)


def _yaml_fences(text: str) -> list:
    """Bodies of ```yaml fences at any indentation (docs nest them in list items), dedented."""
    import textwrap
    return [textwrap.dedent(m.group(2)) for m in
            re.finditer(r"^([ \t]*)```ya?ml[^\n]*\n(.*?)^\1```", text, re.S | re.M)]


def _documented_keys(upstream: pathlib.Path, known_roots: set) -> set:
    """Config key paths shown in official docs YAML examples + cli-config.yaml.example.

    Some real keys (e.g. top-level ``model_aliases``) live outside DEFAULT_CONFIG.
    A root from the docs counts only if Hermes' own source mentions it as a string
    literal, which keeps compose files and other non-config YAML out.
    """
    import yaml  # type: ignore
    src_text = []
    for d in ("hermes_cli", "agent", "gateway", "tools", "cron"):
        for f in (upstream / d).rglob("*.py"):
            src_text.append(f.read_text(encoding="utf-8", errors="replace"))
    src_blob = "\n".join(src_text)

    blocks = []
    keys: set = set()
    for f in (upstream / "website" / "docs").rglob("*.md"):
        text = f.read_text(encoding="utf-8", errors="replace")
        blocks += _yaml_fences(text)
        # dotted keys the docs name in prose, e.g. `skills.creation_nudge_interval`
        for span in re.findall(r"`([a-z_][a-z0-9_]*(?:\.[a-z0-9_]+)+)`", text):
            if span.split(".")[0] in known_roots and not FILE_EXT.search(span):
                keys.add(span)
        # keys the docs set on the command line, e.g. `hermes config set model.lmstudio_load_mode jit`
        for span in re.findall(r"hermes config set ([a-z_][a-z0-9_]*(?:\.[a-z0-9_]+)+)", text):
            if span.split(".")[0] in known_roots:
                keys.add(span)
    example = upstream / "cli-config.yaml.example"
    if example.exists():
        blocks.append(example.read_text(encoding="utf-8", errors="replace"))

    for body in blocks:
        try:
            data = yaml.safe_load(body)
        except yaml.YAMLError:
            continue
        if not isinstance(data, dict):
            continue
        for root, val in data.items():
            root = str(root)
            if not re.fullmatch(r"[a-z][a-z0-9_]*", root):
                continue
            if root not in known_roots and f'"{root}"' not in src_blob:
                continue
            keys.add(root)
            if isinstance(val, dict):
                _flatten(val, root, keys)
    return keys


_INLINE_MD = re.compile(r"`([^`]*)`|\*\*([^*]*)\*\*|\*([^*]*)\*|__([^_]*)__|(?<!\w)_([^_]*)_(?!\w)")


def _slug(text: str) -> str:
    """Heading id as generated by GitHub / Docusaurus (github-slugger): markup is
    stripped first, so `write_approval` in a code span keeps its underscore."""
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)      # [text](url) -> text
    text = _INLINE_MD.sub(lambda m: next(g for g in m.groups() if g is not None), text)
    out = []
    for ch in text.strip().lower():
        if ch.isalnum() or ch in "_-":
            out.append(ch)
        elif ch == " ":
            out.append("-")
    return "".join(out)


def _docs_pages(upstream: pathlib.Path) -> dict:
    """URL path (relative to /docs/) -> heading anchors, for every official docs page."""
    root = upstream / "website" / "docs"
    pages = {}
    for f in list(root.rglob("*.md")) + list(root.rglob("*.mdx")):
        rel = f.relative_to(root).with_suffix("").as_posix()
        text = f.read_text(encoding="utf-8", errors="replace")
        m = re.search(r"^---\n.*?^slug:\s*(\S+).*?^---", text, re.S | re.M)
        if m:
            url = m.group(1).strip("/")
        elif rel == "index" or rel.endswith("/index"):
            url = rel[: -len("index")].rstrip("/")
        else:
            url = rel
        anchors, seen = set(), {}
        in_fence = False
        for line in text.splitlines():
            if line.lstrip().startswith(("```", "~~~")):
                in_fence = not in_fence
                continue
            hm = None if in_fence else re.match(r"^#{1,6}\s+(.*?)\s*$", line)
            if not hm:
                continue
            title = hm.group(1)
            explicit = re.search(r"\{#([\w-]+)\}\s*$", title)
            if explicit:
                anchors.add(explicit.group(1))
                continue
            base = _slug(title)
            n = seen.get(base, 0)
            seen[base] = n + 1
            anchors.add(base if n == 0 else f"{base}-{n}")
        pages[url] = sorted(anchors)
    return pages


def cmd_extract(args):
    upstream = pathlib.Path(args.upstream).resolve()
    sys.path.insert(0, str(upstream))
    # Importing Hermes initializes a Hermes home. Never touch the reader's real one.
    import os
    import tempfile
    os.environ.setdefault("HERMES_HOME", tempfile.mkdtemp(prefix="drift-guard-home-"))

    tree: dict = {}
    _walk_parser(_capture_parser(), ["hermes"], tree)
    try:
        from hermes_cli import _parser as hp  # type: ignore
        pre_flags = {flag: bool(takes_value)
                     for flag, takes_value in getattr(hp, "PRE_ARGPARSE_INHERITED_FLAGS", [])}
    except Exception:
        pre_flags = {}

    from hermes_cli import commands as hc  # type: ignore
    slash = {}
    for cmd in hc.COMMAND_REGISTRY:
        scope = "cli" if getattr(cmd, "cli_only", False) else (
            "gateway" if getattr(cmd, "gateway_only", False) else "both")
        for n in (cmd.name, *(getattr(cmd, "aliases", ()) or ())):
            slash[n] = scope

    from hermes_cli import config as hcfg  # type: ignore
    keys: set = set()
    _flatten(hcfg.DEFAULT_CONFIG, "", keys)
    extra_roots = sorted(getattr(hcfg, "_EXTRA_KNOWN_ROOT_KEYS", set()))
    keys |= _documented_keys(upstream, set(hcfg.DEFAULT_CONFIG) | set(extra_roots))

    env: set = set()
    try:
        from hermes_cli import config_defaults as hcd  # type: ignore
        env |= set(getattr(hcd, "OPTIONAL_ENV_VARS", {}).keys())
    except Exception:
        pass
    env_pat = re.compile(r"\b([A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+)\b")
    for f in list(upstream.rglob("*.py")) + list((upstream / "website" / "docs").rglob("*.md")) \
            + [upstream / ".env.example", upstream / "cli-config.yaml.example"]:
        if "node_modules" in f.parts or not f.is_file():
            continue
        try:
            env |= set(env_pat.findall(f.read_text(encoding="utf-8", errors="replace")))
        except OSError:
            pass

    skills = set()
    for base in ("skills", "optional-skills"):
        for sk in (upstream / base).rglob("SKILL.md"):
            m = re.search(r"^name:\s*['\"]?([A-Za-z0-9_.-]+)", sk.read_text(encoding="utf-8",
                          errors="replace"), re.M)
            skills.add(m.group(1) if m else sk.parent.name)
            skills.add(sk.parent.name)

    # Top-level keys the gateway reads straight from config.yaml without a
    # DEFAULT_CONFIG entry (gateway/config_loader.py _TOPLEVEL_BRIDGE).
    loader = upstream / "gateway" / "config_loader.py"
    if loader.exists():
        m = re.search(r"_TOPLEVEL_BRIDGE[^=]*=\s*\((.*?)\n\)", loader.read_text(encoding="utf-8"), re.S)
        if m:
            keys |= set(re.findall(r'\(\s*"([a-z_]+)",', m.group(1)))
            for presence_args in re.findall(r"_presence\(([^)]*)\)", m.group(1)):
                keys |= set(re.findall(r'"([a-z_]+)"', presence_args))

    # Toolset names: the static registry plus toolsets that tools and plugins
    # register at import time (e.g. plugins/platforms/a2a registers "a2a").
    toolset_names: set = {"all", "*"}
    try:
        import toolsets as _toolsets  # type: ignore  # upstream module
        toolset_names |= set(_toolsets.TOOLSETS)
    except Exception as e:  # pragma: no cover - reported, not fatal
        print(f"warning: could not import upstream toolsets: {e}", file=sys.stderr)
    for d in ("tools", "plugins"):
        for f in (upstream / d).rglob("*.py"):
            toolset_names |= set(re.findall(r'toolset="([a-z0-9_-]+)"',
                                            f.read_text(encoding="utf-8", errors="replace")))
    toolset_names.discard("example")

    version = ""
    pyproject = upstream / "pyproject.toml"
    if pyproject.exists():
        m = re.search(r'^version\s*=\s*"([^"]+)"', pyproject.read_text(), re.M)
        version = m.group(1) if m else ""

    surface = {
        "hermes_version": version,
        "cli": tree,
        "pre_argparse_flags": pre_flags,
        "slash": slash,
        "config_keys": sorted(keys | CURATED_KEYS | MODEL_KEYS),
        "extra_roots": extra_roots,
        "env": sorted(env),
        "skills": sorted(skills),
        "toolsets": sorted(toolset_names),
        "docs_pages": _docs_pages(upstream),
    }
    pathlib.Path(args.out).write_text(json.dumps(surface, indent=1, sort_keys=True))
    print(f"hermes {version}: {len(tree)} command paths, {len(slash)} slash names, "
          f"{len(surface['config_keys'])} config keys, {len(env)} env names, "
          f"{len(skills)} skill names, {len(surface['docs_pages'])} docs pages -> {args.out}",
          file=sys.stderr)


# --------------------------------------------------------------------------- check

class Surface:
    def __init__(self, data: dict, local_skills: set):
        self.version = data.get("hermes_version", "?")
        self.cli = data["cli"]
        self.pre_flags = data.get("pre_argparse_flags", {})
        self.slash = data["slash"]
        self.keys = set(data["config_keys"])
        self.roots = {k.split(".")[0] for k in self.keys} | set(data["extra_roots"])
        self.dynamic = set(DYNAMIC_PREFIXES) | set(data["extra_roots"])
        self.env = set(data["env"]) | GENERIC_ENV
        self.skills = set(data["skills"]) | local_skills
        self.toolsets = set(data.get("toolsets", []))
        self.mcp_servers: set = set()  # filled by cmd_check from the guide itself
        # Only names that look like Hermes/provider/platform settings are checked;
        # a user's own script variables (BACKUP_PASSPHRASE, ...) are not our business.
        prefixes = {n.split("_", 1)[0] + "_" for n in data["env"]
                    if n.startswith(("HERMES_", "GATEWAY_", "TERMINAL_"))}
        self.env_prefixes = tuple(prefixes | {"HERMES_", "GATEWAY_", "TERMINAL_"})
        self.env_suffixes = ("_API_KEY", "_ALLOWED_USERS", "_HOME_CHANNEL", "_BOT_TOKEN")
        self.docs = {k: set(v) for k, v in data.get("docs_pages", {}).items()}

    def env_checked(self, name: str) -> bool:
        return name.startswith(self.env_prefixes) or name.endswith(self.env_suffixes)

    def toolset_ok(self, name: str) -> bool:
        """MCP servers become `mcp-<server>` toolsets, so those are always accepted, as
        are `no_mcp` and bare names of MCP servers the guide itself defines (a platform's
        toolset list can allowlist servers by name, hermes_cli/tools_config.py)."""
        return (not self.toolsets or name in self.toolsets or name.startswith("mcp-")
                or name == "no_mcp" or name in self.mcp_servers)

    def key_ok(self, key: str) -> bool:
        parts = [p for p in key.split(".") if p]
        if not parts:
            return True
        # Placeholder segments (<task>, *, {name}) match anything at that level.
        if any(re.fullmatch(r"<[^>]+>|\*|\{[^}]+\}", p) for p in parts):
            prefix = []
            for p in parts:
                if re.fullmatch(r"<[^>]+>|\*|\{[^}]+\}", p):
                    break
                prefix.append(p)
            return self.key_ok(".".join(prefix)) if prefix else True
        if key in self.keys:
            return True
        for d in self.dynamic:
            if key == d or key.startswith(d + "."):
                return True
        return False


def _code_contexts(text: str):
    """Yield (kind, lang, line_no, content). kind: 'fence' | 'inline'."""
    lines = text.splitlines()
    in_fence, lang, ignore, fence_marker = False, "", False, ""
    prev = ""
    for i, line in enumerate(lines, 1):
        if "drift-guard: ignore-line" in line:
            prev = line
            continue
        s = line.strip()
        m = re.match(r"^(`{3,}|~{3,})\s*([\w+-]*)", s)
        if not in_fence and m:
            in_fence, fence_marker, lang = True, m.group(1), m.group(2).lower()
            ignore = "drift-guard: ignore" in prev
            continue
        if in_fence and s.startswith(fence_marker) and s.strip("`~") == "":
            in_fence = False
            prev = line
            continue
        if in_fence:
            if not ignore:
                yield "fence", lang, i, line
        else:
            for span in re.findall(r"(?<!`)`([^`\n]+)`(?!`)", line):
                yield "inline", "", i, span
        prev = line


def _fenced_blocks(text: str):
    """Yield (lang, start_line, block_text) for fenced blocks not marked ignore."""
    lines = text.splitlines()
    i, prev = 0, ""
    while i < len(lines):
        m = re.match(r"^\s*(`{3,}|~{3,})\s*([\w+-]*)", lines[i])
        if m:
            marker, lang, start = m.group(1), m.group(2).lower(), i + 1
            ignore = "drift-guard: ignore" in prev
            body = []
            i += 1
            while i < len(lines) and not (lines[i].strip().startswith(marker)
                                          and lines[i].strip().strip("`~") == ""):
                body.append(lines[i])
                i += 1
            if not ignore:
                yield lang, start, "\n".join(body)
        prev = lines[i] if i < len(lines) else ""
        i += 1


def _split_commands(line: str):
    """Split a shell line on operators and yield token lists starting at `hermes`."""
    line = re.sub(r"(^|\s)#.*$", "", line)          # strip comments
    line = re.sub(r"^\s*(\$|>|PS[^>]*>)\s+", "", line)  # strip prompts
    for seg in re.split(r"\|\||&&|[|;()]|\$\(|`", line):
        seg = seg.strip()
        seg = re.sub(r"^(sudo(\s+-\S+)*\s+|-u\s+\S+\s+|env\s+(-u\s+\S+\s+)*([A-Z_]+=\S+\s+)*"
                     r"|[A-Z_][A-Z0-9_]*=\S+\s+|exec\s+|time\s+|nohup\s+)+", "", seg)
        if not re.match(r"^hermes(\s|$)", seg):
            continue
        try:
            toks = shlex.split(seg, posix=True)
        except ValueError:
            toks = seg.split()
        # stop at redirections
        clean = []
        for t in toks:
            if t in (">", ">>", "<", "2>", "2>&1", "&>", "&") or t.startswith((">", "2>")):
                break
            clean.append(t)
        yield clean


def check_hermes_cmd(toks, surf: Surface):
    """Return an error string or None."""
    path = ["hermes"]
    node = surf.cli["hermes"]
    i = 1
    descended_leaf = False
    while i < len(toks):
        t = toks[i]
        if t in ("\\",):
            i += 1
            continue
        if t.startswith("-") and t != "-":
            flag = t.split("=", 1)[0]
            if flag in surf.pre_flags:  # e.g. -p/--profile, parsed before argparse
                i += 2 if surf.pre_flags[flag] and "=" not in t else 1
                continue
            if flag not in node["flags"]:
                # top-level flags are accepted anywhere by some subparsers
                if flag not in surf.cli["hermes"]["flags"]:
                    return f"unknown flag `{flag}` for `{' '.join(path)}`"
            if flag in node["value_flags"] and "=" not in t:
                i += 1
            i += 1
            continue
        if re.fullmatch(r"<[^>]*>|\[.*\]|\.\.\.|…", t) or t.startswith("<"):
            return None  # placeholder: stop verifying deeper
        if node["subcommands"] and not descended_leaf:
            if t in node["subcommands"]:
                path.append(t)
                node = surf.cli[" ".join(path)]
                i += 1
                continue
            if not node["positionals"]:
                return f"unknown subcommand `{t}` for `{' '.join(path)}`"
        descended_leaf = True  # positional argument; remaining non-flags are values
        i += 1
    return None


def toolset_args(toks, surf: Surface) -> list:
    """Toolset names a hermes invocation mentions: `tools enable|disable` arguments
    and -t/--toolsets values on the chat entry points (`hermes send -t` is not toolsets)."""
    path, node, i, names = ["hermes"], surf.cli["hermes"], 1, []
    top = surf.cli["hermes"]
    while i < len(toks):
        t = toks[i]
        if t.startswith("-") and t != "-":
            flag, _, inline = t.partition("=")
            if flag in surf.pre_flags:
                i += 2 if surf.pre_flags[flag] and not inline else 1
                continue
            takes_value = flag in node["value_flags"] or (
                flag not in node["flags"] and flag in top["value_flags"])
            value = inline or (toks[i + 1] if takes_value and i + 1 < len(toks) else "")
            if flag in ("-t", "--toolsets") and " ".join(path) in ("hermes", "hermes chat"):
                names += value.split(",")
            i += 2 if takes_value and not inline else 1
            continue
        if node["subcommands"] and t in node["subcommands"]:
            path.append(t)
            node = surf.cli[" ".join(path)]
            i += 1
            continue
        if " ".join(path) in ("hermes tools enable", "hermes tools disable"):
            names += t.split(",")
        i += 1
    # `server:tool` names one MCP tool (hermes tools disable github:create_issue)
    return [n for n in names if n and ":" not in n and not re.search(r"[<>…{}$]|\.\.\.", n)]


def _toolset_lists(data: dict):
    """(key, list) pairs of config values that name toolsets."""
    agent = data.get("agent")
    if isinstance(agent, dict) and isinstance(agent.get("disabled_toolsets"), list):
        yield "agent.disabled_toolsets", agent["disabled_toolsets"]
    pt = data.get("platform_toolsets")
    if isinstance(pt, dict):
        for plat, val in pt.items():
            if isinstance(val, list):
                yield f"platform_toolsets.{plat}", val


def check_file(path: pathlib.Path, surf: Surface, errors: list):
    rel = path.relative_to(REPO)
    text = path.read_text(encoding="utf-8")

    def err(line, msg):
        errors.append(f"{rel}:{line}: {msg}")

    # 0. links into the official docs must point at a page (and heading) that
    #    exists at the pinned tag
    if surf.docs:
        docs_re = re.compile(r"https://hermes-agent\.nousresearch\.com/docs/?([^\s)\"'>#]*)"
                             r"(?:#([^\s)\"'>]+))?")
        for ln, line in enumerate(text.splitlines(), 1):
            for m in docs_re.finditer(line):
                page = m.group(1).strip("/")
                if page.startswith("api/"):
                    continue  # generated JSON endpoints (model catalog), not pages
                if page not in surf.docs:
                    err(ln, f"official docs page not found at this tag: /docs/{page}")
                elif m.group(2) and m.group(2) not in surf.docs[page]:
                    err(ln, f"heading #{m.group(2)} not found on /docs/{page}")

    # 1. hermes invocations + config set/get keys + env vars + inline keys/slash
    for kind, lang, ln, content in _code_contexts(text):
        is_shell = kind == "inline" or lang in SHELL_LANGS
        if is_shell and "hermes" in content:
            for toks in _split_commands(content):
                e = check_hermes_cmd(toks, surf)
                if e:
                    err(ln, e)
                for name in toolset_args(toks, surf):
                    if not surf.toolset_ok(name):
                        err(ln, f"unknown toolset `{name}`")
                if len(toks) >= 4 and toks[1] == "config" and toks[2] in ("set", "get", "unset"):
                    k = toks[3]
                    if not k.startswith(("<", "…", "...")) and not surf.key_ok(k):
                        err(ln, f"unknown config key `{k}` in `hermes config {toks[2]}`")
        # env vars in code contexts (assignments or references)
        if kind == "fence" and lang in (SHELL_LANGS | {"dotenv", "env", "ini"}) or kind == "inline":
            for name in re.findall(r"(?<![\w.-])\$?\{?([A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+)\}?(?==|\b)",
                                   content):
                if surf.env_checked(name) and name not in surf.env:
                    err(ln, f"unknown environment variable `{name}`")
        if kind == "inline":
            span = content.strip()
            # config key like compression.threshold
            if re.fullmatch(r"[a-z_][a-z0-9_]*(\.[A-Za-z0-9_<>*{}-]+)+", span) \
                    and not FILE_EXT.search(span) and span.split(".")[0] in surf.roots:
                if not surf.key_ok(span):
                    err(ln, f"unknown config key `{span}`")
            # slash command like /compress here 10
            m = re.match(r"^/([a-z][a-z0-9_-]*)(\s|$)", span)
            if m and "/" not in span.split()[0][1:] and m.group(1) not in PATH_ROOTS:
                name = m.group(1)
                if name not in surf.slash and name not in surf.skills and name not in FOREIGN_SLASH:
                    err(ln, f"unknown slash command `/{name}`")
        elif lang in CHAT_LANGS:
            m = re.match(r"^\s*/([a-z][a-z0-9_-]*)(\s|$)", content)
            if m and m.group(1) not in PATH_ROOTS:
                name = m.group(1)
                if name not in surf.slash and name not in surf.skills and name not in FOREIGN_SLASH:
                    err(ln, f"unknown slash command `/{name}`")

    # 2. YAML config blocks
    try:
        import yaml  # type: ignore
    except ImportError:
        return
    for lang, start, body in _fenced_blocks(text):
        if lang not in ("yaml", "yml"):
            continue
        try:
            data = yaml.safe_load(body)
        except yaml.YAMLError as e:
            err(start, f"YAML block does not parse: {str(e).splitlines()[0]}")
            continue
        check_config_mapping(data, surf, lambda m, s=start: err(s, m))


def check_config_mapping(data, surf: Surface, report):
    if not isinstance(data, dict):
        return
    if not any(str(k) in surf.roots for k in data):
        return  # not a Hermes config block (compose file, frontmatter, ...)
    keys: set = set()
    _flatten_yaml(data, "", keys, surf)
    for k in sorted(keys):
        if not surf.key_ok(k):
            report(f"unknown config key `{k}`")
    for key, names in _toolset_lists(data):
        for name in names:
            if isinstance(name, str) and not surf.toolset_ok(name):
                report(f"unknown toolset `{name}` in `{key}`")


def _flatten_yaml(d, prefix, out, surf):
    for k, v in d.items():
        p = f"{prefix}.{k}" if prefix else str(k)
        out.add(p)
        if any(p == dp or p.startswith(dp + ".") for dp in surf.dynamic):
            continue
        if p == "model" and isinstance(v, dict):
            for mk in v:
                out.add(f"model.{mk}")
            continue
        if isinstance(v, dict):
            _flatten_yaml(v, p, out, surf)


def check_skill(path: pathlib.Path, errors: list):
    rel = path.relative_to(REPO)
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        errors.append(f"{rel}:1: missing YAML frontmatter")
        return
    import yaml  # type: ignore
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as e:
        errors.append(f"{rel}:1: frontmatter does not parse: {e}")
        return
    for field in ("name", "description"):
        if not fm.get(field):
            errors.append(f"{rel}:1: frontmatter missing `{field}`")
    name = str(fm.get("name", ""))
    if name and not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", name):
        errors.append(f"{rel}:1: skill name `{name}` must be lowercase letters, digits, hyphens")
    if name and name != path.parent.name:
        errors.append(f"{rel}:1: skill name `{name}` should match its folder `{path.parent.name}`")
    if len(str(fm.get("description", ""))) > 1024:
        errors.append(f"{rel}:1: description longer than 1024 chars")


def _user_defined_mcp_servers(md_files) -> set:
    """MCP server names the guide defines: `hermes mcp add <name>` and `mcp_servers:` YAML."""
    import yaml  # type: ignore
    names: set = set()
    for f in md_files:
        if not f.exists():
            continue
        text = f.read_text(encoding="utf-8")
        names |= set(re.findall(r"hermes mcp (?:add|install) ([a-z0-9][a-z0-9_-]*)", text))
        for body in _yaml_fences(text):
            try:
                data = yaml.safe_load(body)
            except yaml.YAMLError:
                continue
            if isinstance(data, dict) and isinstance(data.get("mcp_servers"), dict):
                names |= {str(k) for k in data["mcp_servers"]}
    return names


def _user_defined_commands(md_files) -> set:
    """Slash names the guide itself creates: bundles, example skills, quick commands."""
    import yaml  # type: ignore
    names: set = set()
    for f in md_files:
        if not f.exists():
            continue
        text = f.read_text(encoding="utf-8")
        names |= set(re.findall(r"hermes bundles create ([a-z][a-z0-9_-]*)", text))
        # example SKILL.md files shown in fences: frontmatter `name: <skill>`
        for front in re.findall(r"^```[a-z]*\n---\n(.*?)\n---", text, re.S | re.M):
            m = re.search(r"^name:\s*([a-z][a-z0-9_-]*)\s*$", front, re.M)
            if m:
                names.add(m.group(1))
        for body in _yaml_fences(text):
            try:
                data = yaml.safe_load(body)
            except yaml.YAMLError:
                continue
            if isinstance(data, dict) and isinstance(data.get("quick_commands"), dict):
                names |= {str(k) for k in data["quick_commands"]}
    return names


def cmd_check(args):
    data = json.loads(pathlib.Path(args.surface).read_text())
    local_skills = {p.parent.name for p in (REPO / "skills").rglob("SKILL.md")}
    md_files = [REPO / "README.md", *sorted((REPO / "guide").rglob("*.md")),
                *sorted((REPO / "templates").rglob("*.md")),
                *sorted((REPO / "skills").rglob("*.md"))]
    surf = Surface(data, local_skills | _user_defined_commands(md_files))
    surf.mcp_servers = _user_defined_mcp_servers(md_files)
    errors: list = []

    for f in md_files:
        if f.exists():
            check_file(f, surf, errors)

    import yaml  # type: ignore
    for f in sorted((REPO / "templates" / "config").glob("*.yaml")):
        rel = f.relative_to(REPO)
        try:
            data = yaml.safe_load(f.read_text(encoding="utf-8"))
        except yaml.YAMLError as e:
            errors.append(f"{rel}:1: does not parse: {e}")
            continue
        if not isinstance(data, dict):
            errors.append(f"{rel}:1: top level must be a mapping")
            continue
        keys: set = set()
        _flatten_yaml(data, "", keys, surf)
        for k in sorted(keys):
            if not surf.key_ok(k):
                errors.append(f"{rel}: unknown config key `{k}`")
        for key, names in _toolset_lists(data):
            for name in names:
                if isinstance(name, str) and not surf.toolset_ok(name):
                    errors.append(f"{rel}: unknown toolset `{name}` in `{key}`")

    for f in sorted((REPO / "skills").rglob("SKILL.md")):
        check_skill(f, errors)

    if errors:
        print(f"drift guard: {len(errors)} problem(s) vs Hermes {surf.version}\n")
        for e in errors:
            print("  " + e)
        return 1
    print(f"drift guard: OK — {len(md_files)} markdown files, templates and skills match "
          f"Hermes {surf.version}")
    return 0


def cmd_lint_skills(args):
    """Run upstream's own skill linter (tools/skill_linter.py) over skills/."""
    upstream = pathlib.Path(args.upstream).resolve()
    sys.path.insert(0, str(upstream))
    import os
    import tempfile
    os.environ.setdefault("HERMES_HOME", tempfile.mkdtemp(prefix="drift-guard-home-"))
    from tools.skill_linter import lint_skill  # type: ignore
    problems = 0
    for skill_md in sorted((REPO / "skills").rglob("SKILL.md")):
        for f in lint_skill(skill_md):
            problems += 1
            print(f"  {skill_md.relative_to(REPO)}: {f.severity} [{f.rule}] {f.message}")
    if problems:
        print(f"skill lint: {problems} finding(s)")
        return 1
    print("skill lint: OK (upstream tools/skill_linter.py, zero findings)")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("extract", help="build surface.json from an installed upstream checkout")
    e.add_argument("--upstream", required=True)
    e.add_argument("--out", default="surface.json")
    c = sub.add_parser("check", help="check the guide against surface.json")
    c.add_argument("--surface", default="surface.json")
    ls = sub.add_parser("lint-skills", help="run upstream's skill linter over skills/")
    ls.add_argument("--upstream", required=True)
    args = ap.parse_args()
    try:
        if args.cmd == "extract":
            cmd_extract(args)
            print(f"drift guard: surface written to {args.out}", file=sys.__stdout__)
            return 0
        if args.cmd == "lint-skills":
            return cmd_lint_skills(args)
        return cmd_check(args)
    except Exception:
        # Importing Hermes can swap out sys.stderr; make sure a crash is never silent.
        import traceback
        traceback.print_exc(file=sys.__stderr__)
        return 2


if __name__ == "__main__":
    sys.exit(main())
