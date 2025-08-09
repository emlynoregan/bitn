#!/usr/bin/env python3
"""
Northern Argus Document Processor

Automatically processes the Northern Argus markdown document using OpenAI's API
to extract individual records according to the instructions in Northern Argus Instructions.md
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

class NorthernArgusProcessor:
    def __init__(self, config_path: str = "scripts/config.json"):
        self.config = self.load_config(config_path)
        self.client = OpenAI(api_key=self.config["openai_api_key"])
        self.instructions = self.load_instructions()
        self.all_records = []
        self.chunk_count = 0
        self.source_lines = []  # Store source lines for gap filling
        self.supports_temperature = True
        # Verify model availability up-front to avoid wasted retries
        self.verify_model_available()
    
    def create_chat_completion(self, messages: List[Dict[str, str]], temperature: float, max_tokens: int):
        """Create a chat completion with compatibility handling for models that require
        'max_completion_tokens' instead of 'max_tokens'."""
        try:
            kwargs = {
                "model": self.config["model"],
                "messages": messages,
            }
            # Only include temperature if supported and provided
            if self.supports_temperature and temperature is not None:
                kwargs["temperature"] = temperature
            # Prefer max_tokens; if not supported, we'll retry below
            kwargs["max_tokens"] = max_tokens
            return self.client.chat.completions.create(**kwargs)
        except Exception as e:
            err_text = str(e)
            if "max_tokens" in err_text and "not supported" in err_text:
                # Retry with max_completion_tokens for newer models
                kwargs = {
                    "model": self.config["model"],
                    "messages": messages,
                    "max_completion_tokens": max_tokens,
                }
                if self.supports_temperature and temperature is not None:
                    kwargs["temperature"] = temperature
                return self.client.chat.completions.create(**kwargs)
            if ("temperature" in err_text and ("unsupported" in err_text.lower() or "Only the default" in err_text)):
                # Temperature not supported or only default allowed. Disable temperature and retry once.
                self.supports_temperature = False
                kwargs = {
                    "model": self.config["model"],
                    "messages": messages,
                }
                # Use whichever token kw the model accepts
                token_key = "max_tokens"
                if "max_tokens" in err_text and "not supported" in err_text:
                    token_key = "max_completion_tokens"
                kwargs[token_key] = max_tokens
                return self.client.chat.completions.create(**kwargs)
            raise

    def verify_model_available(self) -> None:
        """Perform a tiny request to check that the configured model exists and is accessible.
        Exits the program with a clear message if the model is not available.
        """
        try:
            # Try with temperature first to probe support
            _ = self.create_chat_completion(
                messages=[
                    {"role": "system", "content": "Health check"},
                    {"role": "user", "content": "ping"}
                ],
                temperature=0.7,
                max_tokens=1,
            )
        except Exception as e:
            err_text = str(e)
            if ("model_not_found" in err_text) or ("does not exist" in err_text) or ("do not have access" in err_text):
                print(f"❌ The configured model '{self.config['model']}' is not available on this API key.")
                print("   Please update scripts/config.json to a supported model (e.g., 'gpt-4o-mini').")
                sys.exit(1)
            # If temperature is not supported, set flag and retry once without it
            if ("temperature" in err_text and ("unsupported" in err_text.lower() or "Only the default" in err_text)):
                self.supports_temperature = False
                try:
                    _ = self.create_chat_completion(
                        messages=[
                            {"role": "system", "content": "Health check"},
                            {"role": "user", "content": "ping"}
                        ],
                        temperature=None,
                        max_tokens=1,
                    )
                except Exception:
                    # Defer other errors to runtime handling
                    pass
            # Other errors should surface normally later; don't exit here
        
    def load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Allow environment overrides for key and model
            env_key = os.environ.get("OPENAI_API_KEY")
            if env_key:
                config["openai_api_key"] = env_key
            env_model = os.environ.get("OPENAI_MODEL")
            if env_model:
                config["model"] = env_model

            if config["openai_api_key"] == "your-openai-api-key-here":
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
        """Load processing instructions from markdown file"""
        instructions_path = "docs/Northern Argus Instructions.md"
        try:
            with open(instructions_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            print(f"ERROR: Instructions file not found at {instructions_path}")
            sys.exit(1)
    
    def load_document(self, doc_path: str) -> List[str]:
        """Load the Northern Argus document and return as list of lines"""
        try:
            with open(doc_path, 'r', encoding='utf-8') as f:
                return f.readlines()
        except FileNotFoundError:
            print(f"ERROR: Document not found at {doc_path}")
            sys.exit(1)
    
    def get_max_line_processed(self, records: List[Dict[str, Any]]) -> int:
        """Find the highest line number actually processed in the records"""
        max_line = 0
        for record in records:
            source_line_end = record.get("source_line_end", 0)
            if source_line_end > max_line:
                max_line = source_line_end
        return max_line
    
    def get_previous_records_summary(self) -> List[Dict[str, Any]]:
        """Get summary of previous records for duplicate checking - NO LONGER USED"""
        # This method is kept for backward compatibility but no longer used
        # LLM now processes chunks independently without previous record context
        return []
    
    def merge_records(self, new_records: List[Dict[str, Any]]) -> int:
        """Merge new records with existing ones, handling duplicates and maintaining order"""
        if not new_records:
            return 0
        
        # Create a map of existing records by ID for fast lookup
        existing_ids = {record.get("record_id"): i for i, record in enumerate(self.all_records)}
        
        added_count = 0
        updated_count = 0
        
        for new_record in new_records:
            record_id = new_record.get("record_id")
            if not record_id:
                print(f"⚠️  WARNING: Record missing record_id, skipping: {new_record.get('metadata', {}).get('headline', 'Unknown')}")
                continue
            
            if record_id in existing_ids:
                # Handle duplicate ID
                existing_index = existing_ids[record_id]
                existing_record = self.all_records[existing_index]
                
                # Always prefer the new record (later processing is generally better)
                print(f"🔄 Updating record {record_id} (using latest version)")
                self.all_records[existing_index] = new_record
                updated_count += 1
            else:
                # New record, add it
                self.all_records.append(new_record)
                existing_ids[record_id] = len(self.all_records) - 1
                added_count += 1
        
        # Sort records to maintain proper order (by source line, then by date)
        def sort_key(record):
            # Get source line for primary sorting (most reliable)
            source_line = record.get("source_line_start", 99999)
            
            # Get date for secondary sorting
            metadata = record.get("metadata", {})
            if metadata is None:
                metadata = {}
            date = metadata.get("date", "1900-01-01")
            
            # Handle empty or None dates
            if not date or date is None:
                date = "1900-01-01"
            
            # Extract line number from record_id as fallback (e.g., "northern_argus_477" -> 477)
            if source_line == 99999:
                try:
                    record_id = record.get("record_id", "")
                    parts = record_id.split("_")
                    if len(parts) >= 3 and parts[-1].isdigit():
                        source_line = int(parts[-1])
                except:
                    pass
            
            return (source_line, date)
        
        self.all_records.sort(key=sort_key)
        
        if updated_count > 0:
            print(f"📊 Merge summary: {added_count} new, {updated_count} updated records")
        
        return added_count
    
    def fill_gaps(self) -> int:
        """Find gaps between records and fill with uncategorized content if non-empty"""
        if len(self.all_records) < 2:
            return 0
            
        gap_records = []
        sorted_records = sorted(self.all_records, key=lambda r: r.get("source_line_start", 0))
        
        for i in range(len(sorted_records) - 1):
            current_end = sorted_records[i].get("source_line_end", 0)
            next_start = sorted_records[i + 1].get("source_line_start", 0)
            
            # Check if there's a gap (more than 1 line difference)
            if next_start > current_end + 1:
                gap_start = current_end + 1
                gap_end = next_start - 1
                
                # Extract lines in the gap (convert to 0-indexed for array access)
                gap_lines = []
                for line_num in range(gap_start, gap_end + 1):
                    if line_num <= len(self.source_lines):
                        gap_lines.append(self.source_lines[line_num - 1])  # Convert to 0-indexed
                
                # Check if gap contains non-whitespace content
                non_empty_content = any(line.strip() for line in gap_lines)
                
                if non_empty_content:
                    # Create uncategorized record for this gap
                    gap_text = "".join(gap_lines).strip()
                    gap_record = {
                        "record_id": f"northern_argus_{gap_start}",
                        "source_document": "1985-87_Northern__Argus.md",
                        "source_line_start": gap_start,
                        "source_line_end": gap_end,
                        "original_text": gap_text,
                        "metadata": {
                            "publication": "Northern Argus",
                            "article_type": "uncategorized",
                            "headline": f"Gap content (lines {gap_start}-{gap_end})",
                            "note": "Content found between processed records - may need manual review"
                        }
                    }
                    gap_records.append(gap_record)
        
        # Add gap records to main collection
        if gap_records:
            self.all_records.extend(gap_records)
            # Re-sort to maintain order
            self.all_records.sort(key=lambda r: r.get("source_line_start", 0))
            
        return len(gap_records)
    
    def reprocess_uncategorized_records(self) -> int:
        """Try to reprocess uncategorized records with focused LLM attention"""
        if not self.all_records:
            return 0
            
        uncategorized_records = [r for r in self.all_records if r.get("metadata", {}).get("article_type") == "uncategorized"]
        
        if not uncategorized_records:
            return 0
            
        print(f"🔄 Attempting to reprocess {len(uncategorized_records)} uncategorized records...")
        
        reprocessed_count = 0
        records_to_remove = []
        records_to_add = []
        
        for uncat_record in uncategorized_records:
            record_id = uncat_record.get("record_id")
            start_line = uncat_record.get("source_line_start")
            end_line = uncat_record.get("source_line_end")
            
            if not start_line or not end_line:
                continue
                
            # Extract the specific lines for this uncategorized record
            chunk_lines = []
            for line_num in range(start_line, end_line + 1):
                if line_num <= len(self.source_lines):
                    chunk_lines.append(self.source_lines[line_num - 1])  # Convert to 0-indexed
            
            if not chunk_lines:
                continue
                
            print(f"  🎯 Reprocessing lines {start_line}-{end_line} (record {record_id})")
            
            try:
                # Process this small focused chunk
                new_records = self.process_chunk(chunk_lines, start_line, end_line)
                
                if new_records:
                    print(f"    ✅ Successfully extracted {len(new_records)} records from uncategorized content")
                    records_to_remove.append(uncat_record)
                    records_to_add.extend(new_records)
                    reprocessed_count += 1
                else:
                    print(f"    ⏭️  No records extracted - keeping as uncategorized")
                    
            except Exception as e:
                print(f"    ⚠️  Error reprocessing: {e} - keeping as uncategorized")
                continue
        
        # Remove uncategorized records that were successfully reprocessed
        for record_to_remove in records_to_remove:
            if record_to_remove in self.all_records:
                self.all_records.remove(record_to_remove)
        
        # Add new records (they'll go through normal merge process)
        if records_to_add:
            self.merge_records(records_to_add)
        
        return reprocessed_count
    
    def process_chunk(
        self,
        chunk_lines: List[str],
        start_line: int,
        end_line: int,
        temperature_override: float = None,
        fail_fast: bool = True,
    ) -> List[Dict[str, Any]]:
        """Process a single chunk using OpenAI API.
        
        Parameters:
            chunk_lines: The raw lines of the chunk
            start_line, end_line: 1-indexed inclusive bounds in the source document
            temperature_override: Optional temperature to use for this call
            fail_fast: If True, exit on JSON errors; if False, raise to allow retries
        """
        # Add explicit line numbers to help LLM understand positioning
        numbered_lines = []
        for i, line in enumerate(chunk_lines):
            line_num = start_line + i
            # Format line numbers right-aligned to 6 characters (matches our citation format)
            numbered_lines.append(f"{line_num:6d}→{line}")
        
        chunk_text = ''.join(numbered_lines)
        
        # Create the prompt
        system_prompt = f"""You are processing the Northern Argus historical newspaper document according to these instructions:

{self.instructions}

IMPORTANT: You must return ONLY a valid JSON array of records. No other text, explanations, or markdown formatting."""

        user_prompt = f"""Current chunk (lines {start_line}-{end_line}):

IMPORTANT: Each line is prefixed with its actual line number in the format "LINE_NUMBER→CONTENT".
Use these line numbers for accurate source_line_start and source_line_end values.

{chunk_text}

Process this chunk according to the instructions and return a JSON array of records for all content you find."""

        try:
            response = self.create_chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=self.config["max_tokens"],
                temperature=(self.config["temperature"] if temperature_override is None else temperature_override)
            )
            
            content = response.choices[0].message.content.strip()
            
            # Try to parse JSON
            try:
                records = json.loads(content)
                if not isinstance(records, list):
                    print(f"WARNING: Chunk {self.chunk_count + 1} returned non-list: {type(records)}")
                    return []
                
                # Add record_kind default and record_id
                for record in records:
                    if not record.get("record_kind"):
                        record["record_kind"] = "content"
                    source_line_start = record.get("source_line_start")
                    if source_line_start:
                        record["record_id"] = f"northern_argus_{source_line_start}"
                    else:
                        print(f"WARNING: Record missing source_line_start: {record}")
                
                return records
            except json.JSONDecodeError as e:
                # Detailed diagnostics
                print(f"❌ JSON error in chunk {self.chunk_count + 1} ({start_line}-{end_line}): {e}")
                print(f"Response length: {len(content)} chars | Max tokens: {self.config['max_tokens']}")
                print(f"Content start: {content[:100]}... | end: ...{content[-100:]}")
                if fail_fast:
                    # Preserve previous fail-fast behavior
                    sys.exit(1)
                # Allow caller to retry with explicit reason
                raise ValueError(f"INVALID_JSON_RESPONSE: {e}")
                
        except Exception as e:
            if fail_fast:
                print(f"❌ FATAL: Unexpected error processing chunk {self.chunk_count + 1}: {e}")
                print("🛑 Terminating to prevent data loss.")
                sys.exit(1)
            raise

    def split_into_chunks(self, total_lines: int, chunk_size: int, overlap_size: int) -> List[Dict[str, int]]:
        """Pre-split the document into top-level chunks with overlap.
        Returns a list of dicts with start_line and end_line (1-indexed, inclusive)."""
        chunks = []
        start = 1
        while start <= total_lines:
            end = min(start + chunk_size - 1, total_lines)
            chunks.append({"start": start, "end": end})
            # Next start accounts for overlap
            start = end - overlap_size + 1
            if start <= chunks[-1]["start"]:
                start = chunks[-1]["start"] + 1
        return chunks

    def process_document_per_chunk(self, doc_path: str, output_root: str = None):
        """Process each top-level chunk independently with retries, writing one file per chunk.
        Retries vary temperature until valid JSON is returned.
        Uses a single persistent output directory so processing can be stopped/restarted safely.
        """
        print(f"🚀 Per-chunk processing with {self.config['model']}")
        print(f"📁 Document: {doc_path}")
        print(f"🔧 Chunk size: {self.config['chunk_size']} | Overlap: {self.config['overlap_size']}")

        lines = self.load_document(doc_path)
        self.source_lines = lines
        total_lines = len(lines)

        # Prepare persistent output directory
        output_dir = self.config.get("output_directory", "processed/chunks")
        run_dir = Path(output_root) if output_root else Path(output_dir)
        run_dir.mkdir(parents=True, exist_ok=True)

        # Manifest to track attempts and status (persisted)
        manifest_path = run_dir / "manifest.json"
        manifest = {"document": doc_path, "total_lines": total_lines, "chunks": []}
        if manifest_path.exists():
            try:
                with open(manifest_path, "r", encoding="utf-8") as mf:
                    prev = json.load(mf)
                    if isinstance(prev, dict):
                        manifest.update({k: v for k, v in prev.items() if k != "chunks"})
                        if isinstance(prev.get("chunks"), list):
                            manifest["chunks"] = prev["chunks"]
            except Exception:
                pass

        # Increase overlap as configured for header capture
        chunks = self.split_into_chunks(total_lines, self.config["chunk_size"], max(self.config["overlap_size"], int(self.config.get("overlap_size_boost", 30))))
        # Determine retry temperatures. If the model does not support temperature, disable it entirely
        if self.supports_temperature:
            retry_temps = self.config.get("retry_temperatures", [self.config.get("temperature", 0.1), 0.2, 0.0, 0.3])
        else:
            retry_temps = [None]
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
            # Stable filenames based on line range
            out_file = run_dir / f"chunk_{start_line}-{end_line}.json"
            err_file = run_dir / f"chunk_{start_line}-{end_line}.error.txt"

            # Skip if already processed (output exists)
            if out_file.exists() and bool(self.config.get("skip_existing", True)):
                try:
                    with open(out_file, "r", encoding="utf-8") as f:
                        existing = json.load(f)
                        existing_count = len(existing) if isinstance(existing, list) else 0
                except Exception:
                    existing_count = 0
                return {
                    "index": idx,
                    "start": start_line,
                    "end": end_line,
                    "attempts": 0,
                    "temperature_used": None,
                    "file": out_file.name,
                    "status": "skipped",
                    "record_count": existing_count,
                }
            while not success and attempt < max_retries:
                temp_used = retry_temps[attempt % len(retry_temps)]
                attempt += 1
                temp_label = ("n/a" if (temp_used is None or not self.supports_temperature) else f"{temp_used}")
                print(f"   🔁 [chunk {idx:03d} {start_line}-{end_line}] Attempt {attempt} temp={temp_label}")
                try:
                    records = self.process_chunk(
                        chunk_lines,
                        start_line,
                        end_line,
                        temperature_override=(None if not self.supports_temperature else temp_used),
                        fail_fast=False,
                    )
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
                    # Stop retrying immediately if model is unavailable
                    if "model_not_found" in err_text or "does not exist" in err_text or "do not have access" in err_text:
                        break
                    time.sleep(1)
                    continue

            # Write per-chunk file
            if success:
                with open(out_file, "w", encoding="utf-8") as f:
                    json.dump(records or [], f, indent=2, ensure_ascii=False)
            else:
                # Record failure marker file for inspection
                with open(err_file, "w", encoding="utf-8") as ef:
                    ef.write(f"Failed after {attempt} attempts. Last error: {last_error}\n")
                print(f"   🚫 [chunk {idx:03d} {start_line}-{end_line}] Giving up after {attempt} attempts. Last error: {last_error}")

            return {
                "index": idx,
                "start": start_line,
                "end": end_line,
                "attempts": attempt,
                "temperature_used": temp_used,
                "file": out_file.name if success else None,
                "status": "ok" if success else "failed",
                "record_count": len(records or []),
            }

        # Dispatch all chunks concurrently
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_idx = {
                executor.submit(worker, idx, ch["start"], ch["end"]): idx
                for idx, ch in enumerate(chunks, start=1)
            }

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
                    # Save manifest incrementally from main thread
                    with open(manifest_path, "w", encoding="utf-8") as mf:
                        json.dump(manifest, mf, indent=2, ensure_ascii=False)
                except Exception as e:
                    print(f"⚠️ Chunk {idx:03d} failed unexpectedly: {e}")

        print(f"\n🎉 All chunks processed. Output directory: {run_dir}")
        # Summary of failures
        failed_chunks = [c for c in manifest.get("chunks", []) if c.get("status") == "failed"]
        if failed_chunks:
            print(f"⚠️ {len(failed_chunks)} chunks failed after {max_retries} retries. See .error.txt files in the run directory.")
        print("ℹ️ You can merge this run later to produce a consolidated file.")

    def merge_run_directory(self, run_dir: str, output_file: str = None):
        """Merge all per-chunk files from a run directory using normal dedup/order logic."""
        run_path = Path(run_dir)
        if not run_path.exists():
            print(f"❌ Run directory not found: {run_dir}")
            sys.exit(1)

        # Reset current records
        self.all_records = []

        chunk_files = sorted(run_path.glob("chunk_*.json"))
        for cf in chunk_files:
            try:
                with open(cf, "r", encoding="utf-8") as f:
                    recs = json.load(f)
                    if isinstance(recs, list) and recs:
                        self.merge_records(recs)
            except Exception as e:
                print(f"⚠️ Skipping {cf.name}: {e}")

        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = run_path / f"merged_{timestamp}.json"
        else:
            output_file = Path(output_file)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(self.all_records, f, indent=2, ensure_ascii=False)

        print(f"✅ Merged {len(chunk_files)} chunks → {output_file}")
    
    def save_intermediate_progress(self):
        """Save current progress to a live monitoring file"""
        # Overwrite the same file so user can monitor progress
        progress_file = "processed/northern_argus_live_progress.json"
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump(self.all_records, f, indent=2, ensure_ascii=False)
    
    def save_progress(self, records: List[Dict[str, Any]], chunk_num: int):
        """Save current progress to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save individual chunk
        chunk_file = f"processed/northern_argus_chunk_{chunk_num:03d}_{timestamp}.json"
        with open(chunk_file, 'w', encoding='utf-8') as f:
            json.dump(records, f, indent=2, ensure_ascii=False)
        
        # Save cumulative progress
        progress_file = f"processed/northern_argus_progress_{timestamp}.json"
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump(self.all_records, f, indent=2, ensure_ascii=False)
    
    def process_document(self, doc_path: str):
        """Process the entire Northern Argus document"""
        print(f"🚀 Starting Northern Argus processing with {self.config['model']}")
        print(f"📁 Document: {doc_path}")
        print(f"🔧 Chunk size: {self.config['chunk_size']} lines")
        print(f"🔄 Overlap: {self.config['overlap_size']} lines")
        print(f"👀 Live progress: processed/northern_argus_live_progress.json")
        
        # Load document
        lines = self.load_document(doc_path)
        self.source_lines = lines  # Store for gap filling
        print(f"📄 Loaded {len(lines)} lines")
        
        # Ensure output directory exists
        os.makedirs("processed", exist_ok=True)
        
        # Dynamic chunking - process adaptively based on what LLM actually handles
        start_time = time.time()
        chunk_count = 0
        current_line = 0  # 0-indexed for line array access
        chunk_size = self.config["chunk_size"]
        overlap_size = self.config["overlap_size"]
        
        while current_line < len(lines):
            # Calculate this chunk's range
            end_line = min(current_line + chunk_size, len(lines))
            chunk_lines = lines[current_line:end_line]
            
            # Convert to 1-indexed line numbers for display and processing
            start_line_num = current_line + 1
            end_line_num = end_line
            
            chunk_count += 1
            chunk_start_time = time.time()
            self.chunk_count = chunk_count - 1  # 0-indexed for compatibility
            
            print(f"\n⚙️  Processing chunk {chunk_count} (lines {start_line_num}-{end_line_num})")
            
            records = self.process_chunk(chunk_lines, start_line_num, end_line_num)
            
            # Calculate timing information
            chunk_elapsed = time.time() - chunk_start_time
            total_elapsed = time.time() - start_time
            
            if records:
                added_count = self.merge_records(records)
                print(f"✅ Extracted {len(records)} records, added {added_count} new")
                
                # Fill any gaps in coverage
                gap_count = self.fill_gaps()
                if gap_count > 0:
                    print(f"🔍 Filled {gap_count} content gaps with uncategorized records")
                
                # Try to reprocess uncategorized records with focused LLM attention
                reprocessed_count = self.reprocess_uncategorized_records()
                if reprocessed_count > 0:
                    print(f"🎯 Reprocessed {reprocessed_count} uncategorized records into proper categories")
                    
                    # Fill any new gaps that might have appeared after reprocessing
                    additional_gaps = self.fill_gaps()
                    if additional_gaps > 0:
                        print(f"🔍 Filled {additional_gaps} additional gaps after reprocessing")
                
                # Find the actual last line processed by the LLM
                max_line_processed = self.get_max_line_processed(records)
                print(f"📍 LLM processed up to line {max_line_processed} (requested up to {end_line_num})")
                
                # Calculate next chunk start with overlap, but ensure we always move forward
                next_start_line = max_line_processed - overlap_size + 1
                
                # Ensure we don't go backwards - next chunk must start after current chunk started
                if next_start_line <= start_line_num:
                    print("⚠️  Calculated next start would go backwards - advancing by minimum amount")
                    next_start_line = start_line_num + 1
                
                current_line = next_start_line - 1  # Convert back to 0-indexed
                
                print(f"🔄 Next chunk will start at line {next_start_line}")
                    
            else:
                # This should rarely happen now since JSON errors terminate immediately
                print("⚠️  No records extracted from this chunk (empty chunk or no content)")
                # Advance to avoid infinite loop
                current_line = current_line + chunk_size
            
            # Calculate progress estimates based on actual position
            # Use the max line we've actually processed, not the current chunk position
            if self.all_records:
                actual_lines_processed = self.get_max_line_processed(self.all_records)
            else:
                actual_lines_processed = current_line + 1
            
            progress_percent = (actual_lines_processed / len(lines)) * 100
            
            # Estimate time based on lines per second
            if actual_lines_processed > 0:
                lines_per_second = actual_lines_processed / total_elapsed
                lines_remaining = len(lines) - actual_lines_processed
                estimated_remaining_time = lines_remaining / lines_per_second if lines_per_second > 0 else 0
                estimated_total_time = total_elapsed + estimated_remaining_time
            else:
                estimated_remaining_time = 0
                estimated_total_time = total_elapsed
            
            # Format time strings
            def format_time(seconds):
                if seconds < 60:
                    return f"{seconds:.0f}s"
                elif seconds < 3600:
                    return f"{seconds/60:.1f}m"
                else:
                    return f"{seconds/3600:.1f}h"
            
            # Save progress after every chunk for monitoring
            self.save_intermediate_progress()
            
            # Display comprehensive progress information
            print(f"💾 Progress saved ({len(self.all_records)} total records so far)")
            print(f"📊 Progress: {progress_percent:.1f}% (line {actual_lines_processed}/{len(lines)})")
            print(f"⏱️  Elapsed: {format_time(total_elapsed)} | Chunk: {format_time(chunk_elapsed)}")
            print(f"🔮 ETA: {format_time(estimated_remaining_time)} | Total Est: {format_time(estimated_total_time)}")
            
            # Show distinct article types found so far with counts
            if self.all_records:
                type_counts = {}
                for record in self.all_records:
                    article_type = record.get("metadata", {}).get("article_type", "unknown")
                    type_counts[article_type] = type_counts.get(article_type, 0) + 1
                
                # Format counts nicely
                type_list = []
                for article_type in sorted(type_counts.keys()):
                    count = type_counts[article_type]
                    if article_type == "uncategorized":
                        type_list.append(f"{article_type}({count})")
                    else:
                        type_list.append(f"{article_type}({count})" if count > 1 else article_type)
                
                print(f"📝 Article types found: {', '.join(type_list)}")
            
            # Brief pause to avoid rate limiting
            time.sleep(1)
        
        # Final save
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        final_file = f"processed/northern_argus_complete_{timestamp}.json"
        
        with open(final_file, 'w', encoding='utf-8') as f:
            json.dump(self.all_records, f, indent=2, ensure_ascii=False)
        
        # Summary
        elapsed = time.time() - start_time
        print(f"\n🎉 Processing complete!")
        print(f"📊 Total records extracted: {len(self.all_records)}")
        print(f"⏱️  Total time: {elapsed:.1f} seconds")
        print(f"💾 Final output: {final_file}")
        
        # Generate summary statistics
        self.print_summary()
    
    def print_summary(self):
        """Print summary statistics about extracted records"""
        if not self.all_records:
            return
            
        # Count by article type
        type_counts = {}
        date_range = {"earliest": None, "latest": None}
        
        for record in self.all_records:
            article_type = record.get("metadata", {}).get("article_type", "unknown")
            type_counts[article_type] = type_counts.get(article_type, 0) + 1
            
            date_str = record.get("metadata", {}).get("date")
            if date_str:
                if not date_range["earliest"] or date_str < date_range["earliest"]:
                    date_range["earliest"] = date_str
                if not date_range["latest"] or date_str > date_range["latest"]:
                    date_range["latest"] = date_str
        
        print(f"\n📈 SUMMARY STATISTICS")
        print(f"📅 Date range: {date_range['earliest']} to {date_range['latest']}")
        print(f"📋 Records by type:")
        for article_type, count in sorted(type_counts.items()):
            print(f"   {article_type}: {count}")

def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        doc_path = sys.argv[1]
    else:
        doc_path = "archive/markdown/1985-87_Northern__Argus.md"
    
    processor = NorthernArgusProcessor()
    processor.process_document(doc_path)

if __name__ == "__main__":
    main()