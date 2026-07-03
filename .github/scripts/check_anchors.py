#!/usr/bin/env python3
"""Check that every relative markdown link resolves.

For each *.md in the repo:
  - [text](./other.md)          -> other.md must exist
  - [text](./other.md#section)  -> other.md must exist AND contain a heading
                                   whose GitHub-style slug is `section`
  - [text](#section)            -> this file must contain that heading

External URLs (http/https/mailto/tel), pure images, and links inside fenced
code blocks are skipped. Slugs follow GitHub's algorithm: lowercase, strip
everything but word chars/spaces/hyphens, spaces -> hyphens, duplicates get
-1/-2/... suffixes. Explicit <a name="..."> / id="..." anchors also count.

Run via: python .github/scripts/check_anchors.py
Exit code 0 = all links resolve; 1 = violations (each printed as ::error).
"""
from __future__ import annotations

import pathlib
import re
import sys
import unicodedata
from urllib.parse import unquote

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

SKIP_DIRS = {".git", "node_modules", ".venv", "__pycache__"}
EXTERNAL_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")  # any URI scheme
LINK_RE = re.compile(r"(!?)\[(?:[^\[\]]|\[[^\]]*\])*\]\(\s*<?([^)<>\s]+)>?(?:\s+[\"'][^\"']*[\"'])?\s*\)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
EXPLICIT_ANCHOR_RE = re.compile(r"<a\s+(?:name|id)\s*=\s*[\"']([^\"']+)[\"']|\bid\s*=\s*[\"']([^\"']+)[\"']")

# strip inline markdown from heading text before slugging
INLINE_MD_RE = re.compile(r"`([^`]*)`|\*\*([^*]*)\*\*|\*([^*]*)\*|__([^_]*)__|_([^_]*)_")
HEADING_LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")


def github_slug(text: str) -> str:
    """GitHub heading slug: strip markdown, lowercase, keep word chars/hyphens,
    spaces -> hyphens."""
    text = HEADING_LINK_RE.sub(r"\1", text)
    text = INLINE_MD_RE.sub(lambda m: next(g for g in m.groups() if g is not None), text)
    text = unicodedata.normalize("NFC", text)
    out = []
    for ch in text:
        if ch.isalnum() or ch == "_":
            out.append(ch.lower())
        elif ch == " ":
            out.append("-")  # every space becomes a hyphen (GitHub does NOT collapse)
        elif ch == "-":
            out.append("-")
        # other punctuation dropped
    return "".join(out)


def iter_md_files() -> list[pathlib.Path]:
    files = []
    for p in sorted(REPO_ROOT.rglob("*.md")):
        if any(part in SKIP_DIRS for part in p.relative_to(REPO_ROOT).parts):
            continue
        files.append(p)
    return files


def strip_fences(lines: list[str]) -> list[str]:
    """Blank out lines inside fenced code blocks (keep line count stable)."""
    out = []
    fence = None
    for line in lines:
        m = FENCE_RE.match(line)
        if m:
            if fence is None:
                fence = m.group(1)
            elif m.group(1) == fence:
                fence = None
            out.append("")
            continue
        out.append("" if fence is not None else line)
    return out


def collect_anchors(p: pathlib.Path, cache: dict[pathlib.Path, set[str]]) -> set[str]:
    if p in cache:
        return cache[p]
    anchors: set[str] = set()
    text = p.read_text(encoding="utf-8-sig", errors="replace").replace("\r\n", "\n")
    lines = strip_fences(text.split("\n"))
    seen: dict[str, int] = {}
    for line in lines:
        m = HEADING_RE.match(line)
        if m:
            base = github_slug(m.group(2))
            n = seen.get(base, 0)
            seen[base] = n + 1
            anchors.add(base if n == 0 else f"{base}-{n}")
        for am in EXPLICIT_ANCHOR_RE.finditer(line):
            anchors.add(am.group(1) or am.group(2))
    cache[p] = anchors
    return anchors


def main() -> int:
    anchor_cache: dict[pathlib.Path, set[str]] = {}
    violations = 0

    for md in iter_md_files():
        rel = md.relative_to(REPO_ROOT)
        text = md.read_text(encoding="utf-8-sig", errors="replace").replace("\r\n", "\n")
        lines = strip_fences(text.split("\n"))
        for lineno, line in enumerate(lines, 1):
            line = re.sub(r"`[^`]*`", "``", line)  # links inside inline code aren't links
            for m in LINK_RE.finditer(line):
                is_image, target = m.group(1) == "!", m.group(2)
                target = unquote(target)
                if EXTERNAL_RE.match(target) or target.startswith("//"):
                    continue  # external URL or protocol-relative
                path_part, _, frag = target.partition("#")
                if path_part:
                    dest = (md.parent / path_part).resolve()
                    if not dest.exists():
                        violations += 1
                        print(f"::error file={rel},line={lineno}::broken link '{target}' — file not found")
                        continue
                else:
                    dest = md
                if is_image or not frag:
                    continue
                if dest.suffix.lower() != ".md" or dest.is_dir():
                    continue  # can't check anchors in non-markdown targets
                if frag not in collect_anchors(dest, anchor_cache):
                    violations += 1
                    where = "" if dest == md else f" in {dest.relative_to(REPO_ROOT)}"
                    print(f"::error file={rel},line={lineno}::broken anchor '#{frag}'{where} ('{target}')")

    if violations:
        print(f"\n{violations} broken relative link(s)/anchor(s)", file=sys.stderr)
        return 1
    print("All relative links and anchors resolve.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
