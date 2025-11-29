from __future__ import annotations

import re
import sys
import html
import string
import datetime as dt
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

try:
    import yaml
except ImportError:  # pragma: no cover - fallback to minimal parser
    yaml = None

REPO_ROOT = Path(__file__).resolve().parents[1]
NOTES_DIR = REPO_ROOT / "obsidian" / "CyberBits"
INDEX_PATH = REPO_ROOT / "index.md"


@dataclass
class Term:
    id: int
    slug: str
    category: str
    title: str
    one_liner: str
    note_path: Path

    @property
    def link(self) -> str:
        return self.note_path.as_posix()


def load_frontmatter(text: str, note_path: Path) -> dict:
    """Parse YAML frontmatter with PyYAML if available, otherwise a basic parser."""
    if yaml:
        try:
            return yaml.safe_load(text) or {}
        except yaml.YAMLError as exc:  # type: ignore[attr-defined]
            raise ValueError(f"Invalid YAML in {note_path}") from exc
    return parse_basic_frontmatter(text, note_path)


def parse_basic_frontmatter(text: str, note_path: Path) -> dict:
    """Minimal YAML subset parser (keys, scalars, simple lists) for offline use."""
    data: dict[str, object] = {}
    current_key: str | None = None

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line:
            continue

        if line.startswith("  - ") and current_key:
            data.setdefault(current_key, [])
            if isinstance(data[current_key], list):
                data[current_key].append(line[4:].strip())
            continue

        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()

            if value == "[]":
                data[key] = []
                current_key = None
            elif value:
                data[key] = coerce_scalar(value)
                current_key = None
            else:
                data[key] = []
                current_key = key
        else:
            raise ValueError(f"Cannot parse frontmatter line in {note_path}: {raw_line}")

    return data


def coerce_scalar(value: str) -> object:
    """Convert scalar strings to int when appropriate."""
    if value.isdigit():
        return int(value)
    return value


def parse_frontmatter_block(content: str, note_path: Path) -> tuple[dict, list[str]]:
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError(f"Missing frontmatter in {note_path}")

    end_index: int | None = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end_index = i
            break

    if end_index is None:
        raise ValueError(f"Frontmatter not terminated in {note_path}")

    fm_text = "\n".join(lines[1:end_index])
    body_lines = lines[end_index + 1 :]
    frontmatter = load_frontmatter(fm_text, note_path)
    return frontmatter, body_lines


def first_paragraph_after_heading(body_lines: list[str]) -> str:
    """Return the first non-empty paragraph after the H1 title."""
    heading_seen = False
    paragraph: list[str] = []

    for line in body_lines:
        if not heading_seen:
            if line.strip().startswith("#"):
                heading_seen = True
            continue

        if not line.strip():
            if paragraph:
                break
            continue

        paragraph.append(line.strip())

    return " ".join(paragraph).strip()


def clean_one_liner(text: str) -> str:
    """
    Normalize a one-liner by stripping markdown decorations and leading labels.

    Notes assume the summary is either in frontmatter or the first paragraph
    under the H1 title, often starting with "One-liner:" in bold.
    """
    text = re.sub(r"^\s*\*{0,2}One-liner:\*{0,2}\s*", "", text, flags=re.IGNORECASE)
    text = text.replace("**", "").replace("__", "")
    text = re.sub(r"\[\[(.+?)\]\]", r"\1", text)
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    return text


def extract_title(frontmatter: dict, body_lines: list[str], note_path: Path) -> str:
    if frontmatter.get("title"):
        return str(frontmatter["title"]).strip()

    for line in body_lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            title = stripped.lstrip("#").strip()
            if title:
                return title

    fallback = frontmatter.get("slug") or note_path.stem
    return str(fallback)


def extract_one_liner(frontmatter: dict, body_lines: list[str]) -> str:
    if isinstance(frontmatter.get("one_liner"), str):
        return clean_one_liner(frontmatter["one_liner"])

    paragraph = first_paragraph_after_heading(body_lines)
    return clean_one_liner(paragraph)


def parse_note(note_path: Path) -> Term:
    content = note_path.read_text(encoding="utf-8")
    frontmatter, body_lines = parse_frontmatter_block(content, note_path)

    if "id" not in frontmatter or "slug" not in frontmatter:
        raise ValueError(f"Note missing required fields (id/slug): {note_path}")

    try:
        note_id = int(frontmatter["id"])
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Invalid id in {note_path}") from exc

    slug = str(frontmatter["slug"]).strip()
    category = str(frontmatter.get("category", "uncategorized")).strip() or "uncategorized"
    title = extract_title(frontmatter, body_lines, note_path)
    one_liner = extract_one_liner(frontmatter, body_lines) or "Summary pending."

    relative_path = note_path.relative_to(REPO_ROOT)

    return Term(
        id=note_id,
        slug=slug,
        category=category,
        title=title,
        one_liner=one_liner,
        note_path=relative_path,
    )


def load_terms(notes_dir: Path) -> list[Term]:
    if not notes_dir.exists():
        raise FileNotFoundError(f"Notes directory not found: {notes_dir}")

    terms = [parse_note(path) for path in sorted(notes_dir.glob("*.md"))]
    return terms


def render_a_z_index(terms: Iterable[Term]) -> str:
    lines = ["## A-Z Index", ""]
    letters_present = {
        (t.title[0].upper() if t.title else "#") for t in terms
    } or set(string.ascii_uppercase)
    letter_links = [
        f"[{letter}](#az-{letter.lower()})"
        for letter in string.ascii_uppercase
        if letter in letters_present
    ]
    lines.append(" | ".join(letter_links))
    lines.append("")

    grouped: dict[str, list[Term]] = {}
    for term in sorted(terms, key=lambda t: t.title.lower()):
        letter = term.title[0].upper() if term.title else "#"
        grouped.setdefault(letter, []).append(term)

    for letter in sorted(grouped.keys()):
        lines.append(f'<h3 id="az-{letter.lower()}">{letter}</h3>')
        lines.append('<ul class="az-list">')
        for term in grouped[letter]:
            data_text = html.escape(
                f"{term.title} {term.one_liner} {term.category}".lower()
            )
            lines.append(
                f'<li class="searchable" data-text="{data_text}">'
                f'<a href="{term.link}">{html.escape(term.title)}</a>: '
                f'{html.escape(term.one_liner)}</li>'
            )
        lines.append("</ul>")
        lines.append("")
    return "\n".join(lines)


def render_by_category_index(terms: Iterable[Term]) -> str:
    from collections import defaultdict

    grouped: dict[str, list[Term]] = defaultdict(list)
    for term in terms:
        grouped[term.category].append(term)

    categories = sorted(grouped.keys(), key=lambda c: c.lower())

    lines = ["## By Category Index", ""]
    lines.append(
        " | ".join(
            f"[{cat.title()}](#category-{cat.lower()})" for cat in categories
        )
    )
    lines.append("")

    for category in categories:
        lines.append(f'<h3 id="category-{category.lower()}">{category.title()}</h3>')
        lines.append('<ul class="cat-list">')
        for term in sorted(grouped[category], key=lambda t: t.title.lower()):
            data_text = html.escape(
                f"{term.title} {term.one_liner} {term.category}".lower()
            )
            lines.append(
                f'<li class="searchable" data-text="{data_text}">'
                f'<a href="{term.link}">{html.escape(term.title)}</a>: '
                f'{html.escape(term.one_liner)}</li>'
            )
        lines.append("</ul>")
        lines.append("")

    return "\n".join(lines)


def build_index_content(terms: list[Term]) -> str:
    today = dt.date.today().isoformat()
    intro = (
        "# Cyber Bits\n\n"
        "Plain-language notebook of 128 core cyber, network, and automation terms for small businesses and home offices.\n\n"
        "Written for non-technical owners who want quick context without jargon. Visit the main site at https://example.com (placeholder).\n\n"
        "> This file is auto-generated by tools/build_index.py. Do not edit by hand.\n\n"
        f"Generated on {today}\n\n"
        "### Quick navigation\n"
        "- Jump by letter in the A-Z index below.\n"
        "- Jump by category in the By Category index below.\n"
        "- Use the search box to filter everything on this page.\n\n"
        '<label for="search-box"><strong>Search terms:</strong></label><br />\n'
        '<input type="text" id="search-box" placeholder="Type to filter terms..." />\n'
        '<div id="search-results-count"></div>\n\n'
    )

    parts = [
        intro,
        render_a_z_index(terms),
        render_by_category_index(terms),
        (
            "<script>\n"
            "(function(){\n"
            "  const input = document.getElementById('search-box');\n"
            "  if (!input) return;\n"
            "  const items = Array.from(document.querySelectorAll('li.searchable'));\n"
            "  const counter = document.getElementById('search-results-count');\n"
            "  function render() {\n"
            "    const q = input.value.trim().toLowerCase();\n"
            "    let visible = 0;\n"
            "    items.forEach(li => {\n"
            "      const text = (li.getAttribute('data-text') || '');\n"
            "      const match = !q || text.includes(q);\n"
            "      li.style.display = match ? '' : 'none';\n"
            "      if (match) visible += 1;\n"
            "    });\n"
            "    if (counter) counter.textContent = q ? `${visible} matches` : '';\n"
            "  }\n"
            "  input.addEventListener('input', render);\n"
            "})();\n"
            "</script>\n"
        ),
    ]
    return "\n".join(parts).rstrip() + "\n"


def main() -> None:
    try:
        terms = load_terms(NOTES_DIR)
    except Exception as exc:  # pragma: no cover - CLI helper
        sys.exit(str(exc))

    index_content = build_index_content(terms)
    INDEX_PATH.write_text(index_content, encoding="utf-8")
    print(f"Wrote index for {len(terms)} terms to {INDEX_PATH}")


if __name__ == "__main__":
    main()
