# Burra in the News (BITN) - Digital Archive Project

> **170 years of South Australian community history, digitally preserved and searchable**

Find the site here: [https://emlynoregan.com/bitn](https://emlynoregan.com/bitn)

[![Archive Status](https://img.shields.io/badge/Archive-Complete-green)](#archive-status)
[![Content](https://img.shields.io/badge/Content-250K%2B%20paragraphs-blue)](#content-overview)
[![Time Span](https://img.shields.io/badge/Years-1845--2016-orange)](#time-coverage)
[![Formats](https://img.shields.io/badge/Formats-DOC%2FDOCX%2FMD%2FJSON-purple)](#available-formats)

## 📖 About This Archive

This repository contains the complete digitization of **Eric Fuss's "Burra in the News"** archive - a meticulously compiled collection documenting every mention of Burra, South Australia in newspapers spanning **over 170 years (1845-2016)**. 

This isn't just a newspaper collection - it's a **scholarly treasure trove** with genealogical research, fact-checking annotations, and cross-references that transform scattered primary sources into an integrated community biography.

### 🏆 What Makes This Special

- **📚 Complete Coverage**: 9,168+ historical items across 14 publications
- **🔬 Scholarly Enhanced**: Eric Fuss's annotations with verified genealogical data
- **🔍 Fully Searchable**: Every paragraph indexed and searchable
- **👨‍👩‍👧‍👦 Genealogical Gold**: Birth/death dates verified against SA registrations
- **🏛️ Historical Continuity**: Seamless coverage despite newspaper transitions
- **🎯 Research Ready**: Multiple formats for different use cases

## ✅ Current Project Status

- **Archive**: All 14 original `.doc` files present with corresponding `.docx` and `.md` in `archive/`.
- **Static site**: Hugo site configured and buildable locally; GitHub Pages deployment workflow present.
- **Search**: Lunr.js client-side search enabled; assets use absolute URLs for HTTPS on Pages.
- **LLM processing status**:
  - Northern Argus: Pass 1–4 complete (merged + backfilled + QA); integrated into site
  - SA Register (1845–76): Pass 1–4 complete; integrated into site
  - Record (1876–79): Pass 1–4 complete; integrated into site
  - Record (1880–99): Pass 1–4 complete; integrated into site
  - Record (1900–1919): Pass 1 complete; Pass 2–4 pending; not yet integrated
  - Record (1920–39): Pass 1 complete; Pass 2–4 pending; not yet integrated
  - Record (1940–59): Pass 1 complete; Pass 2–4 pending; not yet integrated
  - Record (1960 – Part 77): Pass 1 complete; Pass 2–4 pending; not yet integrated
  - Review Times Record, BCS & CN, Burra Broadcaster, Mid North Broadcaster: Pass 1–4 pending; not yet integrated
- **Outputs**: Incremental and final JSONs under `processed/`; site content under `site/content/records/`; downloads under `site/static/downloads/markdown/`.
- **Next actions**:
  - Rotate any committed API key (see Security)
  - Option A (recommended): clean-regenerate site content and search from the four completed Pass 4 datasets for a consistent state
  - Option B: leave existing pages in place and append additional datasets via the generator
  - Add a downloads page linking ZIPs for `archive/originals` and `archive/markdown`

## 📊 Content Overview

| Publication Series | Years | Items | Description |
|-------------------|-------|-------|-------------|
| SA Register | 1845-1876 | 613 | Pre-local newspaper Adelaide coverage |
| The Record Series | 1876-1977 | 6,862 | Core local newspaper (multiple name changes) |
| Review Times Record | 1977-1987 | 87 | Transition period coverage |
| Northern Argus | 1985-1987 | 73 | Regional newspaper coverage |
| School & Community News | 1978-1993 | 407 | Community newsletter era |
| Burra Broadcaster | 1991-2016 | 762 | Modern community newspaper |
| Mid North Broadcaster | 2006-2013 | 371 | Regional modern coverage |

**Total**: **9,175+ pages** • **250,000+ paragraphs** • **30+ million characters**

## 📂 Repository Structure

```
bitn/
├── README.md                           # This file
├── LICENSE
├── .github/
│   └── workflows/
│       └── hugo.yml                    # GitHub Pages deployment workflow
├── docs/                               # Project documentation
│   ├── Burra In The News - Analysis.md
│   ├── Static Site Design Plan.md
│   ├── Data Design Document.md
│   └── Technical Architecture Explanation.md
├── scripts/                            # Processing and utility scripts
│   ├── process_northern_argus.py       # LLM orchestration (dynamic chunking, dedup, gaps, reprocessing)
│   ├── run_processor.py                # Entry point with setup/monitoring
│   ├── batch_convert_extract.py        # Conversion + extraction helpers
│   └── config.json                     # Model/config (see Security about keys)
├── archive/                            # The historical content
│   ├── originals/                      # Original .doc/.docx files
│   ├── docx/                           # Converted .docx
│   └── markdown/                       # Extracted .md
├── processed/                          # Incremental and live outputs
│   ├── northern_argus_live_progress.json
│   ├── northern_argus_records_001.json
│   ├── northern_argus_records_002.json
│   └── northern_argus_records_003.json
├── site/                               # Hugo site
│   ├── config.yaml                     # baseURL, pagination, etc.
│   ├── content/                        # Section pages
│   ├── static/js/search.js             # Lunr search
│   └── themes/burra-archive/           # Templates
├── burra_news_complete_extraction.json # Legacy/aux data
└── extraction_progress.json            # Legacy/aux data
```

## 🔎 Processing Progress by Source (Pass-by-pass)

| Source (years) | Slug prefix | Pass 1 | Pass 2 | Pass 3 | Pass 4 | Site integrated |
|---|---|---|---|---|---|---|
| SA Register (1845–76) | `sa_register` | ✅ `processed/sa_register_pass_01/` | ✅ `..._pass_02/` | ✅ `..._pass_03/merged.json` | ✅ `..._pass_04/merged.backfilled.json` | ✅ many files in `site/content/records/1845_76_sa_register_content_*.md` |
| Record (1876–79) | `1876_79_record` | ✅ | ✅ | ✅ | ✅ | ✅ `site/content/records/1876_79_record_content_*.md` |
| Record (1880–99) | `1880_99_record` | ✅ | ✅ | ✅ | ✅ | ✅ `site/content/records/1880_99_record_content_*.md` |
| Record (1900–1919) | `1900_1919_record` | ✅ | ⏳ | ⏳ | ⏳ | ⛔ |
| Record (1920–39) | `1920_39_record` | ✅ | ⏳ | ⏳ | ⏳ | ⛔ |
| Record (1940–59) | `1940_59_record` | ✅ | ⏳ | ⏳ | ⏳ | ⛔ |
| Record (1960 – Part 77) | `1960_part_77_record` | ✅ | ⏳ | ⏳ | ⏳ | ⛔ |
| Northern Argus (1985–87) | `northern_argus` | ✅ | ✅ | ✅ | ✅ | ✅ `site/content/records/northern_argus_*.md` |
| Review Times Record | N/A | ⛔ | ⛔ | ⛔ | ⛔ | ⛔ |
| BCS & CN (1978–93) | N/A | ⛔ | ⛔ | ⛔ | ⛔ | ⛔ |
| Burra Broadcaster (1991–2016) | N/A | ⛔ | ⛔ | ⛔ | ⛔ | ⛔ |
| Mid North Broadcaster (2006–13) | N/A | ⛔ | ⛔ | ⛔ | ⛔ | ⛔ |

Notes
- Site downloads: all 14 source markdowns are available in `site/static/downloads/markdown/`.
- Search index: `site/static/js/search-data.json` is populated; regenerate after any bulk content updates to ensure full coverage.

## 🧱 Two-track plan

- Long-term: high-fidelity, reusable JSON records (stable IDs, provenance, backfilled metadata) suitable for real back-end indexing and apps.
- Near-term: static Hugo site as a proof-of-concept to validate usability and surface the data publicly.

## 🔧 Available Formats

### 1. **Original Files** (`archive/originals/`)
- **Format**: Microsoft Word (.doc/.docx)
- **Use**: Preserve original formatting and structure
- **Size**: ~100MB total
- **Best for**: Archival preservation, exact reproduction

### 2. **Modern DOCX** (`archive/docx/`)
- **Format**: Modern Word format (.docx)
- **Use**: Compatible with current Microsoft Office
- **Size**: ~75MB total  
- **Best for**: Editing, modern office compatibility

### 3. **Markdown** (`archive/markdown/`)
- **Format**: Universal text format (.md)
- **Use**: Platform-independent, version control friendly
- **Size**: ~30MB total
- **Best for**: Web publishing, development, long-term preservation

### 4. **Structured Data** (`*.json`)
- **Format**: Machine-readable JSON
- **Use**: Database import, API development, analysis
- **Size**: ~46MB total
- **Best for**: Search engines, data analysis, application development

## 🚀 Quick Start

### For Researchers
1. **Browse content**: Start with `archive/markdown/` for easy reading
2. **Search specific people**: Use the JSON files with any text editor's search
3. **Citation format**: See `docs/Burra In The News - Analysis.md` for proper attribution

### For Developers
1. **Static site**: Follow `docs/Static Site Design Plan.md`; GitHub Pages workflow at `.github/workflows/hugo.yml`.
2. **Data processing**: Use `scripts/*.py` passes (1–4) per source; outputs appear under `processed/<slug>_pass_0X/`.
3. **Per-record pages**: Generate from Pass 4 backfilled JSON into `site/content/records/` using `scripts/generate_hugo_records.py`.
4. **Search**: The generator updates `site/static/js/search-data.json`; regenerate after adding datasets.

### For Genealogists
1. **People search**: Content includes verified birth/death dates
2. **Family connections**: Eric Fuss's annotations link related individuals
3. **Source verification**: Original citations preserved for academic use

## 💡 Use Cases

### 🔍 **Search & Discovery**
- Full-text search across 170+ years
- People, places, and event discovery
- Family history research

### 📊 **Data Analysis**
- Historical trend analysis
- Social/economic pattern recognition  
- Community development studies

### 🌐 **Web Development**
- Static site generation (Hugo recommended)
- Search functionality (Lunr.js)
- Mobile-responsive historical archive

### 🎓 **Academic Research**
- Primary source citation
- Regional Australian history
- Mining community studies

### 🏛️ **Heritage & Tourism**
- Community engagement
- Historical interpretation
- Educational resources

## 🔧 JSON Data Structure

The JSON files contain structured data perfect for applications:

```json
{
  "file_name": "1876-79 Record .doc",
  "file_type": "doc (converted)",
  "extraction_method": "LibreOffice + python-docx",
  "paragraphs": [
    {
      "text": "John D. Cave - Auctioneer & General Commission Agent, Farrell's Flat",
      "style": "Normal"
    }
  ],
  "paragraph_count": 3747,
  "total_characters": 612112
}
```

**Perfect for:**
- 🔍 **Search indexing** (Elasticsearch, Solr, Lunr.js)
- 📱 **Mobile apps** (lightweight, structured)
- 🤖 **APIs** (REST/GraphQL endpoints)
- 📊 **Analytics** (business intelligence, research)
- 🧠 **AI/ML** (text analysis, pattern recognition)

## 🏗️ Next Steps: Static Website

This archive is designed to become a comprehensive static website. See `docs/Static Site Design Plan.md` for:

- **🎨 User experience design** for multiple audiences
- **⚡ Technical architecture** (Hugo + Lunr.js)
- **🔍 Advanced search** functionality
- **📱 Mobile-first** responsive design
- **🌐 Deployment strategy** (Netlify/GitHub Pages)

## 🤖 LLM Processing Pipeline

- **Model**: configurable small-LLM (see `scripts/config.example.json`)
- **Dynamic chunking**: Moves forward based on the last processed source line
- **Record IDs**: `northern_argus_<source_line_start>`
- **Deduplication**: Newer records overwrite older duplicates
- **Gap filling**: Inserts "uncategorized" records for missed content between records
- **Focused reprocessing**: Each uncategorized block is re-run as its own mini-chunk; successful extractions replace placeholders; gaps checked again
- **Monitoring**: Writes `processed/northern_argus_live_progress.json` after every chunk with timing and type counts

Output JSONs are under `processed/`. After Pass 4, use the backfilled merged JSON for site generation.

### Clean regenerate site content from completed datasets (optional)

Use this to reset `site/content/records` and build it deterministically from the four completed Pass 4 datasets.

```powershell
Remove-Item -Recurse -Force .\site\content\records
Remove-Item -Force .\site\static\js\search-data.json
python .\scripts\generate_hugo_records.py processed\sa_register_pass_04\merged.backfilled.json
python .\scripts\generate_hugo_records.py processed\1876_79_record_pass_04\merged.backfilled.json
python .\scripts\generate_hugo_records.py processed\1880_99_record_pass_04\merged.backfilled.json
python .\scripts\generate_hugo_records.py processed\northern_argus_pass_04\merged.backfilled.json
hugo serve -s site
```

## 👥 Target Audiences

### 🔬 **Researchers & Academics**
- Primary source access with verified citations
- Comprehensive historical timeline
- Cross-referenced genealogical data

### 👨‍👩‍👧‍👦 **Genealogists & Family Historians**
- Verified birth/death/marriage records
- Family connection mapping
- Multi-generational story discovery

### 🏠 **Local Community & Tourists**
- Heritage discovery and engagement
- Historical context for modern Burra
- Shareable stories and connections

### 💻 **Developers & Data Scientists**
- Clean, structured historical dataset
- API development foundation
- Text analysis and mining opportunities

## 📜 Historical Significance

This archive represents one of the most **complete community historical documentations** ever created, featuring:

- **📈 Complete lifecycle** of an Australian mining town
- **🔗 Scholarly enhancement** of primary sources
- **⚖️ Critical analysis** with error correction
- **🌍 Model methodology** for community history preservation

## 🤝 Contributing

This is a historical preservation project. Contributions welcome for:

- **🌐 Website development** (see design plans)
- **🔍 Search functionality** improvements  
- **📱 Mobile applications** development
- **📊 Data analysis** and visualization
- **🐛 Error corrections** or additional annotations

## 📄 License

This repository contains historical documents and derived works. See [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- **Eric Fuss**: Original compiler and researcher whose decades of work made this archive possible
- **Ian Auhl**: SA Register research (1845-1876)
- **The original publishers**: All newspaper publishers who documented Burra's history
- **South Australia Archives**: Source of vital records verification

## 📞 Contact

For questions about this digital archive or the original research, please:

1. **Open an issue** for technical questions
2. **Check the docs/** folder for detailed information
3. **Review the analysis document** for research methodology

---

**This archive stands as a testament to the power of dedicated historical scholarship and the importance of preserving community heritage for future generations.**

## 🔐 Security and API Keys

- Do not commit API keys. The project's `.gitignore` excludes `config.json` globally, which covers `scripts/config.json`.
- Keep API keys only in local, ignored files (or environment variables).
- If a key was ever committed previously, rotate it.
