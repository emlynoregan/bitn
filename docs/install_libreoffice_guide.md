# LibreOffice Installation Guide

## 🚀 Quick Installation Options

### Option 1: Direct Download (RECOMMENDED)
1. **Go to**: https://www.libreoffice.org/download/
2. **Download**: LibreOffice 25.2.5 for Windows
3. **Run the installer** and follow the prompts
4. **After installation**, run: `py convert_with_libreoffice.py`

### Option 2: Windows Package Manager
If the previous winget command didn't complete:
```bash
winget install --id=TheDocumentFoundation.LibreOffice --exact
```

### Option 3: Chocolatey (if installed)
```bash
choco install libreoffice
```

## 📋 Installation Steps
1. Download LibreOffice from the official site
2. Run the installer (may require admin privileges)
3. Complete the installation wizard
4. LibreOffice will be installed to: `C:\Program Files\LibreOffice\`

## 🔧 After Installation
Once LibreOffice is installed, run our conversion script:
```bash
py convert_with_libreoffice.py
```

This will:
- ✅ Convert all 13 .doc files to .docx format
- ✅ Extract content from all documents  
- ✅ Save everything to `libreoffice_extracted_content.json`
- ✅ Process all 9,168 historical news items!

## ⚡ Alternative: Manual Conversion
If you prefer not to install LibreOffice:
1. Open each .doc file in Microsoft Word
2. Save As → .docx format
3. Run: `py extract_documents.py`

## 🎯 Expected Results
After successful extraction, you'll have:
- **14 documents processed** (1 .docx + 13 converted .doc files)
- **Complete text content** from all 9,168 news items
- **Structured JSON data** ready for static site generation
- **Metadata** for building search and filter features

Ready to proceed once LibreOffice is installed! 🚀