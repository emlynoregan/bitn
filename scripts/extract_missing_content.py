#!/usr/bin/env python3
"""
Extract content from the newly converted files
"""

import json
from pathlib import Path
from docx import Document

def extract_docx_content(file_path: Path, original_name: str = None) -> dict:
    """Extract content from .docx files"""
    try:
        doc = Document(file_path)
        
        paragraphs = []
        for para in doc.paragraphs:
            text = para.text.strip()
            if text and len(text) > 2:
                paragraphs.append({
                    'text': text,
                    'style': para.style.name if para.style else 'Normal'
                })
        
        return {
            'file_name': original_name or file_path.name,
            'converted_file': file_path.name if original_name else None,
            'file_type': 'doc (converted)' if original_name else 'docx',
            'extraction_method': 'LibreOffice + python-docx',
            'paragraphs': paragraphs,
            'paragraph_count': len(paragraphs),
            'total_characters': sum(len(p['text']) for p in paragraphs)
        }
        
    except Exception as e:
        print(f"❌ Extraction failed: {e}")
        return None

def check_and_extract_missing():
    """Check if the two files are properly extracted and extract if needed"""
    
    # Load existing progress
    progress_file = "extraction_progress.json"
    
    try:
        with open(progress_file, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
    except:
        print("❌ Could not load progress file")
        return
    
    # Files that were just converted
    target_files = [
        "1845-76 SA Register.doc",
        "1876-79 Record .doc"
    ]
    
    print("🔍 Checking extraction status of newly converted files...")
    
    needs_extraction = []
    for target_file in target_files:
        # Find in existing data
        found = None
        for item in existing_data:
            if item.get('file_name') == target_file:
                found = item
                break
        
        if found:
            paras = found.get('paragraph_count', 0)
            if paras > 0:
                print(f"✅ {target_file}: {paras:,} paragraphs already extracted")
            else:
                print(f"⚠️  {target_file}: Found but 0 paragraphs - needs re-extraction")
                needs_extraction.append(target_file)
        else:
            print(f"❌ {target_file}: Not found in progress - needs extraction")
            needs_extraction.append(target_file)
    
    if not needs_extraction:
        print("\n🎉 All files properly extracted!")
        return
    
    print(f"\n🔄 Extracting content from {len(needs_extraction)} files...")
    
    temp_folder = Path("temp_converted")
    updated_data = existing_data.copy()
    
    for file_name in needs_extraction:
        # Find corresponding converted file
        converted_name = file_name.replace('.doc', '.docx')
        converted_path = temp_folder / converted_name
        
        if not converted_path.exists():
            print(f"❌ Converted file not found: {converted_name}")
            continue
        
        print(f"\n📄 Extracting: {file_name}")
        print(f"    From: {converted_name}")
        
        # Extract content
        content = extract_docx_content(converted_path, file_name)
        
        if content:
            # Remove old entry if exists
            updated_data = [item for item in updated_data if item.get('file_name') != file_name]
            
            # Add new extraction
            updated_data.append(content)
            
            print(f"    ✅ Extracted {content['paragraph_count']:,} paragraphs ({content['total_characters']:,} chars)")
        else:
            print(f"    ❌ Extraction failed")
    
    # Save updated progress
    try:
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump(updated_data, f, indent=2, ensure_ascii=False)
        
        # Also save as final results
        with open("burra_news_complete_extraction.json", 'w', encoding='utf-8') as f:
            json.dump(updated_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Updated progress saved!")
        
        # Show final summary
        total_docs = len(updated_data)
        total_paras = sum(item.get('paragraph_count', 0) for item in updated_data)
        total_chars = sum(item.get('total_characters', 0) for item in updated_data)
        
        print(f"\n📊 FINAL SUMMARY:")
        print(f"   • Documents: {total_docs}")
        print(f"   • Paragraphs: {total_paras:,}")
        print(f"   • Characters: {total_chars:,}")
        
    except Exception as e:
        print(f"❌ Failed to save: {e}")

if __name__ == "__main__":
    check_and_extract_missing()