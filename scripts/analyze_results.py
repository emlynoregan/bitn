#!/usr/bin/env python3
"""
Analyze the final extraction results
"""

import json
from pathlib import Path

def analyze_extraction():
    """Analyze the complete extraction results"""
    
    # Try multiple result files
    files_to_try = [
        "burra_news_complete_extraction.json",
        "extraction_progress.json"
    ]
    
    data = None
    results_file = None
    
    for file_path in files_to_try:
        if Path(file_path).exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                results_file = file_path
                print(f"✅ Loaded data from: {file_path}")
                break
            except json.JSONDecodeError as e:
                print(f"⚠️  JSON error in {file_path}: {e}")
                continue
    
    if not data:
        print("❌ No valid results file found")
        return
    
    print("🎉 BURRA IN THE NEWS - EXTRACTION COMPLETE!")
    print("=" * 60)
    
    # Overall statistics
    total_docs = len(data)
    total_paragraphs = sum(doc.get('paragraph_count', 0) for doc in data)
    total_characters = sum(doc.get('total_characters', 0) for doc in data)
        
        print(f"📊 SUMMARY:")
        print(f"   • Documents processed: {total_docs}")
        print(f"   • Total paragraphs: {total_paragraphs:,}")
        print(f"   • Total characters: {total_characters:,}")
        print(f"   • Average per document: {total_paragraphs // total_docs:,} paragraphs")
        
        # File breakdown
        print(f"\n📋 BY PUBLICATION:")
        for doc in sorted(data, key=lambda x: x['file_name']):
            file_name = doc['file_name']
            paragraphs = doc.get('paragraph_count', 0)
            characters = doc.get('total_characters', 0)
            method = doc.get('extraction_method', 'unknown')
            
            print(f"   • {file_name}")
            print(f"     - {paragraphs:,} paragraphs ({characters:,} characters)")
            print(f"     - Method: {method}")
        
        # Time period analysis (based on filenames)
        print(f"\n📅 BY TIME PERIOD:")
        
        # Group by publication type
        sa_register = [d for d in data if 'SA Register' in d['file_name']]
        record_files = [d for d in data if 'Record' in d['file_name'] and 'SA Register' not in d['file_name']]
        broadcaster_files = [d for d in data if 'Broadcaster' in d['file_name']]
        argus_files = [d for d in data if 'Argus' in d['file_name']]
        other_files = [d for d in data if d not in sa_register + record_files + broadcaster_files + argus_files]
        
        if sa_register:
            paragraphs = sum(d.get('paragraph_count', 0) for d in sa_register)
            print(f"   • SA Register (1845-76): {paragraphs:,} paragraphs")
        
        if record_files:
            paragraphs = sum(d.get('paragraph_count', 0) for d in record_files)
            print(f"   • Record series (1876-1977): {paragraphs:,} paragraphs")
        
        if broadcaster_files:
            paragraphs = sum(d.get('paragraph_count', 0) for d in broadcaster_files)
            print(f"   • Broadcaster series (1991-2016): {paragraphs:,} paragraphs")
        
        if argus_files:
            paragraphs = sum(d.get('paragraph_count', 0) for d in argus_files)
            print(f"   • Northern Argus (1985-87): {paragraphs:,} paragraphs")
        
        if other_files:
            paragraphs = sum(d.get('paragraph_count', 0) for d in other_files)
            print(f"   • Other publications: {paragraphs:,} paragraphs")
        
        print(f"\n✨ READY FOR STATIC SITE GENERATION!")
        print(f"   File: {results_file} ({Path(results_file).stat().st_size / 1024 / 1024:.1f} MB)")
        
        # Compare with Eric's Research metadata
        print(f"\n🔍 COMPARISON WITH METADATA:")
        print(f"   Eric's Research predicted: 9,168 items")
        print(f"   We extracted: {total_paragraphs:,} paragraphs")
        print(f"   Ratio: {total_paragraphs / 9168:.1f}x (paragraphs per item)")
        
    except Exception as e:
        print(f"❌ Error analyzing results: {e}")

if __name__ == "__main__":
    analyze_extraction()