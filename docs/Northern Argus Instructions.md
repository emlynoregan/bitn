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
Process the current chunk and output a JSON array of records. 

**Key Rules**:
1. Extract each article/item as a separate record  
2. Process everything you see - don't worry about duplicates
3. Stop processing if the last record appears incomplete

## Output Format

```json
[
  {
    "source_document": "1985-87_Northern__Argus.md",
    "source_line_start": 11,
    "source_line_end": 15,
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

### 2. Stop at Incomplete Records
If last item appears cut off (mid-sentence, header only, etc.), exclude it.

## Metadata Guidelines

**Article Types** (choose the most appropriate):
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