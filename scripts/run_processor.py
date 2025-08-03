#!/usr/bin/env python3
"""
Simple launcher for Northern Argus processor with setup checks
"""

import os
import sys
import json
from pathlib import Path

def check_setup():
    """Check if everything is set up correctly"""
    print("🔍 Checking setup...")
    
    # Check if we're in the right directory
    if not Path("archive/markdown/1985-87_Northern__Argus.md").exists():
        print("❌ ERROR: Northern Argus document not found!")
        print("   Make sure you're running this from the bitn project root.")
        return False
    
    # Check if instructions exist
    if not Path("docs/Northern Argus Instructions.md").exists():
        print("❌ ERROR: Northern Argus Instructions not found!")
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
    print("🚀 Northern Argus Document Processor Launcher")
    print("=" * 50)
    
    if not check_setup():
        print("\n❌ Setup check failed. Please fix the issues above.")
        sys.exit(1)
    
    print("\n🎯 Starting processing...")
    print("📋 This will:")
    print("   • Process the full Northern Argus document (3,331 lines)")
    print("   • Extract ~150-200 individual records")
    print("   • Cost approximately $2-5 in OpenAI API calls")
    print("   • Take 10-20 minutes to complete")
    
    # Ask for confirmation
    try:
        response = input("\n❓ Continue? [y/N]: ").strip().lower()
        if response not in ['y', 'yes']:
            print("🛑 Processing cancelled.")
            sys.exit(0)
    except KeyboardInterrupt:
        print("\n🛑 Processing cancelled.")
        sys.exit(0)
    
    # Import and run the main processor
    print("\n" + "=" * 50)
    try:
        from process_northern_argus import NorthernArgusProcessor
        
        processor = NorthernArgusProcessor()
        processor.process_document("archive/markdown/1985-87_Northern__Argus.md")
        
        print("\n🎉 Processing completed successfully!")
        print("📁 Check the 'processed/' folder for results.")
        
    except KeyboardInterrupt:
        print("\n🛑 Processing interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()