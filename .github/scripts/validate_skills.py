#!/usr/bin/env python3
"""Validate every skills/**/SKILL.md has correct frontmatter.

Run via: python .github/scripts/validate_skills.py
Exit code 0 = all pass; 1 = any fail. Each failing file is listed with reason.
"""
from __future__ import annotations

import pathlib
import re
import sys

import yaml

REQUIRED_KEYS = {"name", "description", "when_to_use", "toolsets"}
ALLOWED_TOOLSETS = {
    "terminal",
    "file",
    "github",
    "delegate_task",
    "classify",
    "telegram",
    "web",
    "browser",
    "email",
    "discord",
    "slack",
    "memory",
}

KEBAB_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)


def extract_frontmatter(p: pathlib.Path) -> dict | None:
    # utf-8-sig strips a BOM if present; normalize CRLF so the regex matches.
    text = p.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None
    try:
        return yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as e:
        print(f"  yaml parse error: {e}")
        return None


def validate_parameters(params: object) -> list[str]:
    """Accept either shape used in the wild:

    - list form:    [{name: pr, type: string, required: true}, ...]
    - mapping form:  {pr: {type: string, required: true}, ...}

    Both normalize to (name, spec) pairs validated identically.
    """
    errs: list[str] = []
    if isinstance(params, dict):
        pairs = [(str(k), v, f"parameters.{k}") for k, v in params.items()]
    elif isinstance(params, list):
        pairs = []
        for i, item in enumerate(params):
            if not isinstance(item, dict):
                errs.append(f"parameters[{i}] must be a mapping, got {type(item).__name__}")
                continue
            name = item.get("name")
            if not isinstance(name, str) or not name:
                errs.append(f"parameters[{i}] missing/invalid 'name' (non-empty string required)")
                continue
            spec = {k: v for k, v in item.items() if k != "name"}
            pairs.append((name, spec, f"parameters[{i}]"))
    else:
        return ["parameters must be a list of {name, type, required?} mappings or a name->spec mapping"]

    for name, spec, where in pairs:
        if not isinstance(spec, dict):
            errs.append(f"{where} spec must be a mapping, got {type(spec).__name__}")
            continue
        if not isinstance(spec.get("type"), str) or not spec.get("type"):
            errs.append(f"{where} missing/invalid 'type' (non-empty string required)")
        if "required" in spec and not isinstance(spec["required"], bool):
            errs.append(f"{where}.required must be a boolean")
        unknown = set(spec) - {"type", "required", "description", "default", "enum"}
        if unknown:
            errs.append(f"{where} has unknown keys: {sorted(unknown)}")
    return errs


def validate(p: pathlib.Path) -> list[str]:
    errs: list[str] = []
    fm = extract_frontmatter(p)
    if fm is None:
        return ["missing or unparseable frontmatter"]

    missing = REQUIRED_KEYS - set(fm.keys())
    if missing:
        errs.append(f"missing required keys: {sorted(missing)}")

    name = fm.get("name")
    if isinstance(name, str):
        if not KEBAB_RE.match(name):
            errs.append(f"name '{name}' is not kebab-case")
        if name != p.parent.name:
            errs.append(f"name '{name}' != parent directory '{p.parent.name}' (cron wiring depends on this)")
    elif "name" in fm:
        errs.append("name must be a string")

    toolsets = fm.get("toolsets", [])
    if not isinstance(toolsets, list):
        errs.append("toolsets must be a list")
    else:
        unknown = [t for t in toolsets if t not in ALLOWED_TOOLSETS]
        if unknown:
            errs.append(f"unknown toolsets: {unknown} (allowed: {sorted(ALLOWED_TOOLSETS)})")

    when = fm.get("when_to_use", [])
    if not isinstance(when, list) or not when:
        errs.append("when_to_use must be a non-empty list of triggers")

    desc = fm.get("description", "")
    if not isinstance(desc, str) or len(desc) < 10:
        errs.append("description must be a >=10-char string")

    if "parameters" in fm:
        errs.extend(validate_parameters(fm["parameters"]))

    return errs


def main() -> int:
    root = pathlib.Path(__file__).resolve().parents[2] / "skills"
    if not root.is_dir():
        print(f"::error::no skills/ dir at {root}")
        return 1

    skills = sorted(root.rglob("SKILL.md"))
    if not skills:
        print(f"::warning::no SKILL.md files found under {root}")
        return 0

    total_fails = 0
    seen_names: dict[str, pathlib.Path] = {}
    for p in skills:
        rel = p.relative_to(root.parent)
        errs = validate(p)

        fm = extract_frontmatter(p)
        name = fm.get("name") if isinstance(fm, dict) else None
        if isinstance(name, str):
            if name in seen_names:
                errs.append(f"duplicate skill name '{name}' (also in {seen_names[name].relative_to(root.parent)})")
            else:
                seen_names[name] = p

        if errs:
            total_fails += 1
            print(f"::error file={rel}::{'; '.join(errs)}")
        else:
            print(f"ok  {rel}")

    if total_fails:
        print(f"\n{total_fails}/{len(skills)} skill(s) failed validation", file=sys.stderr)
        return 1

    print(f"\nAll {len(skills)} skill(s) passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
