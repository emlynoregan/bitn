#!/usr/bin/env python3
"""
Hugo Content Processor for Burra in the News Archive
Converts JSON archive data into Hugo-compatible markdown files
"""

import json
import os
import re
from pathlib import Path
from datetime import datetime
import yaml
from typing import Dict, List, Any
import unicodedata

def clean_filename(filename: str) -> str:
    """Clean filename for filesystem safety"""
    # Remove file extension
    name = Path(filename).stem
    # Replace spaces and special chars with hyphens
    name = re.sub(r'[^\w\s-]', '', name)
    name = re.sub(r'[-\s]+', '-', name)
    return name.lower().strip('-')

def extract_publication_name(filename: str) -> str:
    """Extract publication name from filename"""
    filename = filename.lower()
    
    # Publication mappings based on filename patterns
    pub_mappings = {
        'sa register': 'SA Register',
        'record': 'Record',
        'broadcaster': 'Burra Broadcaster', 
        'northern argus': 'Northern Argus',
        'midnorthbroadcaster': 'Mid North Broadcaster',
        'burra broadcaster': 'Burra Broadcaster',
        'bcs': 'BCS',
        'cn': 'CN'
    }
    
    for key, value in pub_mappings.items():
        if key in filename:
            return value
    
    # Default fallback
    return 'Unknown Publication'

def extract_date_range(filename: str) -> tuple:
    """Extract start and end years from filename"""
    # Look for year patterns like 1845-76, 1880-99, 1991-2016
    patterns = [
        r'(\d{4})-(\d{4})',  # Full years: 1991-2016
        r'(\d{4})-(\d{2})',  # Short end year: 1845-76
    ]
    
    for pattern in patterns:
        match = re.search(pattern, filename)
        if match:
            start_year = int(match.group(1))
            end_year_str = match.group(2)
            
            if len(end_year_str) == 2:
                # Handle short year format (e.g., 76 -> 1876)
                if int(end_year_str) < 50:  # Assume 2000s
                    end_year = 2000 + int(end_year_str)
                else:  # Assume 1900s
                    end_year = 1900 + int(end_year_str)
            else:
                end_year = int(end_year_str)
            
            return (start_year, end_year)
    
    # Single year pattern
    single_year = re.search(r'(\d{4})', filename)
    if single_year:
        year = int(single_year.group(1))
        return (year, year)
    
    return (1845, 2016)  # Default range

def normalize_text(text: str) -> str:
    """Normalize text for consistent encoding"""
    if not text:
        return ""
    
    # Normalize unicode
    text = unicodedata.normalize('NFKD', text)
    
    # Clean up common issues
    text = re.sub(r'\s+', ' ', text)  # Multiple spaces
    text = text.strip()
    
    return text

def create_frontmatter(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Create Hugo frontmatter from document metadata"""
    file_name = doc.get('file_name', '')
    publication = extract_publication_name(file_name)
    start_year, end_year = extract_date_range(file_name)
    
    # Use start year as the date for sorting
    date = datetime(start_year, 1, 1)
    
    frontmatter = {
        'title': file_name,
        'date': date.isoformat(),
        'publication': publication,
        'start_year': start_year,
        'end_year': end_year,
        'type': 'article',
        'paragraph_count': doc.get('paragraph_count', 0),
        'total_characters': doc.get('total_characters', 0),
        'extraction_method': doc.get('extraction_method', ''),
        'original_filename': file_name,
        'tags': [
            publication.lower().replace(' ', '-'),
            f"decade-{start_year//10*10}s",
            f"period-{start_year}-{end_year}"
        ]
    }
    
    # Add decade taxonomy
    for year in range(start_year, end_year + 1, 10):
        decade = year // 10 * 10
        frontmatter['tags'].append(f"{decade}s")
    
    return frontmatter

def process_content(paragraphs: List[Dict[str, Any]]) -> str:
    """Process paragraphs into markdown content"""
    content_lines = []
    
    for para in paragraphs:
        text = normalize_text(para.get('text', ''))
        if not text:
            continue
            
        # Handle different paragraph styles
        style = para.get('style', '')
        
        if 'heading' in style.lower():
            content_lines.append(f"## {text}\n")
        elif 'title' in style.lower():
            content_lines.append(f"# {text}\n")
        else:
            content_lines.append(f"{text}\n")
    
    return '\n'.join(content_lines)

def create_hugo_content(doc: Dict[str, Any], output_dir: Path) -> None:
    """Create Hugo markdown file from document"""
    
    frontmatter = create_frontmatter(doc)
    content = process_content(doc.get('paragraphs', []))
    
    # Create publication directory
    publication = frontmatter['publication']
    pub_dir = output_dir / 'publications' / clean_filename(publication)
    pub_dir.mkdir(parents=True, exist_ok=True)
    
    # Create filename
    safe_filename = clean_filename(frontmatter['original_filename'])
    md_file = pub_dir / f"{safe_filename}.md"
    
    # Create markdown file
    with open(md_file, 'w', encoding='utf-8') as f:
        # Write frontmatter
        f.write('---\n')
        yaml.dump(frontmatter, f, default_flow_style=False, allow_unicode=True)
        f.write('---\n\n')
        
        # Write content
        f.write(content)
    
    print(f"✓ Created: {md_file.relative_to(output_dir)}")

def create_publication_pages(docs: List[Dict[str, Any]], output_dir: Path) -> None:
    """Create publication index pages"""
    
    # Group documents by publication
    publications = {}
    for doc in docs:
        pub_name = extract_publication_name(doc.get('file_name', ''))
        if pub_name not in publications:
            publications[pub_name] = []
        publications[pub_name].append(doc)
    
    # Create publication section page
    pub_section_dir = output_dir / 'publications'
    pub_section_dir.mkdir(parents=True, exist_ok=True)
    
    # Main publications index
    index_content = """---
title: "Browse by Publication"
type: "section"
layout: "publications"
---

# Browse by Publication

Explore the archive organized by newspaper and publication. Each publication represents a different perspective and time period in Burra's history.

"""
    
    with open(pub_section_dir / '_index.md', 'w', encoding='utf-8') as f:
        f.write(index_content)
    
    # Individual publication pages
    for pub_name, pub_docs in publications.items():
        pub_dir = pub_section_dir / clean_filename(pub_name)
        pub_dir.mkdir(exist_ok=True)
        
        # Calculate date range for this publication
        years = []
        for doc in pub_docs:
            start_year, end_year = extract_date_range(doc.get('file_name', ''))
            years.extend([start_year, end_year])
        
        min_year = min(years) if years else 1845
        max_year = max(years) if years else 2016
        
        frontmatter = {
            'title': pub_name,
            'type': 'publication',
            'publication': pub_name,
            'date_range': f"{min_year}-{max_year}",
            'document_count': len(pub_docs),
            'total_paragraphs': sum(doc.get('paragraph_count', 0) for doc in pub_docs)
        }
        
        content = f"""# {pub_name}

**Coverage Period:** {min_year}-{max_year}  
**Documents:** {len(pub_docs)}  
**Total Content:** {sum(doc.get('paragraph_count', 0) for doc in pub_docs)} paragraphs

{pub_name} provides valuable insights into Burra's history during the period {min_year}-{max_year}. 
This collection contains {len(pub_docs)} documents with comprehensive coverage of local events, 
community developments, and historical milestones.

## Documents in this Publication

"""
        
        with open(pub_dir / '_index.md', 'w', encoding='utf-8') as f:
            f.write('---\n')
            yaml.dump(frontmatter, f, default_flow_style=False, allow_unicode=True)
            f.write('---\n\n')
            f.write(content)

def create_search_index(docs: List[Dict[str, Any]], output_dir: Path) -> None:
    """Create search index for Lunr.js"""
    
    search_data = []
    
    for doc in docs:
        file_name = doc.get('file_name', '')
        publication = extract_publication_name(file_name)
        start_year, end_year = extract_date_range(file_name)
        
        # Combine all paragraph text for searching
        content_text = ' '.join([
            normalize_text(para.get('text', '')) 
            for para in doc.get('paragraphs', [])
        ])
        
        search_entry = {
            'id': clean_filename(file_name),
            'title': file_name,
            'publication': publication,
            'date_range': f"{start_year}-{end_year}",
            'content': content_text[:1000],  # Limit for performance
            'url': f"/publications/{clean_filename(publication)}/{clean_filename(file_name)}/"
        }
        
        search_data.append(search_entry)
    
    # Save search index
    static_dir = output_dir.parent / 'static' / 'js'
    static_dir.mkdir(parents=True, exist_ok=True)
    
    with open(static_dir / 'search-data.json', 'w', encoding='utf-8') as f:
        json.dump(search_data, f, ensure_ascii=False, indent=2)
    
    print(f"✓ Created search index with {len(search_data)} entries")

def main():
    """Main processing function"""
    print("🚀 Starting Hugo content processing...")
    
    # Paths
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    json_file = project_root / 'burra_news_complete_extraction.json'
    output_dir = project_root / 'site' / 'content'
    
    # Load JSON data
    print(f"📖 Loading data from: {json_file}")
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            archive_data = json.load(f)
    except FileNotFoundError:
        print(f"❌ Error: Could not find {json_file}")
        return
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing JSON: {e}")
        return
    
    print(f"📊 Processing {len(archive_data)} documents...")
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Process each document
    for i, doc in enumerate(archive_data, 1):
        print(f"⚙️  Processing ({i}/{len(archive_data)}): {doc.get('file_name', 'Unknown')}")
        try:
            create_hugo_content(doc, output_dir)
        except Exception as e:
            print(f"❌ Error processing {doc.get('file_name', 'Unknown')}: {e}")
    
    # Create publication pages
    print("📚 Creating publication index pages...")
    create_publication_pages(archive_data, output_dir)
    
    # Create search index
    print("🔍 Building search index...")
    create_search_index(archive_data, output_dir)
    
    # Create home page content
    print("🏠 Creating home page...")
    home_content = """---
title: "Home"
type: "homepage"
---

Welcome to the Burra in the News digital archive."""
    
    with open(output_dir / '_index.md', 'w', encoding='utf-8') as f:
        f.write(home_content)
    
    print("✅ Hugo content processing complete!")
    print(f"📁 Content created in: {output_dir}")
    print(f"📊 Total documents processed: {len(archive_data)}")

if __name__ == "__main__":
    main()