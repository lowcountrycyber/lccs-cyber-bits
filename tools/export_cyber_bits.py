import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
DATA_PATH = REPO_ROOT / "data" / "cyber_bits.json"
OBSIDIAN_DIR = REPO_ROOT / "obsidian" / "CyberBits"
WEB_JSON_PATH = REPO_ROOT / "web" / "cyber_bits.json"


def load_cyber_bits() -> list[dict]:
    """Load Cyber Bits data from the repository data file."""
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Missing data file: {DATA_PATH}")
    try:
        return json.loads(DATA_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {DATA_PATH}") from exc


CYBER_BITS = load_cyber_bits()


def slug_to_wikilink(slug: str) -> str:
    """Convert slug to Obsidian [[Title]] link. We’ll look up the title."""
    term = next((t for t in CYBER_BITS if t["slug"] == slug), None)
    return f"[[{term['title']}]]" if term else ""


def render_markdown(term: dict) -> str:
    """Render one Cyber Bit as an Obsidian-ready Markdown note."""
    related_links = [
        slug_to_wikilink(s) for s in term.get("related", []) if slug_to_wikilink(s)
    ]
    related_block = ""
    if related_links:
        related_block = "\n\n**Related:** " + ", ".join(related_links)

    frontmatter = f"""---
id: {term['id']}
slug: {term['slug']}
category: {term['category']}
audience_level: {term['audience_level']}
aliases: []
tags:
  - cyber-bits
  - {term['category']}
---

"""

    body = f"""# {term['title']}

**One-liner:** {term['one_liner']}

**Why it matters for small businesses / home offices:** {term['owner_why_it_matters']}\
{related_block}
"""

    return frontmatter + body.strip() + "\n"


def export_obsidian_notes():
    OBSIDIAN_DIR.mkdir(parents=True, exist_ok=True)
    for term in CYBER_BITS:
        filename = OBSIDIAN_DIR / f"{term['id']:03d}-{term['slug']}.md"
        md = render_markdown(term)
        filename.write_text(md, encoding="utf-8")
    print(f"Wrote {len(CYBER_BITS)} Obsidian notes to {OBSIDIAN_DIR}")


def export_web_json():
    # Strip down to fields that the Wix front-end needs
    web_terms = [
        {
            "id": t["id"],
            "slug": t["slug"],
            "title": t["title"],
            "category": t["category"],
            "audience_level": t["audience_level"],
            "one_liner": t["one_liner"],
            "owner_why_it_matters": t["owner_why_it_matters"],
            "related": t["related"],
        }
        for t in CYBER_BITS
    ]
    WEB_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    WEB_JSON_PATH.write_text(json.dumps(web_terms, indent=2), encoding="utf-8")
    print(f"Wrote JSON for {len(web_terms)} terms to {WEB_JSON_PATH}")


if __name__ == "__main__":
    export_obsidian_notes()
    export_web_json()
