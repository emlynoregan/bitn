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
from typing import Any, Dict, List
from datetime import datetime, timezone


def main():
    merged_input = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("processed/northern_argus_pass_03/merged.json")
    source_md = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("archive/markdown/1985-87_Northern__Argus.md")
    output_dir = Path(sys.argv[3]) if len(sys.argv) > 3 else Path("processed/northern_argus_pass_04")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Lazy import generic processor (ensure scripts directory on path)
    import sys as _sys
    _sys.path.append("scripts")
    from process_archive import ArchiveDocumentProcessor

    # Prepare checkpoint paths
    out_file = output_dir / "merged.json"
    checkpoint_file = output_dir / "checkpoint.json"
    state_file = output_dir / "checkpoint_state.json"
    manifest_path = output_dir / "manifest.json"

    # Load input merged records
    input_records = json.loads(merged_input.read_text(encoding="utf-8"))

    # Initialize processor and source lines
    proc = ArchiveDocumentProcessor()
    lines = proc.load_document(str(source_md))
    proc.source_lines = lines

    # Default state
    state: Dict[str, Any] = {
        "gap1_done": False,
        "reproc_processed_ids": [],
        "gap2_done": False,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "started_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }

    # If checkpoint exists, resume from it
    if checkpoint_file.exists() and state_file.exists():
        try:
            proc.all_records = json.loads(checkpoint_file.read_text(encoding="utf-8"))
            loaded_state = json.loads(state_file.read_text(encoding="utf-8"))
            if isinstance(loaded_state, dict):
                state.update(loaded_state)
            print("♻️  Resuming Pass 4 from checkpoint")
        except Exception:
            proc.all_records = input_records[:]
            print("⚠️  Failed to load checkpoint. Starting fresh from input.")
    else:
        proc.all_records = input_records[:]

    initial_count = len(proc.all_records)
    gap1 = 0
    reproc_success = 0
    gap2 = 0

    progress_file = output_dir / "progress.txt"

    def _parse_iso(ts: str) -> datetime:
        try:
            if ts and ts.endswith("Z"):
                ts = ts[:-1] + "+00:00"
            return datetime.fromisoformat(ts)
        except Exception:
            return datetime.now(timezone.utc)

    def _fmt_duration(seconds: float) -> str:
        try:
            seconds = int(max(0, seconds))
            h = seconds // 3600
            m = (seconds % 3600) // 60
            s = seconds % 60
            return f"{h:02d}:{m:02d}:{s:02d}"
        except Exception:
            return "00:00:00"

    def _progress_times(s: Dict[str, Any]) -> Dict[str, str]:
        now = datetime.now(timezone.utc)
        start = _parse_iso(s.get("started_at") or s.get("created_at"))
        elapsed = (now - start).total_seconds()
        done = len(s.get("reproc_processed_ids") or [])
        total = int(s.get("reproc_total") or 0)
        if done <= 0 or total <= 0:
            return {"elapsed": _fmt_duration(elapsed), "pred_total": "N/A", "eta": "N/A"}
        rate = done / elapsed if elapsed > 0 else 0
        if rate <= 0:
            return {"elapsed": _fmt_duration(elapsed), "pred_total": "N/A", "eta": "N/A"}
        pred_total = total / rate
        eta = max(0, pred_total - elapsed)
        return {"elapsed": _fmt_duration(elapsed), "pred_total": _fmt_duration(pred_total), "eta": _fmt_duration(eta)}

    def save_checkpoint(records: List[Dict[str, Any]], s: Dict[str, Any]):
        s["updated_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        checkpoint_file.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
        state_file.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")
        # Also persist a rolling manifest snapshot
        snapshot = {
            "input_file": str(merged_input).replace("\\", "/"),
            "source_md": str(source_md).replace("\\", "/"),
            "output_file": str(out_file).replace("\\", "/"),
            "checkpoint_file": str(checkpoint_file).replace("\\", "/"),
            "state_file": str(state_file).replace("\\", "/"),
            "resumable": True,
            "state": s,
            "counters": {
                "initial_records": initial_count,
                "gaps_filled_initial": gap1,
                "uncategorized_reprocessed": reproc_success,
                "gaps_filled_after_reprocess": gap2,
                "current_records": len(records),
                "reproc_total_candidates": state.get("reproc_total", 0),
                "reproc_completed": len(state.get("reproc_processed_ids", [])),
            },
        }
        manifest_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
        # Lightweight human-readable progress
        try:
            total = int(state.get("reproc_total") or 0)
            done = len(state.get("reproc_processed_ids") or [])
            times = _progress_times(s)
            progress_file.write_text(
                f"{datetime.now(timezone.utc).isoformat().replace('+00:00','Z')}  Reprocess: {done}/{total}  "
                f"elapsed {times['elapsed']} | total ~ {times['pred_total']} | ETA {times['eta']}\n",
                encoding="utf-8",
            )
        except Exception:
            pass

    # Step 1: initial gap fill (once)
    if not bool(state.get("gap1_done")):
        gap1 = proc.fill_gaps(str(source_md))
        state["gap1_done"] = True
        save_checkpoint(proc.all_records, state)
    else:
        # If resuming, recompute counters from current records
        gap1 = 0

    # Step 2: reprocess uncategorized incrementally with checkpointing
    processed_ids = set(state.get("reproc_processed_ids") or [])
    # Build a stable list of uncategorized record ids from current snapshot
    uncats: List[Dict[str, Any]] = [r for r in proc.all_records if (r.get("metadata") or {}).get("article_type") == "uncategorized"]
    total_uncats = len(uncats)
    state["reproc_total"] = total_uncats
    print(f"🔄 Reprocessing uncategorized incrementally: {total_uncats} candidates; {len(processed_ids)} already processed", flush=True)
    batch = 0
    try:
        for idx, uncat in enumerate(uncats, start=1):
            rid = uncat.get("record_id")
            if rid and rid in processed_ids:
                if idx % 10 == 0:
                    times = _progress_times(state)
                    print(
                        f"   ⏭️  [{idx}/{total_uncats}] Skipped already processed: {rid}  "
                        f"(elapsed {times['elapsed']} | total ~ {times['pred_total']} | ETA {times['eta']})",
                        flush=True,
                    )
                continue
            start_line = uncat.get("source_line_start")
            end_line = uncat.get("source_line_end")
            if not start_line or not end_line:
                state.setdefault("reproc_processed_ids", []).append(rid)
                times = _progress_times(state)
                print(
                    f"   ⚠️  [{idx}/{total_uncats}] Missing line bounds; keeping uncategorized: {rid}  "
                    f"(elapsed {times['elapsed']} | total ~ {times['pred_total']} | ETA {times['eta']})",
                    flush=True,
                )
                continue
            chunk_lines: List[str] = []
            for line_num in range(start_line, end_line + 1):
                if line_num <= len(proc.source_lines):
                    chunk_lines.append(proc.source_lines[line_num - 1])
            if not chunk_lines:
                state.setdefault("reproc_processed_ids", []).append(rid)
                times = _progress_times(state)
                print(
                    f"   ⚠️  [{idx}/{total_uncats}] No source lines; keeping uncategorized: {rid}  "
                    f"(elapsed {times['elapsed']} | total ~ {times['pred_total']} | ETA {times['eta']})",
                    flush=True,
                )
                continue
            times = _progress_times(state)
            print(
                f"   🎯  [{idx}/{total_uncats}] Reprocessing {rid} (lines {start_line}-{end_line})  "
                f"(elapsed {times['elapsed']} | total ~ {times['pred_total']} | ETA {times['eta']})",
                flush=True,
            )
            try:
                new_records = proc.process_chunk(chunk_lines, start_line, end_line, fail_fast=False, doc_path=str(source_md))
                if new_records:
                    try:
                        proc.all_records.remove(uncat)
                    except ValueError:
                        pass
                    proc.merge_records(new_records)
                    reproc_success += 1
                    times = _progress_times(state)
                    print(
                        f"      ✅ Extracted {len(new_records)} record(s) → replaced {rid}  "
                        f"(elapsed {times['elapsed']} | total ~ {times['pred_total']} | ETA {times['eta']})",
                        flush=True,
                    )
                else:
                    times = _progress_times(state)
                    print(
                        f"      ↪️  No structured records extracted; keeping uncategorized  "
                        f"(elapsed {times['elapsed']} | total ~ {times['pred_total']} | ETA {times['eta']})",
                        flush=True,
                    )
            except Exception as e:
                times = _progress_times(state)
                print(
                    f"      ⚠️  Error reprocessing: {e} — keeping uncategorized  "
                    f"(elapsed {times['elapsed']} | total ~ {times['pred_total']} | ETA {times['eta']})",
                    flush=True,
                )
            state.setdefault("reproc_processed_ids", []).append(rid)
            batch += 1
            # Save every 5 items to allow resume without rework
            if batch % 5 == 0:
                save_checkpoint(proc.all_records, state)
    except KeyboardInterrupt:
        # Always checkpoint on interrupt
        save_checkpoint(proc.all_records, state)
        times = _progress_times(state)
        print(
            f"\n🛑 Interrupted. Progress saved — you can rerun to resume.  "
            f"(elapsed {times['elapsed']} | total ~ {times['pred_total']} | ETA {times['eta']})",
            flush=True,
        )
        return

    # Final save after reprocess loop
    save_checkpoint(proc.all_records, state)

    # Step 3: final gap fill (once)
    if not bool(state.get("gap2_done")):
        gap2 = proc.fill_gaps(str(source_md))
        state["gap2_done"] = True
        save_checkpoint(proc.all_records, state)

    final_records = proc.all_records
    final_count = len(final_records)

    # Write final outputs
    out_file.write_text(json.dumps(final_records, ensure_ascii=False, indent=2), encoding="utf-8")

    # Build final manifest
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
        "checkpoint_file": str(checkpoint_file).replace("\\", "/"),
        "state_file": str(state_file).replace("\\", "/"),
        "resumable": True,
        "state": state,
        "counters": {
            "initial_records": initial_count,
            "gaps_filled_initial": gap1,
            "uncategorized_reprocessed": reproc_success,
            "gaps_filled_after_reprocess": gap2,
            "final_records": final_count,
        },
        "final_summary": summarize(final_records),
    }

    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"✅ Pass 4 complete → {out_file}")
    print(f"   Initial: {initial_count} | Gaps+first: {gap1} | Reproc(replaced): {reproc_success} | Gaps+second: {gap2} | Final: {final_count}")


if __name__ == "__main__":
    main()


