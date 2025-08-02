#!/usr/bin/env python3
"""
Show extraction results summary
"""

import json
from pathlib import Path

def main():
    # Try to load results
    files = ["extraction_progress.json", "burra_news_complete_extraction.json"]
    
    data = None
    for file_path in files:
        if Path(file_path).exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                print(f"✅ Loaded from: {file_path}")
                break
            except:
                print(f"❌ Error reading: {file_path}")
                continue
    
    if not data:
        print("❌ No valid results found")
        return
    
    print("\n🎉 BURRA IN THE NEWS - EXTRACTION COMPLETE!")
    print("=" * 60)
    
    # Basic stats
    total_docs = len(data)
    total_paragraphs = sum(doc.get('paragraph_count', 0) for doc in data)
    total_chars = sum(doc.get('total_characters', 0) for doc in data)
    
    print(f"📊 SUMMARY:")
    print(f"   • Documents: {total_docs}")
    print(f"   • Paragraphs: {total_paragraphs:,}")
    print(f"   • Characters: {total_chars:,}")
    
    print(f"\n📋 FILES PROCESSED:")
    for doc in sorted(data, key=lambda x: x.get('file_name', '')):
        name = doc.get('file_name', 'Unknown')
        paras = doc.get('paragraph_count', 0)
        chars = doc.get('total_characters', 0)
        print(f"   • {name}: {paras:,} paragraphs ({chars:,} chars)")
    
    print(f"\n✨ SUCCESS! Ready for static site generation!")

if __name__ == "__main__":
    main()