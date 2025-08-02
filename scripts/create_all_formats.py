#!/usr/bin/env python3
"""
Create both .docx and .md versions of all documents
"""

import subprocess
import json
from pathlib import Path
import shutil

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

def recreate_docx_files():
    """Recreate all .docx files from the original .doc files"""
    
    print("🔄 Recreating .docx files...")
    
    soffice_path = find_libreoffice()
    if not soffice_path:
        print("❌ LibreOffice not found")
        return False
    
    source_folder = Path("Burra in the News")
    docx_folder = Path("converted_docx")
    docx_folder.mkdir(exist_ok=True)
    
    # Get all .doc files
    doc_files = [f for f in source_folder.glob("*.doc")]
    
    print(f"📄 Converting {len(doc_files)} .doc files to .docx...")
    
    for i, doc_file in enumerate(sorted(doc_files), 1):
        print(f"  [{i:2d}/{len(doc_files)}] {doc_file.name}")
        
        try:
            cmd = [
                soffice_path,
                '--headless',
                '--convert-to', 'docx',
                '--outdir', str(docx_folder),
                str(doc_file)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                converted_file = docx_folder / f"{doc_file.stem}.docx"
                if converted_file.exists():
                    size_mb = converted_file.stat().st_size / 1024 / 1024
                    print(f"      ✅ Created ({size_mb:.1f} MB)")
                else:
                    print(f"      ❌ Failed - output not found")
            else:
                print(f"      ❌ Conversion error")
                
        except subprocess.TimeoutExpired:
            print(f"      ❌ Timeout")
        except Exception as e:
            print(f"      ❌ Error: {e}")
    
    # Copy the original .docx file too
    original_docx = source_folder / "Eric_s Research - pages notes.docx"
    if original_docx.exists():
        shutil.copy2(original_docx, docx_folder)
        print(f"  📋 Copied original: {original_docx.name}")
    
    converted_count = len(list(docx_folder.glob("*.docx")))
    print(f"\n✅ Created {converted_count} .docx files in {docx_folder}/")
    
    return True

def create_markdown_files():
    """Create .md files from the extracted JSON content"""
    
    print("\n📝 Creating Markdown files...")
    
    # Load the extraction data
    try:
        with open("burra_news_complete_extraction.json", 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Failed to load extraction data: {e}")
        return False
    
    md_folder = Path("markdown_files")
    md_folder.mkdir(exist_ok=True)
    
    print(f"📄 Creating {len(data)} markdown files...")
    
    for i, doc in enumerate(data, 1):
        file_name = doc.get('file_name', f'document_{i}')
        
        # Clean filename for filesystem
        safe_name = file_name.replace('.doc', '').replace('.docx', '')
        safe_name = "".join(c for c in safe_name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_name = safe_name.replace(' ', '_')
        
        md_file = md_folder / f"{safe_name}.md"
        
        print(f"  [{i:2d}/{len(data)}] {file_name} → {md_file.name}")
        
        try:
            with open(md_file, 'w', encoding='utf-8') as f:
                # Write header
                f.write(f"# {file_name}\n\n")
                
                # Metadata
                f.write(f"**Source:** {file_name}\n")
                f.write(f"**Type:** {doc.get('file_type', 'unknown')}\n")
                f.write(f"**Extraction Method:** {doc.get('extraction_method', 'unknown')}\n")
                f.write(f"**Paragraphs:** {doc.get('paragraph_count', 0):,}\n")
                f.write(f"**Characters:** {doc.get('total_characters', 0):,}\n\n")
                
                f.write("---\n\n")
                
                # Content
                paragraphs = doc.get('paragraphs', [])
                for j, para in enumerate(paragraphs):
                    text = para.get('text', '').strip()
                    if text:
                        # Add paragraph breaks for readability
                        f.write(f"{text}\n\n")
            
            print(f"      ✅ Created ({md_file.stat().st_size / 1024:.1f} KB)")
            
        except Exception as e:
            print(f"      ❌ Error: {e}")
    
    md_count = len(list(md_folder.glob("*.md")))
    print(f"\n✅ Created {md_count} markdown files in {md_folder}/")
    
    return True

def main():
    """Create both .docx and .md versions"""
    
    print("📚 CREATING ALL DOCUMENT FORMATS")
    print("=" * 50)
    
    # Recreate .docx files
    docx_success = recreate_docx_files()
    
    # Create markdown files
    md_success = create_markdown_files()
    
    # Summary
    print(f"\n🎉 SUMMARY:")
    print(f"   • .docx files: {'✅ Created' if docx_success else '❌ Failed'}")
    print(f"   • .md files: {'✅ Created' if md_success else '❌ Failed'}")
    
    if docx_success and md_success:
        print(f"\n📂 Your files are now available in:")
        print(f"   • converted_docx/ - All .docx versions")
        print(f"   • markdown_files/ - All .md versions")
        print(f"   • burra_news_complete_extraction.json - Raw extracted data")
        
        print(f"\n✨ All formats preserved! No more accidental deletions!")

if __name__ == "__main__":
    main()