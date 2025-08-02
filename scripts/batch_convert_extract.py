#!/usr/bin/env python3
"""
Batch Document Converter & Extractor - One file at a time
Converts .doc files and extracts content progressively
"""

import os
import sys
import subprocess
from pathlib import Path
import json
from typing import Dict, List, Any
import shutil
import time

def find_libreoffice():
    """Find LibreOffice executable"""
    paths = [
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        "soffice",
        "libreoffice"
    ]
    
    for path in paths:
        if shutil.which(path) or Path(path).exists():
            return path
    return None

def convert_single_doc(doc_file: Path, output_dir: Path, soffice_path: str) -> Path:
    """Convert a single .doc file to .docx"""
    try:
        output_dir.mkdir(exist_ok=True)
        
        # Check if already converted
        converted_file = output_dir / f"{doc_file.stem}.docx"
        if converted_file.exists():
            print(f"    ✅ Already converted (found {converted_file.name})")
            return converted_file
        
        cmd = [
            soffice_path,
            '--headless',
            '--convert-to', 'docx',
            '--outdir', str(output_dir),
            str(doc_file)
        ]
        
        print(f"    Converting {doc_file.name}...")
        
        # Run with shorter timeout
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0:
            converted_file = output_dir / f"{doc_file.stem}.docx"
            if converted_file.exists():
                return converted_file
        
        print(f"    ⚠️  Conversion failed: {result.stderr}")
        return None
        
    except subprocess.TimeoutExpired:
        print(f"    ⚠️  Conversion timed out (>2 minutes)")
        return None
    except Exception as e:
        print(f"    ⚠️  Error: {e}")
        return None

def extract_docx_content(file_path: Path, original_name: str = None) -> Dict[str, Any]:
    """Extract content from .docx files"""
    try:
        from docx import Document
        
        doc = Document(file_path)
        
        paragraphs = []
        for para in doc.paragraphs:
            text = para.text.strip()
            if text and len(text) > 2:  # Filter very short lines
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
        print(f"    ⚠️  Extraction failed: {e}")
        return None

def load_progress(filename: str = "extraction_progress.json") -> List[Dict]:
    """Load existing progress"""
    try:
        if Path(filename).exists():
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"⚠️  Failed to load progress: {e}")
    return []

def save_progress(documents: List[Dict], filename: str = "extraction_progress.json"):
    """Save progress after each file"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(documents, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"⚠️  Failed to save progress: {e}")
        return False

def is_already_processed(file_name: str, documents: List[Dict]) -> bool:
    """Check if file was already processed"""
    return any(doc.get('file_name') == file_name for doc in documents)

def main():
    """Process files one by one with progress tracking"""
    print("📄 Batch Document Converter & Extractor")
    print("=" * 50)
    
    # Find LibreOffice
    soffice_path = find_libreoffice()
    if not soffice_path:
        print("❌ LibreOffice not found")
        return
    
    print(f"✅ Found LibreOffice: {soffice_path}")
    
    source_folder = Path("Burra in the News")
    temp_folder = Path("temp_converted")
    
    if not source_folder.exists():
        print(f"❌ Source folder not found")
        return
    
    # Get all files to process
    doc_files = [f for f in source_folder.glob("*.doc") if f.suffix.lower() == '.doc']
    docx_files = list(source_folder.glob("*.docx"))
    
    print(f"\n📊 Files to process:")
    print(f"   • .doc files to convert: {len(doc_files)}")
    print(f"   • .docx files to extract: {len(docx_files)}")
    print(f"   • Total files: {len(doc_files) + len(docx_files)}")
    
    # Load existing progress
    documents = load_progress("extraction_progress.json")
    processed_count = len(documents)
    total_files = len(doc_files) + len(docx_files)
    
    if documents:
        print(f"📂 Loaded existing progress: {len(documents)} files already processed")
    
    # Process .doc files (convert + extract)
    print(f"\n🔄 Converting and extracting .doc files...")
    for i, doc_file in enumerate(sorted(doc_files), 1):
        # Skip if already processed
        if is_already_processed(doc_file.name, documents):
            print(f"\n[SKIP] {doc_file.name} - already processed")
            continue
            
        print(f"\n[{len(documents) + 1}/{total_files}] Processing: {doc_file.name}")
        
        # Convert to .docx
        converted_file = convert_single_doc(doc_file, temp_folder, soffice_path)
        
        if converted_file:
            print(f"    ✅ Converted successfully")
            
            # Extract content
            content = extract_docx_content(converted_file, doc_file.name)
            if content:
                documents.append(content)
                print(f"    ✅ Extracted {content['paragraph_count']:,} paragraphs")
                
                # Save progress after each file
                save_progress(documents, "extraction_progress.json")
            else:
                print(f"    ❌ Failed to extract content")
        else:
            print(f"    ❌ Conversion failed")
        
        print(f"    📈 Progress: {len(documents)}/{total_files} files completed")
    
    # Process existing .docx files
    print(f"\n📄 Processing existing .docx files...")
    for docx_file in sorted(docx_files):
        # Skip if already processed
        if is_already_processed(docx_file.name, documents):
            print(f"\n[SKIP] {docx_file.name} - already processed")
            continue
            
        print(f"\n[{len(documents) + 1}/{total_files}] Processing: {docx_file.name}")
        
        content = extract_docx_content(docx_file)
        if content:
            content['extraction_method'] = 'python-docx (direct)'
            documents.append(content)
            print(f"    ✅ Extracted {content['paragraph_count']:,} paragraphs")
            
            # Save progress
            save_progress(documents, "extraction_progress.json")
        else:
            print(f"    ❌ Extraction failed")
        
        print(f"    📈 Progress: {len(documents)}/{total_files} files completed")
    
    # Final results
    if documents:
        # Save final results
        final_output = "burra_news_complete_extraction.json"
        with open(final_output, 'w', encoding='utf-8') as f:
            json.dump(documents, f, indent=2, ensure_ascii=False)
        
        print(f"\n🎉 EXTRACTION COMPLETE!")
        print(f"=" * 50)
        print(f"📊 Final Summary:")
        print(f"   • Documents processed: {len(documents)}")
        print(f"   • Total paragraphs: {sum(doc['paragraph_count'] for doc in documents):,}")
        print(f"   • Total characters: {sum(doc.get('total_characters', 0) for doc in documents):,}")
        print(f"   • Output file: {final_output}")
        
        # Show breakdown by file
        print(f"\n📋 Processed files:")
        for doc in documents:
            method = doc.get('extraction_method', 'unknown')
            chars = doc.get('total_characters', 0)
            print(f"   • {doc['file_name']}: {doc['paragraph_count']:,} paragraphs ({chars:,} chars)")
        
        # Clean up temp files
        if temp_folder.exists():
            print(f"\n🧹 Cleaning up temporary files...")
            shutil.rmtree(temp_folder)
        
        print(f"\n✨ Ready for static site generation!")
    
    else:
        print("❌ No documents were processed successfully")

if __name__ == "__main__":
    main()