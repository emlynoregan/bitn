#!/usr/bin/env python3
"""
Pass 4: Gap fill and uncategorized reprocessing on merged output.

Reads pass 03 merged records, fills gaps using source markdown, reprocesses
uncategorized spans with focused LLM calls, fills any new gaps, and writes
results to an output directory.

Usage:
  python scripts/process_pass4.py [merged_input] [source_md] [output_dir]

Defaults:
  merged_input: processed/northern_argus_pass_03/merged.json
  source_md:    archive/markdown/1985-87_Northern__Argus.md
  output_dir:   processed/northern_argus_pass_04
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict


def main():
    merged_input = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("processed/northern_argus_pass_03/merged.json")
    source_md = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("archive/markdown/1985-87_Northern__Argus.md")
    output_dir = Path(sys.argv[3]) if len(sys.argv) > 3 else Path("processed/northern_argus_pass_04")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load merged records
    merged_records = json.loads(merged_input.read_text(encoding="utf-8"))

    # Lazy import generic processor (ensure scripts directory on path)
    import sys as _sys
    _sys.path.append("scripts")
    from process_archive import ArchiveDocumentProcessor

    proc = ArchiveDocumentProcessor()
    # Load source lines for gap detection and targeted reprocessing
    lines = proc.load_document(str(source_md))
    proc.source_lines = lines
    proc.all_records = merged_records[:]  # copy

    initial_count = len(proc.all_records)

    # Pass 4 steps
    gap1 = proc.fill_gaps(str(source_md))
    reproc = proc.reprocess_uncategorized_records(str(source_md))
    gap2 = proc.fill_gaps(str(source_md))

    final_records = proc.all_records
    final_count = len(final_records)

    # Write outputs
    out_file = output_dir / "merged.json"
    out_file.write_text(json.dumps(final_records, ensure_ascii=False, indent=2), encoding="utf-8")

    # Build manifest
    def summarize(records) -> Dict[str, Any]:
        by_kind: Dict[str, int] = {}
        by_type: Dict[str, int] = {}
        for r in records:
            k = (r.get("record_kind") or "content").lower()
            by_kind[k] = by_kind.get(k, 0) + 1
            t = (r.get("metadata") or {}).get("article_type")
            if t:
                by_type[t] = by_type.get(t, 0) + 1
        return {"by_kind": by_kind, "by_article_type": by_type}

    manifest = {
        "input_file": str(merged_input).replace("\\", "/"),
        "source_md": str(source_md).replace("\\", "/"),
        "output_file": str(out_file).replace("\\", "/"),
        "counters": {
            "initial_records": initial_count,
            "gaps_filled_initial": gap1,
            "uncategorized_reprocessed": reproc,
            "gaps_filled_after_reprocess": gap2,
            "final_records": final_count,
        },
        "final_summary": summarize(final_records),
    }

    (output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"✅ Pass 4 complete → {out_file}")
    print(f"   Initial: {initial_count} | Gaps+first: {gap1} | Reproc: {reproc} | Gaps+second: {gap2} | Final: {final_count}")


if __name__ == "__main__":
    main()


