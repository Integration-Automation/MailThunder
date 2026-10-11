"""Protect literal mail-template examples during the GitHub Pages build."""
from __future__ import annotations

import argparse
import re
import subprocess
from html.parser import HTMLParser
from pathlib import Path

_OPENERS = re.compile(r"\{\{|\{%")
_REQUIRED_EXAMPLES = {"{{ }}", "{% if %}", "{% for %}"}


def protect_markdown(text: str) -> str:
    """Quote Liquid-looking delimiters in the body, preserving any YAML front matter."""
    lines = text.splitlines(keepends=True)
    boundary = 0
    if lines and lines[0].strip() == "---":
        for line in lines:
            boundary += len(line)
            if boundary > len(lines[0]) and line.strip() in {"---", "..."}:
                break
        else:
            raise ValueError("Markdown front matter has no closing delimiter")
    body = _OPENERS.sub(lambda match: '{{ "' + match.group(0) + '" }}', text[boundary:])
    return text[:boundary] + body


def prepare_pages(root: Path) -> None:
    """Prepare tracked Markdown only; never follow a path outside the checkout."""
    root = root.resolve()
    files = subprocess.run(
        ["git", "ls-files", "-z", "--", "*.md"], cwd=root, check=True,
        capture_output=True, text=True, timeout=30,
    ).stdout.split("\0")
    for name in filter(None, files):
        path = (root / name).resolve()
        if not path.is_relative_to(root):
            raise ValueError("Markdown path leaves the checkout")
        path.write_text(protect_markdown(path.read_text(encoding="utf-8")), encoding="utf-8")


class CodeExamples(HTMLParser):
    """Collect rendered code text, including nested syntax-highlighting spans."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.examples: set[str] = set()
        self._in_code = False
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, _attrs: list[tuple[str, str | None]]) -> None:
        if tag == "code":
            self._in_code = True
            self._parts = []

    def handle_data(self, data: str) -> None:
        if self._in_code:
            self._parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "code":
            self.examples.add("".join(self._parts))
            self._in_code = False


def verify_pages(site: Path) -> None:
    """Fail the build if any README loses its literal Jinja examples."""
    english = site / "index.html"
    if not english.is_file():
        english = site / "README.html"
    pages = [english, site / "README/README_zh-TW.html", site / "README/README_zh-CN.html"]
    for page in pages:
        parser = CodeExamples()
        parser.feed(page.read_text(encoding="utf-8"))
        if not _REQUIRED_EXAMPLES.issubset(parser.examples):
            raise ValueError(f"Rendered page lost literal template examples: {page.name}")


def main() -> None:
    """Prepare the checkout or verify the generated site."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", type=Path)
    args = parser.parse_args()
    if args.verify is not None:
        verify_pages(args.verify)
    else:
        prepare_pages(Path.cwd())


if __name__ == "__main__":
    main()
