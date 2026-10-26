"""Build a title-only home index from content metadata and the canonical book."""
from __future__ import annotations

import html
import re
from pathlib import Path
from urllib.parse import quote

import yaml

MARKER = "<!-- CONTENT_INDEX -->"
LABELS = {"article": "文章", "book": "书籍"}


def metadata(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    match = re.match(r"\A---\n(.*?)\n---(?:\n|$)", text, re.S)
    if not match:
        raise ValueError(f"unclosed front matter: {path.name}")
    meta = yaml.safe_load(match[1]) or {}
    if not isinstance(meta, dict):
        raise ValueError(f"front matter must be a mapping: {path.name}")
    return meta


def title(path: Path) -> str:
    value = metadata(path).get("title")
    if value is None:
        value = next((line[2:].strip() for line in path.read_text(encoding="utf-8").splitlines() if line.startswith("# ")), None)
    if not isinstance(value, str) or not value.strip() or "\n" in value:
        raise ValueError(f"a single-line title is required: {path.name}")
    return value.strip()


def markdown_text(value: str) -> str:
    value = html.escape(value, quote=False)
    return re.sub(r"([\\`*{}\[\]()#+.!_|$])", r"\\\1", value)


def entries(content: Path, book: Path, spec: dict) -> list[dict]:
    """Typed README files are content units; topic/about/asset pages are not."""
    result = []
    for path in sorted(content.rglob("README.md")):
        meta = metadata(path)
        kind = meta.get("type")
        if kind is None:
            continue
        if not isinstance(kind, str) or kind not in LABELS:
            raise ValueError(f"content type must be article or book: {path.relative_to(content)}")
        rel = path.relative_to(content)
        if len(rel.parts) < 3:
            raise ValueError("content units must be inside a topic folder")
        # The imported source replaces this local reading-entry placeholder.
        if rel.parent.as_posix() == spec["mount"]:
            continue
        result.append({"title": title(path), "type": kind, "topic": rel.parts[0],
                       "href": rel.with_name("index.md").as_posix()})
    mount = Path(spec["mount"])
    if mount.is_absolute() or ".." in mount.parts or len(mount.parts) < 2:
        raise ValueError("external book mount must be inside a topic folder")
    result.append({"title": title(book / "README.md"), "type": "book", "topic": mount.parts[0],
                   "href": (mount / "index.md").as_posix()})
    return sorted(result, key=lambda entry: (entry["topic"], entry["title"].casefold(), entry["href"]))


def render(content: Path, book: Path, spec: dict) -> str:
    groups: dict[str, list[dict]] = {}
    for entry in entries(content, book, spec):
        groups.setdefault(entry["topic"], []).append(entry)
    lines = []
    for topic, items in groups.items():
        topic_page = content / topic / "README.md"
        if not topic_page.is_file():
            raise ValueError(f"topic README missing: {topic}")
        lines.extend([f"## {markdown_text(title(topic_page))}", ""])
        for item in items:
            label = LABELS[item["type"]]
            lines.append(f'- [{markdown_text(item["title"])}]({quote(item["href"], safe="/")}) <span class="content-kind">{label}</span>')
        lines.append("")
    return "\n".join(lines)


def update_home(home: Path, content: Path, book: Path, spec: dict) -> None:
    template = home.read_text(encoding="utf-8")
    if template.count(MARKER) != 1:
        raise ValueError("home page must contain exactly one CONTENT_INDEX marker")
    home.write_text(template.replace(MARKER, render(content, book, spec)), encoding="utf-8")
