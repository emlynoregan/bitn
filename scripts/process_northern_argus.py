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
        
    def load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            
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
    
    def create_chunks(self, lines: List[str]) -> List[tuple]:
        """Create overlapping chunks from the document lines"""
        chunks = []
        chunk_size = self.config["chunk_size"]
        overlap_size = self.config["overlap_size"]
        
        start = 0
        while start < len(lines):
            end = min(start + chunk_size, len(lines))
            chunk_lines = lines[start:end]
            
            # Calculate actual line numbers (1-indexed)
            start_line_num = start + 1
            end_line_num = end
            
            chunks.append((chunk_lines, start_line_num, end_line_num))
            
            # Move start position for next chunk (with overlap)
            if end >= len(lines):
                break
            start = end - overlap_size
            
        return chunks
    
    def get_previous_records_summary(self) -> List[Dict[str, Any]]:
        """Get summary of previous records for duplicate checking"""
        # Return last 20 records for context (to avoid token limits)
        return self.all_records[-20:] if len(self.all_records) > 20 else self.all_records
    
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
                
                # Check if new record is more complete (more content or metadata)
                existing_text_len = len(existing_record.get("original_text", ""))
                new_text_len = len(new_record.get("original_text", ""))
                existing_metadata_count = len(str(existing_record.get("metadata", {})))
                new_metadata_count = len(str(new_record.get("metadata", {})))
                
                if new_text_len > existing_text_len or new_metadata_count > existing_metadata_count:
                    print(f"🔄 Updating record {record_id} (new version more complete)")
                    self.all_records[existing_index] = new_record
                    updated_count += 1
                else:
                    print(f"⏭️  Skipping duplicate record {record_id} (existing version is complete)")
            else:
                # New record, add it
                self.all_records.append(new_record)
                existing_ids[record_id] = len(self.all_records) - 1
                added_count += 1
        
        # Sort records to maintain proper order (by date, then by sequence number in ID)
        def sort_key(record):
            record_id = record.get("record_id", "")
            date = record.get("metadata", {}).get("date", "1900-01-01")
            
            # Extract sequence number from record_id (e.g., "northern_argus_1985_08_21_003" -> 3)
            try:
                parts = record_id.split("_")
                if len(parts) >= 6 and parts[-1].isdigit():
                    sequence = int(parts[-1])
                elif len(parts) >= 5 and parts[-1] == "missing":
                    sequence = 0  # Missing issues come first
                else:
                    sequence = 999  # Unknown format, put at end
            except:
                sequence = 999
            
            return (date, sequence)
        
        self.all_records.sort(key=sort_key)
        
        if updated_count > 0:
            print(f"📊 Merge summary: {added_count} new, {updated_count} updated records")
        
        return added_count
    
    def process_chunk(self, chunk_lines: List[str], start_line: int, end_line: int) -> List[Dict[str, Any]]:
        """Process a single chunk using OpenAI API"""
        # Add explicit line numbers to help LLM understand positioning
        numbered_lines = []
        for i, line in enumerate(chunk_lines):
            line_num = start_line + i
            # Format line numbers right-aligned to 6 characters (matches our citation format)
            numbered_lines.append(f"{line_num:6d}→{line}")
        
        chunk_text = ''.join(numbered_lines)
        previous_records = self.get_previous_records_summary()
        
        # Create the prompt
        system_prompt = f"""You are processing the Northern Argus historical newspaper document according to these instructions:

{self.instructions}

IMPORTANT: You must return ONLY a valid JSON array of records. No other text, explanations, or markdown formatting."""

        user_prompt = f"""Current chunk (lines {start_line}-{end_line}):

IMPORTANT: Each line is prefixed with its actual line number in the format "LINE_NUMBER→CONTENT".
Use these line numbers for accurate source_line_start and source_line_end values.

{chunk_text}

Previous records for duplicate checking:
{json.dumps(previous_records, indent=2) if previous_records else "[]"}

Process this chunk according to the instructions and return a JSON array of new records."""

        try:
            response = self.client.chat.completions.create(
                model=self.config["model"],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=self.config["max_tokens"],
                temperature=self.config["temperature"]
            )
            
            content = response.choices[0].message.content.strip()
            
            # Try to parse JSON
            try:
                records = json.loads(content)
                if not isinstance(records, list):
                    print(f"WARNING: Chunk {self.chunk_count + 1} returned non-list: {type(records)}")
                    return []
                return records
            except json.JSONDecodeError as e:
                print(f"❌ FATAL: Chunk {self.chunk_count + 1} returned invalid JSON: {e}")
                print(f"Response length: {len(content)} characters")
                print(f"Max tokens configured: {self.config['max_tokens']}")
                print(f"Chunk size: {self.config['chunk_size']} lines")
                print(f"Content start: {content[:100]}...")
                print(f"Content end: ...{content[-100:]}")
                
                # Check if this looks like truncation
                if "Unterminated string" in str(e) or (content.strip().startswith('[') and not content.strip().endswith(']')):
                    print("\n🔥 CRITICAL ERROR: Response truncated due to token limit!")
                    print("📋 This means DATA LOSS - some records will be missing from the final output.")
                    print("🛑 Terminating immediately to prevent incomplete extraction.")
                    print("\n💡 REQUIRED FIXES:")
                    print("   1. Increase max_tokens in config.json (try 20000+)")
                    print("   2. Decrease chunk_size in config.json (try 50-60)")
                    print("   3. Or upgrade to gpt-4o (larger context window)")
                    print("\nNo data recovery attempted - fix config and restart.")
                    sys.exit(1)
                
                # For other JSON errors, also fail fast 
                print("\n🔥 CRITICAL ERROR: Invalid JSON response format!")
                print("This indicates a prompt or model issue.")
                print("🛑 Terminating to avoid data loss.")
                sys.exit(1)
                
        except Exception as e:
            print(f"❌ FATAL: Unexpected error processing chunk {self.chunk_count + 1}: {e}")
            print("🛑 Terminating to prevent data loss.")
            sys.exit(1)
    
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
        print(f"📄 Loaded {len(lines)} lines")
        
        # Create chunks
        chunks = self.create_chunks(lines)
        print(f"📦 Created {len(chunks)} chunks")
        
        # Ensure output directory exists
        os.makedirs("processed", exist_ok=True)
        
        # Process each chunk
        start_time = time.time()
        
        for i, (chunk_lines, start_line, end_line) in enumerate(chunks):
            self.chunk_count = i
            print(f"\n⚙️  Processing chunk {i + 1}/{len(chunks)} (lines {start_line}-{end_line})")
            
            records = self.process_chunk(chunk_lines, start_line, end_line)
            
            if records:
                added_count = self.merge_records(records)
                print(f"✅ Extracted {len(records)} records, added {added_count} new")
            else:
                # This should rarely happen now since JSON errors terminate immediately
                print("⚠️  No records extracted from this chunk (empty chunk or no content)")
            
            # Save progress after every chunk for monitoring
            self.save_intermediate_progress()
            print(f"💾 Progress saved ({len(self.all_records)} total records so far)")
            
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