#!/usr/bin/env python3
"""
Universal Document Extractor using textract
Handles both .doc and .docx files
"""

import os
import sys
import subprocess
from pathlib import Path
import json
from typing import Dict, List, Any

def install_textract():
    """Install textract if not available"""
    try:
        import textract
        print("✓ textract already available")
        return True
    except ImportError:
        print("Installing textract...")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'textract'])
            import textract
            print("✓ textract installed successfully")
            return True
        except Exception as e:
            print(f"✗ Failed to install textract: {e}")
            return False

def extract_with_textract(file_path: Path) -> Dict[str, Any]:
    """Extract text using textract (universal extractor)"""
    try:
        import textract
        
        print(f"  Processing {file_path.name} with textract...")
        text = textract.process(str(file_path)).decode('utf-8')
        
        # Split into paragraphs
        paragraphs = []
        for line in text.split('\n'):
            line = line.strip()
            if line and len(line) > 3:  # Filter out very short lines
                paragraphs.append({
                    'text': line,
                    'style': 'Normal'
                })
        
        return {
            'file_name': file_path.name,
            'file_type': file_path.suffix.lower(),
            'extraction_method': 'textract',
            'paragraphs': paragraphs,
            'paragraph_count': len(paragraphs),
            'raw_text_length': len(text)
        }
        
    except Exception as e:
        print(f"  ✗ Textract failed: {e}")
        return None

def fallback_docx_extraction(file_path: Path) -> Dict[str, Any]:
    """Fallback method for .docx files using python-docx"""
    try:
        from docx import Document
        
        print(f"  Processing {file_path.name} with python-docx...")
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
            'file_type': file_path.suffix.lower(),
            'extraction_method': 'python-docx',
            'paragraphs': paragraphs,
            'paragraph_count': len(paragraphs),
            'raw_text_length': sum(len(p['text']) for p in paragraphs)
        }
        
    except Exception as e:
        print(f"  ✗ python-docx failed: {e}")
        return None

def extract_all_documents_universal(source_folder: str = "Burra in the News") -> List[Dict[str, Any]]:
    """Extract content from all Word documents using multiple methods"""
    
    source_path = Path(source_folder)
    if not source_path.exists():
        print(f"Error: Folder '{source_folder}' not found")
        return []
    
    documents = []
    
    # Get all .doc and .docx files
    doc_files = list(source_path.glob("*.doc")) + list(source_path.glob("*.docx"))
    
    print(f"Found {len(doc_files)} Word documents to process...")
    
    for doc_file in sorted(doc_files):
        print(f"\nProcessing: {doc_file.name}")
        
        content = None
        
        # Try textract first (universal)
        content = extract_with_textract(doc_file)
        
        # If textract fails and it's a .docx file, try python-docx
        if not content and doc_file.suffix.lower() == '.docx':
            content = fallback_docx_extraction(doc_file)
        
        if content:
            documents.append(content)
            print(f"  ✓ Extracted {content['paragraph_count']} paragraphs ({content['raw_text_length']} chars)")
        else:
            print(f"  ✗ All extraction methods failed")
    
    return documents

def save_extracted_data(documents: List[Dict[str, Any]], output_file: str = "universal_extracted_content.json"):
    """Save extracted content to JSON file"""
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(documents, f, indent=2, ensure_ascii=False)
        print(f"\n✓ Saved extracted content to {output_file}")
        return True
    except Exception as e:
        print(f"Error saving to {output_file}: {str(e)}")
        return False

def main():
    """Main extraction process"""
    print("Burra in the News - Universal Document Extractor")
    print("=" * 50)
    
    # Install textract
    if not install_textract():
        print("❌ Cannot proceed without textract")
        return
    
    # Extract documents
    print("\nExtracting document content...")
    documents = extract_all_documents_universal()
    
    if documents:
        # Save extracted data
        save_extracted_data(documents)
        
        # Print summary
        print(f"\n📊 Extraction Summary:")
        print(f"   Documents processed: {len(documents)}")
        
        total_paragraphs = sum(doc['paragraph_count'] for doc in documents)
        total_chars = sum(doc['raw_text_length'] for doc in documents)
        print(f"   Total paragraphs: {total_paragraphs:,}")
        print(f"   Total characters: {total_chars:,}")
        
        # Show file breakdown
        print(f"\n📄 Successfully processed files:")
        for doc in documents:
            method = doc.get('extraction_method', 'unknown')
            print(f"   • {doc['file_name']}: {doc['paragraph_count']:,} paragraphs ({method})")
    
    else:
        print("❌ No documents were successfully processed.")

if __name__ == "__main__":
    main()