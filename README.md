# Cyber Bits

Plain-language glossary of cyber, network, and automation basics for small businesses and home offices. This repository powers a browsable GitHub Pages notebook and a machine-readable glossary consumed by the main site.

## Repository layout
- `index.md` — auto-generated homepage and index for GitHub Pages (run `python tools/build_index.py`).
- `obsidian/CyberBits/*.md` — individual term notes with YAML frontmatter (id, slug, category, audience_level) and a one-liner in the first paragraph.
- `cyber_bits.json` — machine-readable glossary exposed at the repo root (mirrors the canonical data export).
- `tools/build_index.py` — generator script that scans the notes and overwrites `index.md`.
- `tools/export_cyber_bits.py` — helper for exporting notes/JSON from the canonical dataset (optional).

## Maintainer workflow
1. Edit or add notes under `obsidian/CyberBits/`. Keep the first paragraph after the H1 as the one-liner, or include `one_liner` in frontmatter.
2. Regenerate `index.md` with `python tools/build_index.py`.
3. Refresh `cyber_bits.json` from your canonical data export so the Wix site stays in sync.
4. Commit and push to update GitHub Pages and the published JSON.
