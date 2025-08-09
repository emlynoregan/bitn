#!/usr/bin/env python3
"""
Backfill missing metadata (date, volume, issue_number, page, issue_reference)
in a merged JSON (with interleaved header/content records) by propagating the
nearest preceding header anchor's metadata forward.

Usage:
  python scripts/backfill_merged_metadata.py [input_json] [output_json]

Defaults:
  input_json:  processed/northern_argus_pass_04/merged.json
  output_json: processed/northern_argus_pass_04/merged.backfilled.json
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List


def is_header(rec: Dict[str, Any]) -> bool:
    return (rec.get("record_kind") or "content").lower() == "header"


def build_issue_ref(vol: str, issue: str, date: str, page: Any) -> str:
    parts: List[str] = []
    if vol: parts.append(vol)
    if issue: parts.append(issue)
    if date: parts.append(date)
    if page not in (None, ""):
        parts.append(f"page {page}")
    return ", ".join(parts) if parts else ""


def main():
    inp = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("processed/northern_argus_pass_04/merged.json")
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("processed/northern_argus_pass_04/merged.backfilled.json")

    data = json.loads(inp.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        print("ERROR: input is not a JSON array")
        sys.exit(1)

    # Prepare header anchors sorted by source line
    anchors: List[Dict[str, Any]] = []
    for r in data:
        if is_header(r):
            meta = r.get("metadata") or {}
            if any([meta.get("date"), meta.get("volume"), meta.get("issue_number"), meta.get("page")]):
                anchors.append({
                    "start": int(r.get("source_line_start") or 0),
                    "date": meta.get("date"),
                    "volume": meta.get("volume"),
                    "issue_number": meta.get("issue_number"),
                    "page": meta.get("page"),
                })
    anchors.sort(key=lambda a: a["start"])

    def find_anchor(line: int) -> Dict[str, Any]:
        # binary search would be fine, but linear is OK for size here
        last = None
        for a in anchors:
            if a["start"] <= line:
                last = a
            else:
                break
        return last or {}

    filled_counts = {"date": 0, "volume": 0, "issue_number": 0, "page": 0, "issue_reference": 0}
    candidates = 0

    for r in data:
        if is_header(r):
            continue
        meta = r.get("metadata") or {}
        r["metadata"] = meta
        line = int(r.get("source_line_start") or 0)
        a = find_anchor(line)
        if not a:
            continue
        candidates += 1

        # backfill fields if missing/empty
        for field in ("date", "volume", "issue_number", "page"):
            if not meta.get(field) and a.get(field) not in (None, ""):
                meta[field] = a[field]
                filled_counts[field] += 1
        # issue_reference
        if not r.get("issue_reference"):
            ref = build_issue_ref(meta.get("volume"), meta.get("issue_number"), meta.get("date"), meta.get("page"))
            if ref:
                r["issue_reference"] = ref
                filled_counts["issue_reference"] += 1

    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest = {
        "input": str(inp).replace("\\", "/"),
        "output": str(out).replace("\\", "/"),
        "candidates": candidates,
        "filled": filled_counts,
        "total": len(data),
    }
    (out.parent / "backfill_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ Backfill complete → {out}")
    print(f"   Filled: {filled_counts}")


if __name__ == "__main__":
    main()


