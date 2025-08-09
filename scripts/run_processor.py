#!/usr/bin/env python3
"""
Simple launcher for generic archive processor with setup checks
"""

import os
import sys
import json
from pathlib import Path

def check_setup():
    """Check if everything is set up correctly"""
    print("🔍 Checking setup...")
    
    # Check that archive exists
    if not Path("archive/markdown").exists():
        print("❌ ERROR: archive/markdown folder not found!")
        return False
    
    # Check config file
    config_path = Path("scripts/config.json")
    if not config_path.exists():
        print("❌ ERROR: Config file not found at scripts/config.json")
        return False
    
    # Check API key
    try:
        with open(config_path) as f:
            config = json.load(f)
        
        if config.get("openai_api_key") == "your-openai-api-key-here":
            print("❌ ERROR: OpenAI API key not set!")
            print("   Edit scripts/config.json and add your API key.")
            return False
    except:
        print("❌ ERROR: Invalid config file")
        return False
    
    # Check OpenAI library
    try:
        import openai
        print("✅ OpenAI library installed")
    except ImportError:
        print("❌ ERROR: OpenAI library not installed")
        print("   Run: pip install openai")
        return False
    
    # Create processed directory
    os.makedirs("processed", exist_ok=True)
    print("✅ Output directory ready")
    
    print("✅ Setup check complete!")
    return True

def main():
    """Main launcher"""
    print("🚀 Archive Document Processor Launcher")
    print("=" * 50)

    if not check_setup():
        print("\n❌ Setup check failed. Please fix the issues above.")
        sys.exit(1)

    print("\n🎯 Starting processing...")
    # Import and run the processor
    print("\n" + "=" * 50)
    try:
        from process_archive import ArchiveDocumentProcessor

        processor = ArchiveDocumentProcessor()
        # Pick document from CLI if provided, otherwise use a default
        doc_path = sys.argv[1] if len(sys.argv) > 1 else "archive/markdown/1985-87_Northern__Argus.md"

        # Per-chunk mode with retries (default and only mode)
        print("ℹ️ Per-chunk mode with retries")
        processor.process_document_per_chunk(doc_path)

        print("\n🎉 Processing completed!")
        print("📁 Check the 'processed/' folder for results.")

    except KeyboardInterrupt:
        print("\n🛑 Processing interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()