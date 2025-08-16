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
import re


REPO_ROOT = Path(__file__).resolve().parents[1]
SITE_DIR = REPO_ROOT / "site"
CONTENT_DIR = SITE_DIR / "content" / "records"
STATIC_DL_DIR = SITE_DIR / "static" / "downloads" / "markdown"
SEARCH_DIR = SITE_DIR / "static" / "js"
MANIFEST_PATH = SEARCH_DIR / "search-manifest.json"


def as_yaml_front_matter(d: Dict[str, Any]) -> str:
    # Minimal YAML emitter for simple types
    import yaml  # type: ignore
    return "---\n" + yaml.safe_dump(d, sort_keys=False, allow_unicode=True).strip() + "\n---\n\n"


def build_permalink(record_id: str) -> str:
    return f"/records/{record_id}/"


def excerpt(text: str, length: int = 200) -> str:
    t = " ".join(text.split())
    return t[:length] + ("…" if len(t) > length else "")


def slugify_from_source_document(source_document: str) -> str:
    """Create a stable slug prefix from a source document filename.
    Example: '1845-76_SA_Register.md' -> '1845_76_sa_register'
    """
    name = Path(source_document).stem if source_document else "record"
    s = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_")
    return s.lower() or "record"


def is_iso_date(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    return re.match(r"^\d{4}-\d{2}-\d{2}$", value) is not None


def hyphenize(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-").lower()


def dataset_base_from_path(merged_path: Path) -> str:
    """Infer dataset base name from processed path, e.g. 'northern_argus_pass_04' -> 'northern_argus'."""
    parent = merged_path.parent.name
    # Strip standard suffixes
    parent = re.sub(r"_pass_?0?4$", "", parent)
    parent = re.sub(r"_pass_?0?[1-9]$", "", parent)
    return parent


PUBLICATION_SLUG_MAP = {
    # Known processed dataset base name -> publication slug used for pages
    # This preserves consistency from source → JSON → publication pages
    "northern_argus": "northern-argus",
    "sa_register": "sa-register",
    "1876_79_record": "record-1876-79",
    "1880_99_record": "record-1880-99",
}


PUBLICATION_TITLES = {
    "northern-argus": "The Northern Argus",
    "sa-register": "The South Australian Register",
    "record-1876-79": "Burra in the News Record 1876–79",
    "record-1880-99": "Burra in the News Record 1880–99",
}


def infer_publication_slug(merged_path: Path, sample_source_document: str) -> str:
    base = dataset_base_from_path(merged_path)
    if base in PUBLICATION_SLUG_MAP:
        return PUBLICATION_SLUG_MAP[base]
    # Fallback to hyphenized dataset base
    cand = hyphenize(base)
    if cand:
        return cand
    # Last resort: derive from source document filename
    return hyphenize(slugify_from_source_document(sample_source_document)) or "record"


def compute_sha256_base64(data: bytes) -> str:
    import hashlib, base64
    digest = hashlib.sha256(data).digest()
    return "sha256-" + base64.b64encode(digest).decode("ascii")


def main():
    merged_path = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO_ROOT / "processed" / "northern_argus_pass_04" / "merged.json"
    records: List[Dict[str, Any]] = json.loads(merged_path.read_text(encoding="utf-8"))

    CONTENT_DIR.mkdir(parents=True, exist_ok=True)
    STATIC_DL_DIR.mkdir(parents=True, exist_ok=True)
    SEARCH_DIR.mkdir(parents=True, exist_ok=True)

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

    # Generate pages and per-publication search data
    search_items: List[Dict[str, Any]] = []

    # Copy known source markdown(s)
    # We copy the entire archive/markdown folder once; links will point to /downloads/markdown/<filename>
    src_md_root = REPO_ROOT / "archive" / "markdown"
    if src_md_root.exists():
        for p in src_md_root.glob("*.md"):
            target = STATIC_DL_DIR / p.name
            if not target.exists() or p.stat().st_mtime > target.stat().st_mtime:
                shutil.copy2(p, target)

    # Determine publication slug early using first content record that has a source_document
    sample_source = None
    for r in records:
        if (r.get("record_kind") or "content").lower() != "content":
            continue
        if r.get("source_document"):
            sample_source = r.get("source_document")
            break
    publication_slug = infer_publication_slug(merged_path, sample_source or "")

    for r in records:
        if (r.get("record_kind") or "content").lower() != "content":
            continue
        meta = r.get("metadata") or {}
        record_id = r.get("record_id")
        if not record_id:
            start = r.get("source_line_start") or "unknown"
            prefix = slugify_from_source_document(r.get("source_document") or "")
            record_id = f"{prefix}_content_{start}"
        permalink = build_permalink(record_id)
        headline = meta.get("headline") or excerpt(r.get("original_text") or "")

        # Write content file
        # Normalize date: Hugo requires parsable date in front matter; move non-ISO to separate field
        date_val = meta.get("date")
        hugo_date = date_val if is_iso_date(date_val) else None
        date_display = date_val if not is_iso_date(date_val) else None

        fm = {
            "title": headline,
            "type": "records",
            "slug": record_id,
            "url": permalink,
            "record_id": record_id,
            "date": hugo_date,
            "date_display": date_display,
            "volume": meta.get("volume"),
            "issue_number": meta.get("issue_number"),
            "page": meta.get("page"),
            "article_type": meta.get("article_type"),
            "issue_reference": r.get("issue_reference"),
            "people_mentioned": meta.get("people_mentioned", []),
            "places_mentioned": meta.get("places_mentioned", []),
            "topics": meta.get("topics", []),
            "source_document": r.get("source_document"),
            "publication_slug": publication_slug,
        }

        body_lines = []
        body_lines.append(r.get("original_text") or "")
        # Source publication link (to publication page)
        pub_title = PUBLICATION_TITLES.get(publication_slug, publication_slug.replace('-', ' ').title())
        publication_url = f"/publications/{publication_slug}/"
        body_lines.append("")
        body_lines.append(f"Source publication: [{pub_title}]({publication_url})")

        md_path = CONTENT_DIR / f"{record_id}.md"
        md_path.write_text(as_yaml_front_matter(fm) + "\n".join(body_lines) + "\n", encoding="utf-8")

        # Add to per-publication search index
        prefix = slugify_from_source_document(r.get("source_document") or "")
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
            "source": prefix,
            "publication_slug": publication_slug,
        })

    # Write per-publication search JSON
    dataset_filename = f"search-{publication_slug}.json"
    dataset_path = SEARCH_DIR / dataset_filename
    dataset_payload = {
        "slug": publication_slug,
        "title": PUBLICATION_TITLES.get(publication_slug, publication_slug.replace('-', ' ').title()),
        "docs": search_items,
    }
    dataset_json = json.dumps(dataset_payload, ensure_ascii=False, indent=2)
    dataset_path.write_text(dataset_json, encoding="utf-8")

    # Update manifest
    manifest = {"version": 1, "generatedAt": "", "datasets": []}
    if MANIFEST_PATH.exists():
        try:
            manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        except Exception:
            manifest = {"version": 1, "generatedAt": "", "datasets": []}
    # Upsert dataset entry
    checksum = compute_sha256_base64(dataset_json.encode("utf-8"))
    path_rel = f"js/{dataset_filename}"
    entry = {
        "slug": publication_slug,
        "title": PUBLICATION_TITLES.get(publication_slug, publication_slug.replace('-', ' ').title()),
        "path": path_rel,
        "docCount": len(search_items),
        "checksum": checksum,
    }
    found = False
    for i, ds in enumerate(manifest.get("datasets", [])):
        if ds.get("slug") == publication_slug:
            manifest["datasets"][i] = entry
            found = True
            break
    if not found:
        manifest.setdefault("datasets", []).append(entry)
    # Update timestamp
    from datetime import datetime, timezone
    manifest["generatedAt"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    # Persist manifest (sorted by title for stability)
    manifest["datasets"] = sorted(manifest.get("datasets", []), key=lambda d: d.get("title", d.get("slug", "")))
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"✅ Generated {len(search_items)} record pages → {CONTENT_DIR}")
    print(f"✅ Wrote per-publication search data → {dataset_path}")
    print(f"✅ Updated manifest → {MANIFEST_PATH} ({len(manifest.get('datasets', []))} datasets)")
    print(f"✅ Copied source markdowns → {STATIC_DL_DIR}")


if __name__ == "__main__":
    main()


