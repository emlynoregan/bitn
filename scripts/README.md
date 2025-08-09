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

3. **Run the processor (Pass 1 – per-chunk extraction):**
   ```powershell
python .\scripts\run_processor.py archive\markdown\<YOUR_SOURCE>.md
   ```
   - Generic for any source file; preflight model check and retries on JSON errors
   - Outputs chunk files to `processed/<slug>_pass_01/` (slug from filename, e.g. `1845_76_sa_register`)
   - Safe to rerun; existing chunk files are skipped when `skip_existing` is true

4. **Backfill header metadata (Pass 2):**
   ```powershell
python .\scripts\backfill_chunk_metadata.py processed\<slug>_pass_01 processed\<slug>_pass_02
   ```
   - Derives header anchors from chunk outputs and propagates `date`/`volume`/`issue_number`/`page`

5. **Merge and dedupe (Pass 3):**
   ```powershell
python .\scripts\merge_pass.py processed\<slug>_pass_02 processed\<slug>_pass_03\merged.json
   ```
   - Deduplicates by `(record_kind, source_line_start)` with a quality score heuristic

6. **Gap-fill and reprocess uncategorized (Pass 4):**
   ```powershell
python .\scripts\process_pass4.py processed\<slug>_pass_03\merged.json archive\markdown\<YOUR_SOURCE>.md processed\<slug>_pass_04
   ```
   - Fills gaps, reprocesses `uncategorized` mini-chunks, writes `processed/<slug>_pass_04/merged.json`
   - Backfill merged header metadata (and build `issue_reference`):
     ```powershell
python .\scripts\backfill_merged_metadata.py processed\<slug>_pass_04\merged.json processed\<slug>_pass_04\merged.backfilled.json
     ```
   - QA report (recommended):
     ```powershell
python .\scripts\qa_report.py processed\<slug>_pass_04\merged.backfilled.json archive\markdown\<YOUR_SOURCE>.md
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

## Outputs & Folders (per document)

- `processed/<slug>_pass_01/` — per-chunk extractions
- `processed/<slug>_pass_02/` — backfilled per-chunk outputs
- `processed/<slug>_pass_03/merged.json` — merged and deduped
- `processed/<slug>_pass_04/merged.json` — gap-filled + reprocessed
- `processed/<slug>_pass_04/merged.backfilled.json` — final backfilled output
- `processed/<slug>_pass_04/qa_report.*` — quality summary

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

After Pass 4, for each dataset you want included in the site/search:

```powershell
python .\scripts\generate_hugo_records.py processed\<slug>_pass_04\merged.backfilled.json
```

Notes:
- The generator merges into `site/static/js/search-data.json` (dedup by URL), so running it multiple times appends additional datasets.
- Front matter `date` is only set when ISO-formatted; non-ISO dates go to `date_display` and are shown in the UI.

Start Hugo locally:

```powershell
hugo serve -s site
```

Then open `/search`. Hard refresh (Ctrl+F5) if results look stale.