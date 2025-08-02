#!/usr/bin/env python3
"""
Convert .doc files to .docx using LibreOffice command line
Then extract with python-docx
"""

import os
import sys
import subprocess
from pathlib import Path
import json
from typing import Dict, List, Any
import shutil

def check_libreoffice():
    """Check if LibreOffice is available"""
    paths = [
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        "soffice",  # If in PATH
        "libreoffice"  # Alternative name
    ]
    
    for path in paths:
        if shutil.which(path) or Path(path).exists():
            print(f"✓ Found LibreOffice at: {path}")
            return path
    
    print("✗ LibreOffice not found")
    return None

def convert_doc_to_docx(doc_file: Path, output_dir: Path, soffice_path: str) -> Path:
    """Convert .doc file to .docx using LibreOffice"""
    try:
        # Ensure output directory exists
        output_dir.mkdir(exist_ok=True)
        
        # Run LibreOffice conversion
        cmd = [
            soffice_path,
            '--headless',
            '--convert-to', 'docx',
            '--outdir', str(output_dir),
            str(doc_file)
        ]
        
        print(f"  Converting {doc_file.name} to .docx...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            # Find the converted file
            converted_file = output_dir / f"{doc_file.stem}.docx"
            if converted_file.exists():
                print(f"    ✓ Converted to {converted_file.name}")
                return converted_file
            else:
                print(f"    ✗ Conversion output not found")
                return None
        else:
            print(f"    ✗ Conversion failed: {result.stderr}")
            return None
            
    except subprocess.TimeoutExpired:
        print(f"    ✗ Conversion timed out")
        return None
    except Exception as e:
        print(f"    ✗ Conversion error: {e}")
        return None

def extract_docx_content(file_path: Path) -> Dict[str, Any]:
    """Extract content from .docx files using python-docx"""
    try:
        from docx import Document
        
        doc = Document(file_path)
        
        paragraphs = []
        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                paragraphs.append({
                    'text': text,
                    'style': para.style.name if para.style else 'Normal'
                })
        
        return {
            'file_name': file_path.name,
            'original_file': file_path.name.replace('.docx', '.doc'),
            'file_type': 'doc (converted)',
            'extraction_method': 'LibreOffice + python-docx',
            'paragraphs': paragraphs,
            'paragraph_count': len(paragraphs),
        }
        
    except Exception as e:
        print(f"  ✗ Extraction failed: {e}")
        return None

def main():
    """Main conversion and extraction process"""
    print("LibreOffice Document Converter & Extractor")
    print("=" * 45)
    
    # Check if LibreOffice is available
    soffice_path = check_libreoffice()
    if not soffice_path:
        print("\n❌ LibreOffice is required for this approach")
        print("   Please install LibreOffice or use an alternative method")
        return
    
    source_folder = Path("Burra in the News")
    temp_folder = Path("temp_converted")
    
    if not source_folder.exists():
        print(f"❌ Source folder '{source_folder}' not found")
        return
    
    # Get all .doc files (excluding .docx)
    doc_files = [f for f in source_folder.glob("*.doc") if f.suffix.lower() == '.doc']
    
    print(f"\nFound {len(doc_files)} .doc files to convert...")
    
    documents = []
    converted_files = []
    
    for doc_file in sorted(doc_files):
        print(f"\nProcessing: {doc_file.name}")
        
        # Convert to .docx
        converted_file = convert_doc_to_docx(doc_file, temp_folder, soffice_path)
        
        if converted_file:
            converted_files.append(converted_file)
            
            # Extract content
            content = extract_docx_content(converted_file)
            if content:
                documents.append(content)
                print(f"    ✓ Extracted {content['paragraph_count']} paragraphs")
            else:
                print(f"    ✗ Failed to extract content")
    
    # Also process existing .docx files
    docx_files = list(source_folder.glob("*.docx"))
    for docx_file in docx_files:
        print(f"\nProcessing existing .docx: {docx_file.name}")
        content = extract_docx_content(docx_file)
        if content:
            content['extraction_method'] = 'python-docx (direct)'
            documents.append(content)
            print(f"    ✓ Extracted {content['paragraph_count']} paragraphs")
    
    if documents:
        # Save extracted data
        output_file = "libreoffice_extracted_content.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(documents, f, indent=2, ensure_ascii=False)
        
        print(f"\n📊 Extraction Summary:")
        print(f"   Documents processed: {len(documents)}")
        
        total_paragraphs = sum(doc['paragraph_count'] for doc in documents)
        print(f"   Total paragraphs: {total_paragraphs:,}")
        
        print(f"\n✓ Saved extracted content to {output_file}")
        
        # Clean up converted files
        if temp_folder.exists():
            print(f"\nCleaning up temporary files...")
            shutil.rmtree(temp_folder)
    
    else:
        print("❌ No documents were successfully processed.")

if __name__ == "__main__":
    main()