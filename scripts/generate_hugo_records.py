#!/usr/bin/env python3
"""
Generate Hugo content and search index from pass 04 merged records.

Creates:
- site/content/records/_index.md
- site/content/records/<record_id>.md (content records only)
- site/static/js/search-data.json (records index for Lunr.js)
- Copies source markdown files referenced to site/static/downloads/markdown/

Usage:
  python scripts/generate_hugo_records.py [merged_json]

Default merged_json: processed/northern_argus_pass_04/merged.json
"""

import json
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List


REPO_ROOT = Path(__file__).resolve().parents[1]
SITE_DIR = REPO_ROOT / "site"
CONTENT_DIR = SITE_DIR / "content" / "records"
STATIC_DL_DIR = SITE_DIR / "static" / "downloads" / "markdown"
SEARCH_DATA = SITE_DIR / "static" / "js" / "search-data.json"


def as_yaml_front_matter(d: Dict[str, Any]) -> str:
    # Minimal YAML emitter for simple types
    import yaml  # type: ignore
    return "---\n" + yaml.safe_dump(d, sort_keys=False, allow_unicode=True).strip() + "\n---\n\n"


def build_permalink(record_id: str) -> str:
    return f"/records/{record_id}/"


def excerpt(text: str, length: int = 200) -> str:
    t = " ".join(text.split())
    return t[:length] + ("…" if len(t) > length else "")


def main():
    merged_path = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO_ROOT / "processed" / "northern_argus_pass_04" / "merged.json"
    records: List[Dict[str, Any]] = json.loads(merged_path.read_text(encoding="utf-8"))

    CONTENT_DIR.mkdir(parents=True, exist_ok=True)
    STATIC_DL_DIR.mkdir(parents=True, exist_ok=True)

    # Write section index
    index_md = CONTENT_DIR / "_index.md"
    index_md.write_text(
        """
---
title: Records
description: Searchable, granular records extracted from the Burra in the News archive.
---

This section contains individual records (articles, notices, letters, etc.) extracted from the source documents. Use the site search to find records by keywords, people, places, and topics.
""".strip()
        + "\n",
        encoding="utf-8",
    )

    # Generate pages and search data
    search_items: List[Dict[str, Any]] = []

    # Copy known source markdown(s)
    # We copy the entire archive/markdown folder once; links will point to /downloads/markdown/<filename>
    src_md_root = REPO_ROOT / "archive" / "markdown"
    if src_md_root.exists():
        for p in src_md_root.glob("*.md"):
            target = STATIC_DL_DIR / p.name
            if not target.exists() or p.stat().st_mtime > target.stat().st_mtime:
                shutil.copy2(p, target)

    for r in records:
        if (r.get("record_kind") or "content").lower() != "content":
            continue
        meta = r.get("metadata") or {}
        record_id = r.get("record_id")
        if not record_id:
            start = r.get("source_line_start") or "unknown"
            record_id = f"northern_argus_content_{start}"
        permalink = build_permalink(record_id)
        headline = meta.get("headline") or excerpt(r.get("original_text") or "")

        # Write content file
        fm = {
            "title": headline,
            "type": "records",
            "slug": record_id,
            "url": permalink,
            "record_id": record_id,
            "date": meta.get("date"),
            "volume": meta.get("volume"),
            "issue_number": meta.get("issue_number"),
            "page": meta.get("page"),
            "article_type": meta.get("article_type"),
            "issue_reference": r.get("issue_reference"),
            "people_mentioned": meta.get("people_mentioned", []),
            "places_mentioned": meta.get("places_mentioned", []),
            "topics": meta.get("topics", []),
            "source_document": r.get("source_document"),
        }

        body_lines = []
        body_lines.append(r.get("original_text") or "")
        # Source download link
        source_doc = r.get("source_document") or ""
        download_url = ""
        if source_doc:
            src_name = Path(source_doc).name
            download_url = f"/downloads/markdown/{src_name}"
            body_lines.append("")
            body_lines.append(f"Source: [{src_name}]({download_url})")

        md_path = CONTENT_DIR / f"{record_id}.md"
        md_path.write_text(as_yaml_front_matter(fm) + "\n".join(body_lines) + "\n", encoding="utf-8")

        # Add to search index
        search_items.append({
            "title": headline,
            "url": permalink,
            "content": " ".join([
                r.get("original_text") or "",
                " ".join(meta.get("people_mentioned", [])),
                " ".join(meta.get("places_mentioned", [])),
                " ".join(meta.get("topics", [])),
            ]).strip(),
            "date": meta.get("date"),
            "type": meta.get("article_type"),
        })

    SEARCH_DATA.write_text(json.dumps(search_items, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ Generated {len(search_items)} record pages → {CONTENT_DIR}")
    print(f"✅ Updated search index → {SEARCH_DATA}")
    print(f"✅ Copied source markdowns → {STATIC_DL_DIR}")


if __name__ == "__main__":
    main()


