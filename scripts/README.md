# Northern Argus Document Processor

This script automates the processing of the Northern Argus historical newspaper document using OpenAI's API.

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure API key:**
   Edit `config.json` and replace `"your-openai-api-key-here"` with your actual OpenAI API key.

3. **Run the processor:**
   ```bash
   python process_northern_argus.py
   ```

## Configuration

Edit `config.json` to adjust settings:

- `model`: OpenAI model to use (recommended: `gpt-4o-mini`)
- `chunk_size`: Lines per chunk (default: 250)
- `overlap_size`: Overlap between chunks (default: 50)
- `max_tokens`: Maximum response tokens (default: 4000)
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

The script creates several files in the `processed/` folder:

- `northern_argus_live_progress.json` - **LIVE MONITORING FILE** - Updated after every chunk with all records so far
- `northern_argus_chunk_XXX_YYYYMMDD_HHMMSS.json` - Individual chunk results (saved periodically)
- `northern_argus_progress_YYYYMMDD_HHMMSS.json` - Cumulative progress saves (saved periodically)
- `northern_argus_complete_YYYYMMDD_HHMMSS.json` - Final complete results

**💡 Tip**: Open `northern_argus_live_progress.json` in your editor to watch records being added in real-time!

## Features

- **Overlap handling**: Prevents missing records at chunk boundaries
- **Duplicate detection**: Uses previous records to avoid duplicates
- **Progress saving**: Saves every 5 chunks in case of interruption
- **Error handling**: Continues processing even if individual chunks fail
- **Statistics**: Provides summary of extracted records by type and date range
- **Rate limiting**: Built-in delays to respect API limits

## Monitoring

The script provides real-time progress updates:
- Current chunk being processed
- Number of records extracted per chunk
- Total records extracted so far
- Estimated completion time