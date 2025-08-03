# Burra in the News - Data Design Document

## Overview

This document outlines the data architecture and processing strategy for transforming Eric Fuss's historical newspaper archive into a searchable, accessible digital resource for the Burra in the News website.

## Current Data State

### Source Materials
- **14 Original Documents**: Mix of `.doc` and `.docx` files spanning 1845-2016
- **Archive Structure**: 
  - `archive/originals/` - Original Word documents (32MB)
  - `archive/docx/` - Converted .docx versions (73MB) 
  - `archive/markdown/` - Extracted markdown versions (30MB)
- **JSON Extracts**: Complete structured data in `burra_news_complete_extraction.json` (32MB)

### Document Categories
1. **Research Documents (2 files)**:
   - `Compiler_s Note 2015.doc` - Eric's methodology and overview
   - `Eric_s Research - pages notes.docx` - Document counts and statistics

2. **Primary Source Documents (12 files)**:
   - `1845-76 SA Register.doc` (613 pages)
   - `1876-79 Record .doc` (195 pages) 
   - `1880-99 Record .doc` (multiple volumes)
   - `1900-1919 Record.doc`
   - `1920-39 Record.doc`
   - `1940-59 Record.doc`
   - `1960-Part 77 Record.doc`
   - `1978-1993 BCS & CN.doc`
   - `Review Times Record.doc` (87 pages)
   - `1985-87 Northern Argus .doc` (73 pages)
   - `1991-2016 Burra Broadcaster.doc`
   - `2006-13 MidNorthBroadcaster .doc`

## Website Data Architecture

### Level 1: Archive Access
**Purpose**: Provide direct access to Eric's complete work

**Components**:
1. **Archive Overview Page**
   - Based on "Burra In The News - Analysis.md"
   - HTML versions of all 14 documents (clickable list)
   - Performance warnings for large files
   - Download links for zip archives

2. **Download Packages**:
   - `burra-originals.zip` - Eric's original Word documents
   - `burra-markdown.zip` - Cleaned markdown versions
   - Individual file downloads with size warnings

3. **Document Viewer Pages**:
   - Full HTML rendering of each markdown file
   - Navigation between documents
   - Metadata display (date range, page count, source info)
   - Back-reference to source document

### Level 2: Searchable Records
**Purpose**: Break down the 12 primary source documents into individual, searchable records

## Record Structure Analysis

### Current Format Pattern (from Northern Argus sample)
```
CXV, 8020, 21 August 1985, page 1

Fire at Jennison's in Burra

On Sunday morning fire caused extensive damage to Jennison's Tyre Services...
[Two photographs of the aftermath.]

CXV, 8020, 21 August 1985, page 23

Obituary. George Hiles Cockrum of Mt Bryan died last week...
[Born 16 June 1904, Adelaide: buried Burra 14 August 1985.]
```

### Identified Record Delimiters
Eric uses consistent patterns that can serve as record boundaries:

1. **Issue References**: Pattern like "CXV, 8020, 21 August 1985, page X"
2. **Date Headers**: Various formats depending on publication
3. **Missing Issue Markers**: "MISSING" or "NOT AVAILABLE"
4. **Subject Separators**: Blank lines between distinct items

### Record Components
Each record should contain:

**Original Content**:
- Eric's unprocessed text exactly as written
- Preservation of his notation system and style

**Processed Metadata**:
- **Publication**: Source newspaper name
- **Date**: Standardized date format (YYYY-MM-DD)
- **Issue Reference**: Volume, number, page information
- **Headline/Subject**: Extracted topic or headline
- **Article Type**: News, obituary, advertisement, announcement, etc.
- **People Mentioned**: Extracted names (where parseable)
- **Places Mentioned**: Geographic references
- **Topics/Keywords**: Subject matter tags
- **Source Document**: Reference to parent document
- **Line Numbers**: Starting position in original document

**Navigation References**:
- Link back to complete source document
- Cross-references to related records
- Chronological navigation (prev/next by date)

## Processing Strategy

### Phase 1: Document Analysis
For each of the 12 primary source documents:

1. **Manual Structure Analysis**:
   - Identify Eric's formatting patterns
   - Document record delimiter patterns
   - Note any inconsistencies or special cases
   - Estimate record counts per document

2. **Create Analysis Templates**:
   ```json
   {
     "document": "1985-87_Northern_Argus.md",
     "total_estimated_records": 150,
     "delimiter_patterns": [
       "^[A-Z]+, \\d+, \\d+ [A-Za-z]+ \\d{4}, page \\d+$",
       "^\\d+ [A-Za-z]+ \\d{4}$"
     ],
     "special_cases": ["MISSING entries", "Multi-page articles"],
     "metadata_patterns": {
       "dates": "DD Month YYYY format",
       "people": "Names in regular text, some in brackets",
       "brackets": "Eric's editorial additions"
     }
   }
   ```

### Phase 2: LLM-Assisted Record Extraction
For each document, deploy an LLM with specific instructions to:

1. **Parse sequentially** through the markdown content
2. **Identify record boundaries** using the analyzed patterns
3. **Extract metadata** according to the defined schema
4. **Preserve original text** exactly as Eric wrote it
5. **Output structured JSON** for each record

**Example Output Schema**:
```json
{
  "record_id": "northern_argus_1985_08_21_001",
  "source_document": "1985-87_Northern_Argus.md",
  "source_line_start": 11,
  "source_line_end": 15,
  "original_text": "CXV, 8020, 21 August 1985, page 1\n\nFire at Jennison's in Burra\n\nOn Sunday morning fire caused extensive damage...",
  "metadata": {
    "publication": "Northern Argus",
    "date": "1985-08-21",
    "issue_reference": "CXV, 8020",
    "page": 1,
    "headline": "Fire at Jennison's in Burra",
    "article_type": "news",
    "people_mentioned": ["Jennison"],
    "places_mentioned": ["Burra"],
    "topics": ["fire", "business", "damage"],
    "eric_notes": ["Two photographs of the aftermath."]
  }
}
```

### Phase 3: Hugo Integration
1. **Generate Individual Pages**: Each record becomes a Hugo content file
2. **Create Indexes**: By date, topic, publication, people
3. **Build Search Data**: Feed into Lunr.js search index
4. **Cross-Reference System**: Link related records

## Technical Implementation

### Hugo Content Structure
```
content/
├── archive/                  # Full document access
│   ├── _index.md
│   ├── sa-register/
│   ├── burra-record/
│   └── ...
├── records/                  # Individual records
│   ├── _index.md
│   ├── 1845/
│   ├── 1846/
│   └── ...
├── search/
├── timeline/
└── downloads/
```

### Record Page Template
Each record page should display:
- Original text in Eric's format
- Cleaned metadata in structured format
- Navigation to related records
- Link back to source document
- Search-friendly content for indexing

### Search Enhancement
- **Lunr.js Index**: Include all record content and metadata
- **Faceted Search**: Filter by date range, publication, topic
- **Full-Text Search**: Across original content and metadata
- **Fuzzy Matching**: Handle historical spelling variations

## Feasibility Assessment

### Does This Approach Make Sense?
**✅ Strengths**:
- Preserves Eric's complete work while making it searchable
- Creates granular access to individual items
- Maintains scholarly integrity through source attribution
- Enables powerful cross-referencing and discovery

**⚠️ Considerations**:
- LLM parsing may require manual verification/correction
- Large number of individual pages (estimated 5,000+ records)
- Need to handle parsing inconsistencies gracefully

### Example Record Page Layout
```
═══════════════════════════════════════════
🏛️ BURRA IN THE NEWS ARCHIVE

📰 Northern Argus • August 21, 1985 • Page 1

Fire at Jennison's in Burra
═══════════════════════════════════════════

🔗 Source: 1985-87 Northern Argus (Line 11-15)

📋 ORIGINAL RECORD
CXV, 8020, 21 August 1985, page 1

Fire at Jennison's in Burra

On Sunday morning fire caused extensive damage to 
Jennison's Tyre Services. The alarm was raised by a 
passer-by at 5.52 a.m...

[Two photographs of the aftermath.]

📊 METADATA
Date: August 21, 1985
Publication: Northern Argus  
Issue: CXV, 8020
Type: News Article
Topics: Fire, Business, Emergency Services
People: Jennison
Places: Burra
Eric's Notes: Two photographs of the aftermath

🔍 RELATED RECORDS
• Other Jennison's mentions
• Other fires in Burra
• Northern Argus, August 1985

⬅️ Previous Record | Next Record ➡️
📚 Back to Northern Argus | 🏠 Home
═══════════════════════════════════════════
```

### Technical Limitations

**Hugo & Static Site Generation**:
- ✅ **Can handle thousands of pages**: Hugo builds efficiently
- ✅ **Fast search**: Lunr.js performs well with large indexes
- ⚠️ **Build time**: May increase with 5,000+ pages
- ⚠️ **GitHub Pages limits**: 1GB total size limit

**Search Functionality**:
- ✅ **Text search**: Lunr.js excellent for full-text search
- ✅ **Faceted filtering**: Can implement date/topic filters  
- ✅ **Cross-references**: Hugo's powerful linking system
- ⚠️ **Real-time indexing**: Static - requires rebuild for updates

**Data Processing**:
- ⚠️ **LLM accuracy**: May need human verification
- ⚠️ **Parsing complexity**: Historical text formatting variations
- ✅ **Batch processing**: Can iterate and improve
- ✅ **Source preservation**: Original text always maintained

## Recommended Next Steps

1. **Validate approach**: Manually analyze 2-3 documents to confirm patterns
2. **Build prototype**: Process one document (Northern Argus) end-to-end
3. **Test search performance**: Verify Lunr.js handles the record volume
4. **Iterate on metadata schema**: Refine based on actual content patterns
5. **Scale to full archive**: Process remaining 11 documents

This approach provides both scholarly access to Eric's complete work and modern searchability for researchers, genealogists, and community members interested in Burra's history.