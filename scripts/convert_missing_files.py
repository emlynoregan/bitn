#!/usr/bin/env python3
"""
Convert specific missing files
"""

import subprocess
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

def convert_specific_files():
    """Convert the missing files specifically"""
    
    soffice_path = find_libreoffice()
    if not soffice_path:
        print("❌ LibreOffice not found")
        return
    
    print(f"✅ Found LibreOffice: {soffice_path}")
    
    # Missing files to convert
    missing_files = [
        "1845-76 SA Register.doc",
        "1876-79 Record .doc"
    ]
    
    source_folder = Path("Burra in the News")
    temp_folder = Path("temp_converted")
    temp_folder.mkdir(exist_ok=True)
    
    print(f"\n🔄 Converting missing files...")
    
    for file_name in missing_files:
        doc_file = source_folder / file_name
        
        if not doc_file.exists():
            print(f"❌ File not found: {file_name}")
            continue
            
        print(f"\n📄 Converting: {file_name}")
        
        try:
            cmd = [
                soffice_path,
                '--headless',
                '--convert-to', 'docx',
                '--outdir', str(temp_folder),
                str(doc_file)
            ]
            
            print(f"    Running conversion...")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            
            if result.returncode == 0:
                converted_file = temp_folder / f"{doc_file.stem}.docx"
                if converted_file.exists():
                    size_mb = converted_file.stat().st_size / 1024 / 1024
                    print(f"    ✅ SUCCESS! Created {converted_file.name} ({size_mb:.1f} MB)")
                else:
                    print(f"    ❌ Conversion failed - output file not found")
            else:
                print(f"    ❌ Conversion failed: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            print(f"    ❌ Conversion timed out (>3 minutes)")
        except Exception as e:
            print(f"    ❌ Error: {e}")
    
    # Check final count
    converted_files = list(temp_folder.glob("*.docx"))
    print(f"\n📊 Conversion Summary:")
    print(f"   • Files in temp_converted: {len(converted_files)}")
    print(f"   • Expected: 13 (.doc conversions)")
    
    if len(converted_files) == 13:
        print(f"   ✅ ALL FILES CONVERTED!")
    else:
        print(f"   ⚠️  Still missing {13 - len(converted_files)} files")

if __name__ == "__main__":
    convert_specific_files()