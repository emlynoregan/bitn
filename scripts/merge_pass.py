#!/usr/bin/env python3
"""
Merge and deduplicate per-chunk JSON outputs into a single ordered file.

Input: a directory containing chunk_*.json files (arrays of records)
Output: a single merged.json plus a manifest with counts and decisions

Deduplication key:
- (record_kind, source_line_start)  
  Default record_kind to "content" if absent for robustness.

Preference policy for duplicates (pick the best quality record):
- Prefer records with richer metadata (date, volume, issue_number, page)
- Prefer records with non-empty issue_reference
- Prefer records with headline and eric_notes
- Small bias for longer original_text

Usage:
  python scripts/merge_pass.py [input_dir] [output_file]

Defaults:
  input_dir = processed/northern_argus_pass_02
  output_file = processed/northern_argus_pass_03/merged.json
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, Tuple, List


def compute_quality_score(record: Dict[str, Any]) -> int:
    metadata = record.get("metadata") or {}
    score = 0
    # Metadata completeness
    if metadata.get("date"): score += 3
    if metadata.get("volume"): score += 2
    if metadata.get("issue_number"): score += 2
    if metadata.get("page") is not None: score += 1
    # Other helpful fields
    if record.get("issue_reference"): score += 1
    headline = (metadata.get("headline") or "").strip()
    if headline: score += 1
    eric_notes = metadata.get("eric_notes") or []
    if isinstance(eric_notes, list) and len(eric_notes) > 0:
        score += 1
    # Original text length (small bias only)
    original_text = (record.get("original_text") or "")
    score += min(len(original_text) // 400, 2)
    return score


def merge_records(input_dir: Path) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    files = sorted([p for p in input_dir.glob("chunk_*.json") if p.is_file()])
    dedup: Dict[Tuple[str, int], Dict[str, Any]] = {}
    reasons: Dict[str, int] = {"replaced_for_quality": 0, "skipped_missing_start": 0}
    stats = {
        "files_processed": 0,
        "records_seen": 0,
        "duplicates_resolved": 0,
        "by_kind": {"header": 0, "content": 0, "other": 0},
        "by_article_type": {},
    }

    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            # Skip malformed files silently but count as processed
            stats["files_processed"] += 1
            continue

        if not isinstance(data, list):
            stats["files_processed"] += 1
            continue

        for rec in data:
            stats["records_seen"] += 1
            kind = (rec.get("record_kind") or "content").lower()
            if kind not in ("header", "content"):
                stats["by_kind"]["other"] = stats["by_kind"].get("other", 0) + 1
            else:
                stats["by_kind"][kind] = stats["by_kind"].get(kind, 0) + 1

            meta = rec.get("metadata") or {}
            art = meta.get("article_type")
            if art:
                stats["by_article_type"][art] = stats["by_article_type"].get(art, 0) + 1

            start = rec.get("source_line_start")
            if start is None:
                reasons["skipped_missing_start"] += 1
                continue
            key = (kind, int(start))

            if key not in dedup:
                dedup[key] = rec
            else:
                # resolve by quality score
                old = dedup[key]
                new_score = compute_quality_score(rec)
                old_score = compute_quality_score(old)
                if new_score > old_score:
                    dedup[key] = rec
                    stats["duplicates_resolved"] += 1
                    reasons["replaced_for_quality"] += 1
                else:
                    # keep existing
                    stats["duplicates_resolved"] += 1

        stats["files_processed"] += 1

    merged = list(dedup.values())
    # Sort deterministically: by start line, then headers before content at same line
    def sort_key(r: Dict[str, Any]):
        k = (r.get("record_kind") or "content").lower()
        s = r.get("source_line_start") or 0
        kind_order = 0 if k == "header" else 1
        return (int(s), kind_order)

    merged.sort(key=sort_key)
    return merged, {"stats": stats, "reasons": reasons}


def main():
    input_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("processed/northern_argus_pass_02")
    output_file = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("processed/northern_argus_pass_03/merged.json")

    output_dir = output_file.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    merged, info = merge_records(input_dir)

    # Write merged output
    output_file.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")

    # Write manifest
    manifest = {
        "input_directory": str(input_dir).replace("\\", "/"),
        "output_file": str(output_file).replace("\\", "/"),
        **info,
        "counts": {
            "total_merged": len(merged),
            "by_kind": {},
            "by_article_type": {},
        },
    }
    # recount from merged for by_kind/article_type in final set
    by_kind: Dict[str, int] = {}
    by_article_type: Dict[str, int] = {}
    for r in merged:
        k = (r.get("record_kind") or "content").lower()
        by_kind[k] = by_kind.get(k, 0) + 1
        art = (r.get("metadata") or {}).get("article_type")
        if art:
            by_article_type[art] = by_article_type.get(art, 0) + 1

    manifest["counts"]["by_kind"] = by_kind
    manifest["counts"]["by_article_type"] = by_article_type

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"✅ Merged {info['stats']['files_processed']} files → {len(merged)} records")
    print(f"   Duplicates resolved: {info['stats']['duplicates_resolved']}")
    print(f"   Output: {output_file}")


if __name__ == "__main__":
    main()


