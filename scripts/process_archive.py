#!/usr/bin/env python3
"""
Archive Document Processor

Generic processor for BITN archive markdown documents using OpenAI's API.
Extracts individual records according to the configured instructions.
"""

import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from openai import OpenAI
except ImportError:
    print("ERROR: OpenAI library not installed. Run: pip install openai")
    sys.exit(1)


def slugify_prefix_from_path(doc_path: str) -> str:
    stem = Path(doc_path).stem.lower()
    # Collapse non-alphanumerics to underscores
    import re
    s = re.sub(r"[^a-z0-9]+", "_", stem).strip("_")
    return s or "doc"


class ArchiveDocumentProcessor:
    def __init__(self, config_path: str = "scripts/config.json"):
        self.config = self.load_config(config_path)
        self.client = OpenAI(api_key=self.config["openai_api_key"])
        self.instructions = self.load_instructions()
        self.all_records: List[Dict[str, Any]] = []
        self.chunk_count = 0
        self.source_lines: List[str] = []
        self.supports_temperature = True
        self.verify_model_available()

    def create_chat_completion(self, messages: List[Dict[str, str]], temperature: float, max_tokens: int):
        try:
            kwargs = {
                "model": self.config["model"],
                "messages": messages,
            }
            if self.supports_temperature and temperature is not None:
                kwargs["temperature"] = temperature
            kwargs["max_tokens"] = max_tokens
            return self.client.chat.completions.create(**kwargs)
        except Exception as e:
            err_text = str(e)
            if "max_tokens" in err_text and "not supported" in err_text:
                kwargs = {"model": self.config["model"], "messages": messages, "max_completion_tokens": max_tokens}
                if self.supports_temperature and temperature is not None:
                    kwargs["temperature"] = temperature
                return self.client.chat.completions.create(**kwargs)
            if ("temperature" in err_text and ("unsupported" in err_text.lower() or "Only the default" in err_text)):
                self.supports_temperature = False
                kwargs = {"model": self.config["model"], "messages": messages}
                token_key = "max_tokens"
                if "max_tokens" in err_text and "not supported" in err_text:
                    token_key = "max_completion_tokens"
                kwargs[token_key] = max_tokens
                return self.client.chat.completions.create(**kwargs)
            raise

    def verify_model_available(self) -> None:
        try:
            _ = self.create_chat_completion(
                messages=[{"role": "system", "content": "Health check"}, {"role": "user", "content": "ping"}],
                temperature=0.7,
                max_tokens=1,
            )
        except Exception as e:
            err_text = str(e)
            if ("model_not_found" in err_text) or ("does not exist" in err_text) or ("do not have access" in err_text):
                print(f"❌ The configured model '{self.config['model']}' is not available on this API key.")
                print("   Please update scripts/config.json to a supported model (e.g., 'gpt-4o-mini').")
                sys.exit(1)
            if ("temperature" in err_text and ("unsupported" in err_text.lower() or "Only the default" in err_text)):
                self.supports_temperature = False
                try:
                    _ = self.create_chat_completion(
                        messages=[{"role": "system", "content": "Health check"}, {"role": "user", "content": "ping"}],
                        temperature=None,
                        max_tokens=1,
                    )
                except Exception:
                    pass

    def load_config(self, config_path: str) -> Dict[str, Any]:
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            env_key = os.environ.get("OPENAI_API_KEY")
            if env_key:
                config["openai_api_key"] = env_key
            env_model = os.environ.get("OPENAI_MODEL")
            if env_model:
                config["model"] = env_model
            if config.get("openai_api_key") == "your-openai-api-key-here":
                print("ERROR: Please set your OpenAI API key in scripts/config.json")
                sys.exit(1)
            return config
        except FileNotFoundError:
            print(f"ERROR: Config file not found at {config_path}")
            sys.exit(1)
        except json.JSONDecodeError:
            print(f"ERROR: Invalid JSON in config file {config_path}")
            sys.exit(1)

    def load_instructions(self) -> str:
        path = self.config.get("instructions_path", "docs/Northern Argus Instructions.md")
        try:
            return Path(path).read_text(encoding='utf-8')
        except FileNotFoundError:
            print(f"ERROR: Instructions file not found at {path}")
            sys.exit(1)

    def load_document(self, doc_path: str) -> List[str]:
        try:
            return Path(doc_path).read_text(encoding='utf-8').splitlines(True)
        except FileNotFoundError:
            print(f"ERROR: Document not found at {doc_path}")
            sys.exit(1)

    def get_max_line_processed(self, records: List[Dict[str, Any]]) -> int:
        max_line = 0
        for record in records:
            source_line_end = record.get("source_line_end", 0)
            if source_line_end > max_line:
                max_line = source_line_end
        return max_line

    def merge_records(self, new_records: List[Dict[str, Any]]) -> int:
        if not new_records:
            return 0
        existing_ids = {record.get("record_id"): i for i, record in enumerate(self.all_records)}
        added_count = 0
        updated_count = 0
        for new_record in new_records:
            record_id = new_record.get("record_id")
            if not record_id:
                continue
            if record_id in existing_ids:
                existing_index = existing_ids[record_id]
                self.all_records[existing_index] = new_record
                updated_count += 1
            else:
                self.all_records.append(new_record)
                existing_ids[record_id] = len(self.all_records) - 1
                added_count += 1

        def sort_key(record):
            source_line = record.get("source_line_start", 99999)
            metadata = record.get("metadata") or {}
            date = metadata.get("date") or "1900-01-01"
            if source_line == 99999:
                try:
                    parts = (record.get("record_id") or "").split("_")
                    if parts and parts[-1].isdigit():
                        source_line = int(parts[-1])
                except Exception:
                    pass
            return (source_line, date)

        self.all_records.sort(key=sort_key)
        if updated_count:
            print(f"📊 Merge summary: {added_count} new, {updated_count} updated records")
        return added_count

    def fill_gaps(self, doc_path: str) -> int:
        if len(self.all_records) < 2:
            return 0
        gap_records: List[Dict[str, Any]] = []
        sorted_records = sorted(self.all_records, key=lambda r: r.get("source_line_start", 0))
        prefix = slugify_prefix_from_path(doc_path)
        for i in range(len(sorted_records) - 1):
            current_end = sorted_records[i].get("source_line_end", 0)
            next_start = sorted_records[i + 1].get("source_line_start", 0)
            if next_start > current_end + 1:
                gap_start = current_end + 1
                gap_end = next_start - 1
                gap_lines = []
                for line_num in range(gap_start, gap_end + 1):
                    if line_num <= len(self.source_lines):
                        gap_lines.append(self.source_lines[line_num - 1])
                if any(line.strip() for line in gap_lines):
                    gap_text = "".join(gap_lines).strip()
                    gap_records.append({
                        "record_id": f"{prefix}_content_{gap_start}",
                        "source_document": Path(doc_path).name,
                        "source_line_start": gap_start,
                        "source_line_end": gap_end,
                        "original_text": gap_text,
                        "metadata": {
                            "article_type": "uncategorized",
                            "headline": f"Gap content (lines {gap_start}-{gap_end})",
                            "note": "Content found between processed records - may need manual review",
                        },
                    })
        if gap_records:
            self.all_records.extend(gap_records)
            self.all_records.sort(key=lambda r: r.get("source_line_start", 0))
        return len(gap_records)

    def reprocess_uncategorized_records(self, doc_path: str) -> int:
        uncategorized_records = [r for r in self.all_records if (r.get("metadata") or {}).get("article_type") == "uncategorized"]
        if not uncategorized_records:
            return 0
        print(f"🔄 Attempting to reprocess {len(uncategorized_records)} uncategorized records...")
        reprocessed_count = 0
        records_to_remove = []
        records_to_add: List[Dict[str, Any]] = []
        for uncat_record in uncategorized_records:
            start_line = uncat_record.get("source_line_start")
            end_line = uncat_record.get("source_line_end")
            if not start_line or not end_line:
                continue
            chunk_lines = []
            for line_num in range(start_line, end_line + 1):
                if line_num <= len(self.source_lines):
                    chunk_lines.append(self.source_lines[line_num - 1])
            if not chunk_lines:
                continue
            print(f"  🎯 Reprocessing lines {start_line}-{end_line} (record {uncat_record.get('record_id')})")
            try:
                new_records = self.process_chunk(chunk_lines, start_line, end_line, doc_path=doc_path)
                if new_records:
                    print(f"    ✅ Successfully extracted {len(new_records)} records from uncategorized content")
                    records_to_remove.append(uncat_record)
                    records_to_add.extend(new_records)
                    reprocessed_count += 1
            except Exception as e:
                print(f"    ⚠️  Error reprocessing: {e} - keeping as uncategorized")
                continue
        for r in records_to_remove:
            if r in self.all_records:
                self.all_records.remove(r)
        if records_to_add:
            self.merge_records(records_to_add)
        return reprocessed_count

    def process_chunk(self, chunk_lines: List[str], start_line: int, end_line: int, temperature_override: float = None, fail_fast: bool = True, doc_path: str = "") -> List[Dict[str, Any]]:
        numbered_lines = []
        for i, line in enumerate(chunk_lines):
            line_num = start_line + i
            numbered_lines.append(f"{line_num:6d}→{line}")
        chunk_text = ''.join(numbered_lines)
        system_prompt = f"""You are processing a historical newspaper document according to these instructions:

{self.instructions}

IMPORTANT: You must return ONLY a valid JSON array of records. No other text, explanations, or markdown formatting."""
        user_prompt = f"""Current chunk (lines {start_line}-{end_line}):

IMPORTANT: Each line is prefixed with its actual line number in the format "LINE_NUMBER→CONTENT".
Use these line numbers for accurate source_line_start and source_line_end values.

{chunk_text}

Process this chunk according to the instructions and return a JSON array of records for all content you find."""
        try:
            response = self.create_chat_completion(
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                max_tokens=self.config["max_tokens"],
                temperature=(self.config["temperature"] if temperature_override is None else temperature_override),
            )
            content = response.choices[0].message.content.strip()
            try:
                records = json.loads(content)
                if not isinstance(records, list):
                    return []
                prefix = slugify_prefix_from_path(doc_path) if doc_path else "record"
                for record in records:
                    if not record.get("record_kind"):
                        record["record_kind"] = "content"
                    # Ensure source_document is set for downstream linking
                    if doc_path and not record.get("source_document"):
                        record["source_document"] = Path(doc_path).name
                    source_line_start = record.get("source_line_start")
                    if source_line_start:
                        kind = (record.get("record_kind") or "content").lower()
                        record["record_id"] = f"{prefix}_{kind}_{source_line_start}"
                    else:
                        print(f"WARNING: Record missing source_line_start: {record}")
                return records
            except json.JSONDecodeError as e:
                print(f"❌ JSON error in chunk {self.chunk_count + 1} ({start_line}-{end_line}): {e}")
                if fail_fast:
                    sys.exit(1)
                raise ValueError(f"INVALID_JSON_RESPONSE: {e}")
        except Exception as e:
            if fail_fast:
                print(f"❌ FATAL: Unexpected error processing chunk {self.chunk_count + 1}: {e}")
                print("🛑 Terminating to prevent data loss.")
                sys.exit(1)
            raise

    def split_into_chunks(self, total_lines: int, chunk_size: int, overlap_size: int) -> List[Dict[str, int]]:
        chunks = []
        start = 1
        while start <= total_lines:
            end = min(start + chunk_size - 1, total_lines)
            chunks.append({"start": start, "end": end})
            start = end - overlap_size + 1
            if start <= chunks[-1]["start"]:
                start = chunks[-1]["start"] + 1
        return chunks

    def process_document_per_chunk(self, doc_path: str, output_root: str = None):
        print(f"🚀 Per-chunk processing with {self.config['model']}")
        print(f"📁 Document: {doc_path}")
        print(f"🔧 Chunk size: {self.config['chunk_size']} | Overlap: {self.config['overlap_size']}")
        lines = self.load_document(doc_path)
        self.source_lines = lines
        total_lines = len(lines)
        output_dir = self.config.get("output_directory", "processed/chunks")
        run_dir = Path(output_root) if output_root else Path(output_dir)
        run_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = run_dir / "manifest.json"
        manifest = {"document": doc_path, "total_lines": total_lines, "chunks": []}
        if manifest_path.exists():
            try:
                prev = json.loads(manifest_path.read_text(encoding='utf-8'))
                if isinstance(prev, dict):
                    manifest.update({k: v for k, v in prev.items() if k != "chunks"})
                    if isinstance(prev.get("chunks"), list):
                        manifest["chunks"] = prev["chunks"]
            except Exception:
                pass
        chunks = self.split_into_chunks(total_lines, self.config["chunk_size"], max(self.config["overlap_size"], int(self.config.get("overlap_size_boost", 30))))
        retry_temps = self.config.get("retry_temperatures", [self.config.get("temperature", 0.1), 0.2, 0.0, 0.3]) if self.supports_temperature else [None]
        max_workers = int(self.config.get("max_concurrency", 4))
        max_retries = int(self.config.get("max_retries", 10))
        print(f"🧵 Concurrency: {max_workers} workers")

        def worker(idx: int, start_line: int, end_line: int) -> Dict[str, Any]:
            chunk_lines = lines[start_line - 1:end_line]
            attempt = 0
            success = False
            records: List[Dict[str, Any]] = []
            temp_used = self.config.get("temperature", 0.1)
            last_error: str = ""
            out_file = run_dir / f"chunk_{start_line}-{end_line}.json"
            err_file = run_dir / f"chunk_{start_line}-{end_line}.error.txt"
            if out_file.exists() and bool(self.config.get("skip_existing", True)):
                try:
                    existing = json.loads(out_file.read_text(encoding='utf-8'))
                    existing_count = len(existing) if isinstance(existing, list) else 0
                except Exception:
                    existing_count = 0
                return {"index": idx, "start": start_line, "end": end_line, "attempts": 0, "temperature_used": None, "file": out_file.name, "status": "skipped", "record_count": existing_count}
            while not success and attempt < max_retries:
                temp_used = retry_temps[attempt % len(retry_temps)]
                attempt += 1
                temp_label = ("n/a" if (temp_used is None or not self.supports_temperature) else f"{temp_used}")
                print(f"   🔁 [chunk {idx:03d} {start_line}-{end_line}] Attempt {attempt} temp={temp_label}")
                try:
                    records = self.process_chunk(chunk_lines, start_line, end_line, temperature_override=(None if not self.supports_temperature else temp_used), fail_fast=False, doc_path=doc_path)
                    success = True
                except ValueError as e:
                    last_error = str(e)
                    print(f"      ↪️  Retry reason: {last_error}")
                    time.sleep(1)
                    continue
                except Exception as e:
                    err_text = f"{type(e).__name__}: {e}"
                    last_error = err_text
                    print(f"      ↪️  Retry reason: {last_error}")
                    if "model_not_found" in err_text or "does not exist" in err_text or "do not have access" in err_text:
                        break
                    time.sleep(1)
                    continue
            if success:
                out_file.write_text(json.dumps(records or [], ensure_ascii=False, indent=2), encoding='utf-8')
            else:
                err_file.write_text(f"Failed after {attempt} attempts. Last error: {last_error}\n", encoding='utf-8')
                print(f"   🚫 [chunk {idx:03d} {start_line}-{end_line}] Giving up after {attempt} attempts. Last error: {last_error}")
            return {"index": idx, "start": start_line, "end": end_line, "attempts": attempt, "temperature_used": temp_used, "file": out_file.name if success else None, "status": ("ok" if success else "failed"), "record_count": len(records or [])}

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_idx = {executor.submit(worker, idx, ch["start"], ch["end"]): idx for idx, ch in enumerate(chunks, start=1)}
            completed = 0
            total = len(chunks)
            failures = 0
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    meta = future.result()
                    manifest["chunks"].append(meta)
                    completed += 1
                    if meta.get("status") == "ok":
                        print(f"✅ Completed chunk {idx:03d} ({completed}/{total})")
                    elif meta.get("status") == "skipped":
                        print(f"⏭️  Skipped chunk {idx:03d} ({completed}/{total}) — already processed")
                    else:
                        failures += 1
                        print(f"❌ Failed chunk {idx:03d} after {meta.get('attempts')} attempts ({completed}/{total})")
                    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
                except Exception as e:
                    print(f"⚠️ Chunk {idx:03d} failed unexpectedly: {e}")
        print(f"\n🎉 All chunks processed. Output directory: {run_dir}")
        failed_chunks = [c for c in manifest.get("chunks", []) if c.get("status") == "failed"]
        if failed_chunks:
            print(f"⚠️ {len(failed_chunks)} chunks failed after {max_retries} retries. See .error.txt files in the run directory.")
        print("ℹ️ You can merge this run later to produce a consolidated file.")


