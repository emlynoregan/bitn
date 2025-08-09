# Northern Argus LLM Processing Instructions

## Document Overview
**Source**: `1985-87_Northern__Argus.md` (3,331 lines)  
**Content**: Eric Fuss's extraction from Northern Argus newspaper, August 1985 - December 1987  
**Output**: ~150-200 individual records

## Key Patterns to Recognize

### Issue Headers (Record Delimiters)
```
CXV, 8020, 21 August 1985, page 1
CXV, 8025, 25 September 1985, MISSING
```

### Content Types
- **News**: Headlines + content
- **Obituary**: "Obituary. [Name] died..."
- **Birth**: "Birth. To [Parents], a [son/daughter], [Name]"
- **Marriage**: "Marriage. [Location] [Date]"
- **Advertisement**: "Advt. [Business details]"

### Eric's Additions (in brackets)
- `[Born 16 June 1904, Adelaide: buried Burra 14 August 1985.]`
- `[Photo.]` or `[Two photographs of the aftermath.]`

## Your Task
Process the current chunk and output a JSON array of records. Records can be one of two kinds:
- `header` (header anchor records)
- `content` (normal article/content records)

**Key Rules**:
1. Extract each article/item as a separate record  
2. Process everything you see - don't worry about duplicates
3. Stop processing if the last record appears incomplete

## Output Format

```json
[
  {
    "record_kind": "header",
    "source_document": "1985-87_Northern__Argus.md",
    "source_line_start": 11,
    "source_line_end": 11,
    "original_text": "CXV, 8020, 21 August 1985, page 1",
    "metadata": {
      "publication": "Northern Argus",
      "date": "1985-08-21",
      "volume": "CXV",
      "issue_number": "8020",
      "page": "1"
    }
  },
  {
    "record_kind": "content",
    "source_document": "1985-87_Northern__Argus.md",
    "source_line_start": 13,
    "source_line_end": 20,
    "issue_reference": "CXV, 8020, 21 August 1985, page 1",
    "original_text": "Fire at Jennison's in Burra\n\nOn Sunday morning fire...",
    "metadata": {
      "publication": "Northern Argus",
      "date": "1985-08-21",
      "volume": "CXV",
      "issue_number": "8020", 
      "page": "1",
      "article_type": "news",
      "headline": "Fire at Jennison's in Burra",
      "people_mentioned": ["Jennison"],
      "places_mentioned": ["Burra"],
      "topics": ["fire", "business", "emergency"],
      "eric_notes": ["Two photographs of the aftermath."]
    }
  }
]
```

## Processing Steps

### 1. Extract Each Record
- **Article boundaries**: Blank lines, topic headers, subject changes
- **Original text**: Everything between boundaries (preserve exactly)
- **Metadata**: Extract dates (→ YYYY-MM-DD), people, places, topics

### 1a. Emit Header Anchors
- When you encounter an issue header line (e.g., `CXV, 8027, 9 October 1985, page 21` or `MISSING`), emit a separate record with `record_kind: "header"`.
- The `original_text` must be exactly the header line.
- Populate `metadata.volume`, `metadata.issue_number`, `metadata.date` (ISO if possible), and `metadata.page` if present. Do not invent values.
- Only emit a header anchor when the header text is present in the chunk.

### 2. Stop at Incomplete Records
If last item appears cut off (mid-sentence, header only, etc.), exclude it.

## Metadata Guidelines

**Article Types** (choose the most appropriate; applies to `record_kind: "content"`):
- `news` - General news articles, events, announcements
- `obituary` - Death notices ("Obituary. [Name] died...")
- `birth` - Birth announcements ("Birth. To [Parents], a [son/daughter]...")
- `marriage` - Marriage announcements ("Marriage. [Location/Church]...")
- `advertisement` - Business advertisements ("Advt. [Business details]...")
- `letter` - Letters to editor ("Letter to the Editor from [Name]...")
- `missing_issue` - Missing newspaper issues ("[Date], MISSING")
- `community_notice` - Community announcements, events, meetings
- `other` - Use for content that should be included but doesn't fit above categories

**IMPORTANT**: Always include content that represents historical value, even if the type is unclear. Use `other` and add a descriptive headline when needed.

**Topics** (use consistent keywords):
- Events: fire, accident, death, birth, marriage, show, race
- Organizations: hospital, council, school, church, club, business  
- Infrastructure: road, building, power, water, development
- Community: celebration, fundraising, award, appointment
- Legal: court, police, theft, dispute

**People/Places**: Extract all names and locations, including from Eric's bracketed additions

**Eric's Notes**: Include ALL bracketed content in `eric_notes` array

## Quality Rules
1. Preserve Eric's exact text (no spelling/grammar fixes)
2. Use consistent place names ("Burra" not "burra")
3. Extract full names from Eric's research
4. Double-check date parsing
5. Use standard topic keywords

## Special Cases
- **Missing issues**: Create record with `article_type: "missing_issue"`
- **Long articles**: Add `"continuation": "continues_from_previous"` to metadata if needed
- **Grouped items**: Multiple births/marriages can be one record if no clear separation

**Goal**: Create individual, searchable records while preserving Eric's scholarly work exactly as compiled.

## Spot-Checking Process (QA Checklist)

Use this quick procedure to verify fidelity and granularity after a run:

1) Select three representative chunks
- Early, mid, and late in the document (e.g., `chunk_1-80.json`, a middle chunk, and a late chunk).

2) Compare chunk records to source lines
- For each selected chunk, open the corresponding line range in `archive/markdown/1985-87_Northern__Argus.md`.
- Confirm every item in the source lines appears as a record in the chunk JSON (1:1 where appropriate; grouped only when the source groups them).

3) Verify header anchors
- Ensure header lines within the range are emitted as `record_kind: "header"` with correct `volume`, `issue_number`, `date` (ISO if parsable), and `page`/`pages`.
- Check there are no invented/missing anchors.

4) Check metadata completeness
- For `record_kind: "content"`, confirm `article_type`, `headline`, `people_mentioned`, `places_mentioned`, `topics`, and `eric_notes` are present where applicable.
- If `date/volume/issue/page` are missing in content, ensure they are present on a preceding header anchor so backfill can populate them.

5) Look for aggregation or omissions
- Ensure multi-item digests are split into separate content records when distinct items are clearly delineated.
- Confirm no gaps: scan between `source_line_end` of one record and `source_line_start` of the next.

6) Dedupe across overlaps
- Check that overlapping chunks did not produce duplicate content records; dedupe by `record_id` (based on `source_line_start`) and by identical `original_text` when needed.

7) Record any issues
- Note any systematic misses (e.g., specific patterns or headers) to tune the prompt or backfill logic.