# Northern Argus Document Processor

This script automates the processing of the Northern Argus historical newspaper document using OpenAI's API.

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure API key:**
   - Copy the example config and edit it locally (note: `config.json` is gitignored):
     ```bash
     cp scripts/config.example.json scripts/config.json
     ```
   - Open `scripts/config.json` and set `openai_api_key`.
   - Optional: You can also provide the key via environment variable (e.g., `OPENAI_API_KEY`) if your environment supports it.

3. **Run the processor:**
   ```bash
   python run_processor.py
   ```

## Configuration

Edit `config.json` to adjust settings (defaults shown):

- `model`: OpenAI model to use (recommended: `gpt-4o-mini`)
- `chunk_size`: Lines per chunk (default: 80)
- `overlap_size`: Overlap between chunks (default: 20)
- `max_tokens`: Maximum response tokens (default: 16000)
- `temperature`: Creativity setting (default: 0.1 for consistency)

## Model Recommendation: GPT-4o-mini

**Why GPT-4o-mini is perfect for this task:**

✅ **Cost-effective**: ~10x cheaper than GPT-4o for large processing jobs  
✅ **Excellent instruction following**: Handles complex structured output requirements  
✅ **JSON reliability**: Very good at producing valid JSON responses  
✅ **Sufficient context**: Can handle our chunk sizes (250 lines + instructions)  
✅ **Fast processing**: Good throughput for batch processing  

**Estimated cost for full Northern Argus document (~3,331 lines):**
- ~15-20 chunks with our settings
- ~$2-5 total cost (vs $20-50 with GPT-4o)

## Output

The script creates files in the `processed/` folder:

- `northern_argus_live_progress.json` — live cumulative results, updated after each chunk (includes timing and type counts)
- `northern_argus_records_00N.json` — incremental snapshots per run
- `northern_argus_records_final.json` — consolidated final output (recommended to export at completion)

**💡 Tip**: Open `northern_argus_live_progress.json` in your editor to watch records being added in real-time!

## Features

- **Dynamic chunking (forward-only)**: Advances based on last processed source line
- **Deterministic record IDs**: `northern_argus_<source_line_start>`
- **Deduplication**: Newer records overwrite older duplicates
- **Gap filling**: Inserts `uncategorized` records for missed content
- **Focused reprocessing**: Re-runs each `uncategorized` block as a mini-chunk and replaces if extraction succeeds
- **Live monitoring**: Writes progress JSON with timing and article-type counts after every chunk
- **Fail-fast JSON handling**: Aborts on invalid JSON to prevent silent data loss

## Monitoring

The script provides real-time progress updates:
- Current chunk being processed
- Number of records extracted per chunk
- Total records extracted so far
- Estimated completion time