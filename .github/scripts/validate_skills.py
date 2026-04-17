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

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)


def extract_frontmatter(p: pathlib.Path) -> dict | None:
    text = p.read_text(encoding="utf-8")
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None
    try:
        return yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as e:
        print(f"  yaml parse error: {e}")
        return None


def validate(p: pathlib.Path) -> list[str]:
    errs: list[str] = []
    fm = extract_frontmatter(p)
    if fm is None:
        return ["missing or unparseable frontmatter"]

    missing = REQUIRED_KEYS - set(fm.keys())
    if missing:
        errs.append(f"missing required keys: {sorted(missing)}")

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
    for p in skills:
        rel = p.relative_to(root.parent)
        errs = validate(p)
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
