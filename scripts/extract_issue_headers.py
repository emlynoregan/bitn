#!/usr/bin/env python3
"""
Extract issue headers from existing chunk JSON files and write a JSON index
mapping source_line_start to structured metadata (volume, issue_number, date, page).

Usage:
  python scripts/extract_issue_headers.py [chunks_dir] [output_json]

Defaults:
  chunks_dir: processed/chunks
  output_json: processed/issue_headers.json
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple


MONTHS = {
    # full
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
    # common abbreviations
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "sept": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}


def normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def parse_date(raw: str) -> Optional[str]:
    """Parse dates like '9 October 1985', '11 Dec. 1987', '27November 1985' to YYYY-MM-DD.
    Returns ISO string or None if unparseable.
    """
    if not raw:
        return None
    s = normalize_spaces(raw.replace(",", "").replace(".", "."))
    # Insert space between day and month if missing (e.g., 27November)
    s = re.sub(r"^(\d{1,2})([A-Za-z])", r"\1 \2", s)
    parts = s.split()
    if len(parts) < 3:
        return None
    day_part, month_part, year_part = parts[0], parts[1], parts[2]
    try:
        day = int(re.sub(r"\D", "", day_part))
    except ValueError:
        return None
    month_key = month_part.lower().rstrip(".")
    month = MONTHS.get(month_key)
    if not month:
        return None
    try:
        year = int(re.sub(r"\D", "", year_part))
    except ValueError:
        return None
    # Basic sanity
    if not (1 <= day <= 31 and 1 <= month <= 12 and 1800 <= year <= 2100):
        return None
    return f"{year:04d}-{month:02d}-{day:02d}"


def try_parse_header(line: str) -> Optional[Dict[str, Any]]:
    """Attempt to parse an issue header line. Expected formats include:
    - 'CXV, 8027, 9 October 1985, page 21'
    - 'CXV, 8029 (2), 20 November 1985, pages 1 & 2  Check this irregular numbering'
    - 'CXV, 8030 (2), 27November 1985, MISSING ...'
    - 'CXVI, 8091, 11 Feb. 1987, page 26'
    Returns dict with volume, issue_number, date_iso, page_raw, raw, flags.
    """
    raw = line.strip()
    # Quick guard: must start with roman-like volume and a comma
    if not re.match(r"^[CXLVI]+,", raw):
        return None
    # Split into up to 4 segments: volume, issue, date-ish, tail (page/MISSING/etc)
    segs = [seg.strip() for seg in raw.split(";")]
    # The file uses commas, not semicolons; split by first 3 commas robustly
    parts = [p.strip() for p in raw.split(",")]
    if len(parts) < 3:
        return None
    volume = parts[0]
    issue_number = parts[1]
    # Re-join the remainder as a date+tail string
    remainder = ",".join(parts[2:]).strip()
    # Attempt to extract date up to the next comma-term like 'page', 'pages', 'MISSING'
    m_date = re.match(r"^([^,]+)", remainder)
    date_raw = m_date.group(1).strip() if m_date else None
    date_iso = parse_date(date_raw) if date_raw else None
    # Tail after date
    tail = remainder[len(date_raw):].lstrip(", ") if date_raw else remainder
    page_raw = None
    flags: List[str] = []
    if tail:
        # Common tokens: page ?, page 26, pages 1 & 2, MISSING ...
        tail_l = tail.lower()
        if tail_l.startswith("page") or tail_l.startswith("pages"):
            # capture up to newline
            page_raw = tail.splitlines()[0].strip()
        if "missing" in tail_l:
            flags.append("missing_issue")
    return {
        "volume": volume,
        "issue_number": issue_number,
        "date_raw": date_raw,
        "date": date_iso,
        "page": page_raw,
        "raw": raw,
        "flags": flags,
    }


def is_header_like(rec: Dict[str, Any]) -> bool:
    meta = rec.get("metadata") or {}
    original_text = (rec.get("original_text") or "").strip()
    has_date = bool(meta.get("date"))
    has_any = bool(meta.get("volume") or meta.get("issue_number") or meta.get("page"))
    if has_date and has_any:
        return True
    # Fallback: textual pattern like 'CXV, 8027, 9 October 1985, page 21'
    return bool(re.match(r"^[CXLVI]+\s*,\s*[^,]+\s*,\s*.+", original_text))


def parse_from_record(rec: Dict[str, Any]) -> Dict[str, Any]:
    meta = rec.get("metadata") or {}
    # Prefer explicit metadata
    if meta.get("date") or meta.get("volume") or meta.get("issue_number") or meta.get("page"):
        return {
            "volume": meta.get("volume"),
            "issue_number": meta.get("issue_number"),
            "date": meta.get("date"),
            "page": meta.get("page"),
            "raw": rec.get("original_text"),
        }
    # Else attempt to parse from text (best-effort)
    text = (rec.get("original_text") or "").strip()
    parts = [p.strip() for p in text.split(",")]
    volume = parts[0] if parts else None
    issue_number = parts[1] if len(parts) > 1 else None
    date_raw = parts[2] if len(parts) > 2 else None
    date_iso = parse_date(date_raw) if date_raw else None
    mpage = re.search(r"\bpage[s]?\s+[^,]+", text, flags=re.IGNORECASE)
    page = mpage.group(0) if mpage else None
    return {
        "volume": volume,
        "issue_number": issue_number,
        "date": date_iso,
        "page": page,
        "raw": text,
    }


def extract_headers_from_chunks(chunks_dir: Path) -> List[Dict[str, Any]]:
    anchors: List[Tuple[int, Dict[str, Any]]] = []
    for p in sorted(chunks_dir.glob("chunk_*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(data, list):
            continue
        for rec in data:
            if not isinstance(rec, dict):
                continue
            if is_header_like(rec):
                start = rec.get("source_line_start") or 0
                if start:
                    anchors.append((int(start), parse_from_record(rec)))
    anchors.sort(key=lambda t: t[0])
    # Normalize to list of dicts with line
    results: List[Dict[str, Any]] = []
    for line, meta in anchors:
        m = dict(meta)
        m["line"] = line
        results.append(m)
    return results


def main():
    chunks_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("processed/chunks")
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("processed/issue_headers.json")

    if not chunks_dir.exists():
        print(f"❌ Chunks directory not found: {chunks_dir}")
        sys.exit(1)

    out.parent.mkdir(parents=True, exist_ok=True)

    headers = extract_headers_from_chunks(chunks_dir)
    payload = {
        "source": str(chunks_dir),
        "total_headers": len(headers),
        "headers": headers,
    }
    with out.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"✅ Extracted {len(headers)} headers from chunks → {out}")


if __name__ == "__main__":
    main()


