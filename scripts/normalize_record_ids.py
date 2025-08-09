#!/usr/bin/env python3
"""
Normalize record_id values in a merged JSON to include record kind to avoid collisions.

For each record:
  record_id := northern_argus_<kind>_<source_line_start>

Usage:
  python scripts/normalize_record_ids.py [input_json] [output_json]

Defaults:
  input_json:  processed/northern_argus_pass_04/merged.json
  output_json: processed/northern_argus_pass_04/merged.json (in-place)
"""

import json
import sys
from pathlib import Path


def main():
    inp = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("processed/northern_argus_pass_04/merged.json")
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else inp

    data = json.loads(inp.read_text(encoding="utf-8"))
    changed = 0
    for r in data:
        kind = (r.get("record_kind") or "content").lower()
        start = r.get("source_line_start")
        if start:
            new_id = f"northern_argus_{kind}_{int(start)}"
            if r.get("record_id") != new_id:
                r["record_id"] = new_id
                changed += 1

    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ Normalized record_id for {changed} records → {out}")


if __name__ == "__main__":
    main()


