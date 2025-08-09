#!/usr/bin/env python3
"""
Backfill missing metadata (date, volume, issue_number, page) in chunk records
by deriving an ordered list of "issue header" anchors from existing chunk
outputs themselves, then propagating those anchors forward by source lines.

Usage:
  python scripts/backfill_chunk_metadata.py [chunks_dir]

Default chunks_dir: processed/chunks
"""

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


HEADER_RE = re.compile(r"^[CXLVI]+\s*,\s*[^,]+\s*,\s*.+", re.IGNORECASE)


def is_header_like(record: Dict[str, Any]) -> bool:
    meta = record.get("metadata") or {}
    original_text = (record.get("original_text") or "").strip()
    # Consider it a header anchor if it carries a date and at least one of volume/issue/page
    has_date = bool(meta.get("date"))
    has_any_vip = bool(meta.get("volume") or meta.get("issue_number") or meta.get("page"))
    if has_date and has_any_vip:
        return True
    # Or if the text looks like an issue header line 'CXV, 8027, 9 October 1985, page 21'
    return bool(HEADER_RE.match(original_text))


def load_all_records(chunks_dir: Path) -> List[Tuple[Path, Dict[str, Any]]]:
    records: List[Tuple[Path, Dict[str, Any]]] = []
    for p in sorted(chunks_dir.glob("chunk_*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(data, list):
                for rec in data:
                    records.append((p, rec))
        except Exception:
            continue
    return records


def parse_header_from_record(rec: Dict[str, Any]) -> Dict[str, Any]:
    meta = rec.get("metadata") or {}
    if meta.get("date") or meta.get("volume") or meta.get("issue_number") or meta.get("page"):
        return {
            "date": meta.get("date"),
            "volume": meta.get("volume"),
            "issue_number": meta.get("issue_number"),
            "page": meta.get("page"),
        }
    # Fallback: try to parse original_text
    text = (rec.get("original_text") or "").strip()
    parts = [p.strip() for p in text.split(",")]
    volume = parts[0] if parts else None
    issue_number = parts[1] if len(parts) > 1 else None
    # Date part is parts[2] if present; leave as-is (we won't hard-parse here)
    date_raw = parts[2] if len(parts) > 2 else None
    page = None
    # Look for 'page' or 'pages' token in remainder
    m = re.search(r"\bpage[s]?\s+[^,]+", text, flags=re.IGNORECASE)
    if m:
        page = m.group(0)
    return {
        "date": date_raw,
        "volume": volume,
        "issue_number": issue_number,
        "page": page,
    }


def main():
    chunks_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("processed/chunks")
    if not chunks_dir.exists():
        print(f"❌ Chunks directory not found: {chunks_dir}")
        sys.exit(1)

    pairs = load_all_records(chunks_dir)
    if not pairs:
        print("❌ No chunk records found")
        sys.exit(1)

    # Build anchors from header-like records, keyed by source_line_start
    anchors: List[Tuple[int, Dict[str, Any]]] = []
    for _path, rec in pairs:
        if is_header_like(rec):
            start = rec.get("source_line_start") or 0
            if start:
                anchors.append((int(start), parse_header_from_record(rec)))
    anchors.sort(key=lambda t: t[0])

    if not anchors:
        print("⚠️ No header-like anchors found; nothing to backfill")
        sys.exit(0)

    # Backfill: for each record in ascending line order, carry forward last anchor
    pairs_sorted = sorted(pairs, key=lambda pr: (int(pr[1].get("source_line_start") or 0)))
    backfilled = 0
    total = 0
    ai = 0
    current = anchors[0][1]

    for path, rec in pairs_sorted:
        total += 1
        start = int(rec.get("source_line_start") or 0)
        while ai + 1 < len(anchors) and start >= anchors[ai + 1][0]:
            ai += 1
            current = anchors[ai][1]

        meta = rec.get("metadata") or {}
        changed = False
        # Only fill when missing/empty
        for key in ("date", "volume", "issue_number", "page"):
            if not meta.get(key) and current.get(key):
                meta[key] = current.get(key)
                changed = True
        if changed:
            rec["metadata"] = meta
            backfilled += 1

    # Write records back to their files (group by path)
    by_path: Dict[Path, List[Dict[str, Any]]] = {}
    for path, rec in pairs_sorted:
        by_path.setdefault(path, []).append(rec)

    for path, recs in by_path.items():
        path.write_text(json.dumps(recs, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"✅ Backfilled {backfilled} of {total} records using {len(anchors)} anchors")


if __name__ == "__main__":
    main()


