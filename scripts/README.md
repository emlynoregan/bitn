# Burra in the News – Data Processing and Site Generation

This folder contains the tooling to transform the original archive documents into granular “records” and to publish them into the Hugo site. The pipeline runs in four passes to guarantee completeness and good metadata.

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

3. **Run the processor (Pass 1–2):**
   ```powershell
python .\scripts\run_processor.py
   ```
   - Per-chunk mode with retries and concurrency
   - Outputs chunk files to `processed/chunks/`
   - You can rerun safely; existing chunk files are skipped

4. **Merge and dedupe (Pass 3):**
   ```powershell
python .\scripts\merge_pass.py
   ```
   - Reads `processed/northern_argus_pass_02/*` (or adjust) and writes 
     `processed/northern_argus_pass_03/merged.json` with deduplication by (kind,start) and quality preference

5. **Gap-fill and reprocess uncategorized (Pass 4):**
   ```powershell
python .\scripts\process_pass4.py
   ```
   - Loads Pass 3 merged, fills textual gaps as `uncategorized`, reprocesses them with focused LLM calls, fills any new gaps, and writes `processed/northern_argus_pass_04/merged.json`
   - Backfill missing header metadata from nearest header anchors:
     ```powershell
python .\scripts\backfill_merged_metadata.py
     ```
   - Normalize IDs to include kind: `northern_argus_<kind>_<start>`:
     ```powershell
python .\scripts\normalize_record_ids.py
     ```
   - QA report (optional but recommended):
     ```powershell
python .\scripts\qa_report.py
     ```
     Writes `qa_report.json` and `qa_report.txt` in Pass 4 folder

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

## Outputs & Folders

- `processed/chunks/` — per-chunk extractions (idempotent)
- `processed/northern_argus_pass_01/` — snapshot (optional)
- `processed/northern_argus_pass_02/` — snapshot (optional)
- `processed/northern_argus_pass_03/merged.json` — merged and deduped
- `processed/northern_argus_pass_04/merged.json` — gap-filled, reprocessed, backfilled; canonical for the site
- `processed/northern_argus_pass_04/qa_report.*` — quality summary

## Features

- **Deterministic record IDs**: `northern_argus_<kind>_<source_line_start>` (e.g., `northern_argus_content_891`)
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

## Populate the Hugo Site

After Pass 4, generate record pages and search index:

```powershell
python .\scripts\generate_hugo_records.py
```

This creates:
- `site/content/records/_index.md` and one page per content record
- `site/static/js/search-data.json` for Lunr search
- Copies archive `.md` files to `site/static/downloads/markdown/` so record pages can link source downloads

Start Hugo locally:

```powershell
hugo serve --config site/config.development.yaml --contentDir site/content --themesDir site/themes --staticDir site/static --baseURL http://localhost:1313/
```

Navigate to `/search` and try queries like “Redruth”; results link to `/records/<record_id>/` detail pages with download links and friendly dates.