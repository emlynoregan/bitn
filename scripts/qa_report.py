#!/usr/bin/env python3
"""
QA report for Northern Argus merged output.

Checks:
- Counts by kind and article_type
- Missing metadata (date, volume, issue_number, page, headline)
- Duplicates by record_id and by (record_kind, source_line_start)
- Overlapping content record ranges
- Residual gaps with non-empty source lines
- Date format sanity
- issue_reference consistency with metadata

Usage:
  python scripts/qa_report.py [merged_json] [source_md]

Defaults:
  merged_json: processed/northern_argus_pass_04/merged.json
  source_md:   archive/markdown/1985-87_Northern__Argus.md
Outputs:
  processed/northern_argus_pass_04/qa_report.json
  processed/northern_argus_pass_04/qa_report.txt (human-readable)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple


DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def load_json_array(path: Path) -> List[Dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Input JSON must be an array of records")
    return data


def summarize(records: List[Dict[str, Any]], source_lines: List[str]) -> Dict[str, Any]:
    total = len(records)
    by_kind: Dict[str, int] = {}
    by_type: Dict[str, int] = {}
    missing = {"date": 0, "volume": 0, "issue_number": 0, "page": 0, "headline": 0}
    header_missing = {"date": 0, "volume": 0, "issue_number": 0, "page": 0}
    uncategorized = 0
    date_bad_format = 0
    issue_ref_mismatch = 0

    ids_seen = set()
    dup_record_id = 0
    key_seen = set()  # (kind, start)
    dup_kind_start = 0

    # Collect ranges for overlap/gap checks
    ranges: List[Tuple[int, int, str, str]] = []  # (start, end, kind, record_id)

    for r in records:
        kind = (r.get("record_kind") or "content").lower()
        by_kind[kind] = by_kind.get(kind, 0) + 1
        meta = r.get("metadata") or {}

        at = meta.get("article_type")
        if at:
            by_type[at] = by_type.get(at, 0) + 1
        if at == "uncategorized":
            uncategorized += 1

        # Missing metadata
        if kind != "header":
            for f in ("date", "volume", "issue_number", "page"):
                if not meta.get(f):
                    missing[f] += 1
            if not (meta.get("headline") or "").strip():
                missing["headline"] += 1
        else:
            for f in ("date", "volume", "issue_number", "page"):
                if not meta.get(f):
                    header_missing[f] += 1

        # Dates
        d = meta.get("date")
        if d and not DATE_RE.match(d):
            date_bad_format += 1

        # issue_reference consistency (relaxed)
        issue_ref = (r.get("issue_reference") or "").lower()
        if issue_ref:
            vol = (meta.get("volume") or "").lower()
            iss = (meta.get("issue_number") or "").lower()
            pg = meta.get("page")
            # Require only vol/issue to be present if provided
            need_ok = True
            if vol and vol not in issue_ref:
                need_ok = False
            if iss and iss not in issue_ref:
                need_ok = False
            # Page: only check when numeric; accept if missing/unknown
            if isinstance(pg, (int, str)) and str(pg).isdigit():
                if f"page {pg}" not in issue_ref and str(pg) not in issue_ref:
                    # still consider ok if ref contains 'page ?' or 'missing'
                    if not ("page ?" in issue_ref or "missing" in issue_ref):
                        need_ok = False
            # Date: do not enforce (prose vs ISO differences)
            if not need_ok:
                issue_ref_mismatch += 1

        # Duplicates
        rid = r.get("record_id")
        if rid is not None:
            if rid in ids_seen:
                dup_record_id += 1
            else:
                ids_seen.add(rid)
        start = int(r.get("source_line_start") or 0)
        key = (kind, start)
        if key in key_seen:
            dup_kind_start += 1
        else:
            key_seen.add(key)

        end = int(r.get("source_line_end") or start)
        ranges.append((start, end, kind, rid or ""))

    # Overlaps for content records
    content_ranges = sorted([(s, e, k, rid) for s, e, k, rid in ranges if k == "content"], key=lambda x: (x[0], x[1]))
    overlaps = []
    for i in range(len(content_ranges) - 1):
        s1, e1, _, rid1 = content_ranges[i]
        s2, e2, _, rid2 = content_ranges[i + 1]
        if s2 <= e1:  # overlap
            overlaps.append({"a": {"id": rid1, "start": s1, "end": e1}, "b": {"id": rid2, "start": s2, "end": e2}})
            if len(overlaps) >= 20:
                break

    # Residual gaps with non-empty content
    residual_gaps = []
    sorted_all = sorted(ranges, key=lambda x: x[0])
    for i in range(len(sorted_all) - 1):
        _, e1, _, _ = sorted_all[i]
        s2, _, _, _ = sorted_all[i + 1]
        if s2 > e1 + 1:
            gap_start = e1 + 1
            gap_end = s2 - 1
            # Inspect source
            slice_lines = source_lines[gap_start - 1: gap_end]
            if any((ln.strip() for ln in slice_lines)):
                residual_gaps.append({"start": gap_start, "end": gap_end})
                if len(residual_gaps) >= 20:
                    break

    report = {
        "totals": {"records": total},
        "by_kind": by_kind,
        "by_article_type": by_type,
        "uncategorized": uncategorized,
        "missing_metadata": missing,
        "headers_missing": header_missing,
        "duplicates": {"record_id": dup_record_id, "kind_start": dup_kind_start},
        "overlaps_sample": overlaps,
        "residual_gaps_sample": residual_gaps,
        "date_bad_format": date_bad_format,
        "issue_reference_mismatch": issue_ref_mismatch,
    }
    return report


def render_text(report: Dict[str, Any]) -> str:
    lines: List[str] = []
    t = report["totals"]["records"]
    lines.append(f"Records: {t}")
    lines.append(f"By kind: {report['by_kind']}")
    lines.append(f"By article_type (top 10): {dict(sorted(report['by_article_type'].items(), key=lambda kv: kv[1], reverse=True)[:10])}")
    lines.append(f"Uncategorized: {report['uncategorized']}")
    lines.append(f"Missing metadata (content): {report['missing_metadata']}")
    lines.append(f"Headers missing: {report['headers_missing']}")
    lines.append(f"Duplicates: {report['duplicates']}")
    lines.append(f"Date bad format: {report['date_bad_format']}")
    lines.append(f"Issue reference mismatches: {report['issue_reference_mismatch']}")
    if report["overlaps_sample"]:
        lines.append("Overlaps (sample):")
        for o in report["overlaps_sample"]:
            lines.append(f"  {o['a']}  vs  {o['b']}")
    if report["residual_gaps_sample"]:
        lines.append("Residual gaps with content (sample):")
        for g in report["residual_gaps_sample"]:
            lines.append(f"  {g['start']}-{g['end']}")
    return "\n".join(lines) + "\n"


def main():
    merged = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("processed/northern_argus_pass_04/merged.json")
    source = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("archive/markdown/1985-87_Northern__Argus.md")
    out_dir = merged.parent
    records = load_json_array(merged)
    source_lines = source.read_text(encoding="utf-8").splitlines(True)
    report = summarize(records, source_lines)
    (out_dir / "qa_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "qa_report.txt").write_text(render_text(report), encoding="utf-8")
    print("✅ QA report written:")
    print(f"   {out_dir / 'qa_report.json'}")
    print(f"   {out_dir / 'qa_report.txt'}")


if __name__ == "__main__":
    main()


