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
   - Runs in per-chunk mode with retries (default and only mode)

## Configuration

Edit `config.json` to adjust settings (defaults shown):

- `model`: OpenAI model to use (e.g., `gpt5-mini`; override with `OPENAI_MODEL` env var)
- `chunk_size`: Lines per chunk (default: 80)
- `overlap_size`: Overlap between chunks (default: 20)
- `max_tokens`: Maximum response tokens (default: 16000)
- `temperature`: Creativity setting (default: 0.1 for consistency)
 - `retry_temperatures`: Optional list of temps to cycle on retry (default: `[temperature, 0.2, 0.0, 0.3]`)
 - `max_concurrency`: Number of chunks to process in parallel (default: 4)

## Model Recommendation

We recommend a small GPT-5 variant for higher accuracy and JSON reliability:

- `gpt5-mini` (default in config): Strong extraction quality at good cost
- `gpt5-nano`: Cheaper, lower latency; try if budget-sensitive

You can set `OPENAI_MODEL=gpt5-mini` or `OPENAI_MODEL=gpt5-nano` to override.

## Output

The script creates files in the `processed/` folder:

- `northern_argus_live_progress.json` — live cumulative results, updated after each chunk (includes timing and type counts)
- `northern_argus_records_00N.json` — incremental snapshots per run
- `northern_argus_records_final.json` — consolidated final output (recommended to export at completion)

**💡 Tip**: Open `northern_argus_live_progress.json` in your editor to watch records being added in real-time!

## Features

- **Deterministic record IDs**: `northern_argus_<source_line_start>`
- **Deduplication**: Newer records overwrite older duplicates
- **Gap filling**: Inserts `uncategorized` records for missed content
- **Focused reprocessing**: Re-runs each `uncategorized` block as a mini-chunk and replaces if extraction succeeds
- **Live monitoring**: Writes progress JSON with timing and article-type counts after every chunk
- **Fail-fast JSON handling**: Aborts on invalid JSON to prevent silent data loss
 - **Per-chunk retry mode**: Each top-level chunk is processed independently and saved to its own file; invalid JSON triggers retries varying temperature until success
 - **Concurrency**: Processes chunks in parallel (configurable via `max_concurrency`)

## Per-chunk Mode Details

- Splits the document into overlapping chunks upfront
- Processes each chunk independently; writes `processed/runs/run_<timestamp>/chunk_XXX_start-end.json`
- Retries on invalid JSON with temperatures cycling through `[config.temperature, 0.2, 0.0, 0.3]` (configurable via `retry_temperatures`)
- A `manifest.json` records chunk ranges, attempts, temperature used, and record counts
- You can later merge a run directory programmatically:

```python
from process_northern_argus import NorthernArgusProcessor
p = NorthernArgusProcessor()
p.merge_run_directory('processed/runs/run_YYYYMMDD_HHMMSS')
```

## Monitoring

The script provides real-time progress updates:
- Current chunk being processed
- Number of records extracted per chunk
- Total records extracted so far
- Estimated completion time