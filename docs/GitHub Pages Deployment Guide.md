# GitHub Pages Deployment Guide - Burra in the News

## Why GitHub Pages is Perfect for This Project

### ✅ **Ideal Match**
- **Static site hosting** - exactly what Hugo generates
- **Free hosting** for public repositories
- **Custom domain** support (yoursite.com)
- **HTTPS included** automatically
- **Global CDN** for fast worldwide access
- **Version control integration** - deploy directly from Git
- **Open source friendly** - great for historical archives

### ✅ **Advantages Over Other Platforms**
- **No build time limits** for this size project
- **Integrated with your code** - everything in one place
- **Community visibility** - discoverable on GitHub
- **Academic credibility** - researchers trust GitHub
- **Long-term stability** - backed by Microsoft

## 🔧 Technical Implementation

### Hugo + GitHub Actions Setup

GitHub Pages doesn't natively support Hugo (it only supports Jekyll), but we can use **GitHub Actions** to build Hugo and deploy automatically.

#### 1. Repository Structure
```
bitn/
├── .github/
│   └── workflows/
│       └── hugo.yml          # Auto-build and deploy
├── site/                     # Hugo source files
│   ├── config.yaml
│   ├── content/
│   ├── layouts/
│   └── static/
├── archive/                  # Your existing content
├── scripts/                  # Content processing
└── docs/                     # Documentation
```

#### 2. GitHub Actions Workflow

**`.github/workflows/hugo.yml`**
```yaml
name: Deploy Hugo site to Pages

on:
  # Run on pushes to main branch
  push:
    branches: ["main"]
  
  # Allow manual trigger
  workflow_dispatch:

# Sets permissions for GitHub Pages
permissions:
  contents: read
  pages: write
  id-token: write

# Allow only one concurrent deployment
concurrency:
  group: "pages"
  cancel-in-progress: false

# Default to bash
defaults:
  run:
    shell: bash

jobs:
  # Build job
  build:
    runs-on: ubuntu-latest
    env:
      HUGO_VERSION: 0.120.0
    steps:
      - name: Install Hugo CLI
        run: |
          wget -O ${{ runner.temp }}/hugo.deb https://github.com/gohugoio/hugo/releases/download/v${HUGO_VERSION}/hugo_extended_${HUGO_VERSION}_linux-amd64.deb \
          && sudo dpkg -i ${{ runner.temp }}/hugo.deb          
      
      - name: Install Dart Sass
        run: sudo snap install dart-sass
      
      - name: Checkout
        uses: actions/checkout@v4
        with:
          submodules: recursive
      
      - name: Setup Pages
        id: pages
        uses: actions/configure-pages@v4
      
      - name: Install Node.js dependencies
        run: "[[ -f package-lock.json || -f npm-shrinkwrap.json ]] && npm ci || true"
        working-directory: ./site
      
      - name: Build with Hugo
        env:
          # For maximum backward compatibility with Hugo modules
          HUGO_ENVIRONMENT: production
          HUGO_ENV: production
        run: |
          hugo \
            --gc \
            --minify \
            --baseURL "${{ steps.pages.outputs.base_url }}/"
        working-directory: ./site
      
      - name: Upload artifact
        uses: actions/upload-pages-artifact@v2
        with:
          path: ./site/public

  # Deployment job
  deploy:
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    runs-on: ubuntu-latest
    needs: build
    steps:
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v3
```

#### 3. Content Processing Integration

**Enhanced `scripts/hugo_content_processor.py`**
```python
#!/usr/bin/env python3
"""
Process JSON archive into Hugo-compatible content
Optimized for GitHub Pages deployment
"""

import json
import os
from pathlib import Path
import re
from datetime import datetime

def process_for_github_pages():
    """Convert archive to Hugo format for GitHub Pages"""
    
    # Load the complete extraction
    with open('burra_news_complete_extraction.json', 'r', encoding='utf-8') as f:
        archive_data = json.load(f)
    
    # Create Hugo site structure
    site_dir = Path('site')
    content_dir = site_dir / 'content'
    
    # Process each publication
    for doc in archive_data:
        create_hugo_content(doc, content_dir)
    
    # Generate search index
    create_search_index(archive_data, site_dir / 'static' / 'js')
    
    print(f"✅ Processed {len(archive_data)} documents for GitHub Pages")

def create_hugo_content(doc, content_dir):
    """Create Hugo markdown file from document"""
    
    # Extract metadata
    file_name = doc.get('file_name', '')
    publication = extract_publication_name(file_name)
    date = extract_date(file_name)
    
    # Create directory structure
    pub_dir = content_dir / 'publications' / publication
    pub_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate markdown file
    md_content = f"""---
title: "{file_name}"
date: {date}
publication: "{publication}"
type: "article"
paragraph_count: {doc.get('paragraph_count', 0)}
extraction_method: "{doc.get('extraction_method', '')}"
---

"""
    
    # Add content paragraphs
    for para in doc.get('paragraphs', []):
        md_content += f"{para.get('text', '')}\n\n"
    
    # Save file
    safe_filename = re.sub(r'[^\w\-_.]', '_', file_name) + '.md'
    with open(pub_dir / safe_filename, 'w', encoding='utf-8') as f:
        f.write(md_content)

# Additional helper functions...
```

## 🚀 Deployment Process

### Setup Steps

#### 1. **Enable GitHub Pages**
```bash
# In your GitHub repository settings:
# 1. Go to Settings > Pages
# 2. Source: GitHub Actions
# 3. That's it! No branch selection needed
```

#### 2. **Repository Configuration**
- **Repository**: Make `bitn` repository public (required for free GitHub Pages)
- **Branch**: Deploy from `main` branch
- **Custom Domain**: Optional (yourarchive.com)

#### 3. **Automatic Deployment**
```bash
# Every time you push to main branch:
git add .
git commit -m "Update content"
git push origin main

# GitHub Actions automatically:
# 1. Runs Hugo build
# 2. Generates static site
# 3. Deploys to yoursite.github.io
```

### URL Structure

**Default GitHub Pages URL:**
`https://[your-username].github.io/bitn/`

**Custom Domain (Optional):**
`https://burranews.org/` (or your chosen domain)

## 📊 Performance Comparison

### GitHub Pages vs Netlify

| Feature | GitHub Pages | Netlify |
|---------|-------------|---------|
| **Cost** | Free (public repos) | Free tier available |
| **Build Time** | ~2-3 minutes | ~1-2 minutes |
| **Global CDN** | ✅ Yes | ✅ Yes |
| **HTTPS** | ✅ Automatic | ✅ Automatic |
| **Custom Domain** | ✅ Yes | ✅ Yes |
| **Form Handling** | ❌ No | ✅ Yes |
| **Redirects** | Limited | Full featured |
| **Hugo Support** | Via Actions | Native |
| **Repository Integration** | ✅ Perfect | Good |

**Verdict for Your Project**: **GitHub Pages is ideal** because:
- Historical archive doesn't need forms or advanced features
- Perfect integration with your existing repository
- Academic/research credibility
- Long-term stability and free hosting

## 🛡️ Advantages for Historical Archives

### **Academic Credibility**
- **Researchers trust GitHub** for scholarly projects
- **Open source accessibility** encourages collaboration
- **Version control transparency** shows development process
- **Citable URLs** with permanent links

### **Long-term Preservation**
- **Microsoft backing** provides stability
- **No vendor lock-in** - standard Git repository
- **Community visibility** helps ensure preservation
- **Fork-friendly** for institutional copies

### **Technical Benefits**
- **Zero configuration** once set up
- **Automatic HTTPS** and security
- **Global CDN** for worldwide access
- **No server maintenance** required

## 🔧 Updated Phase 1 Timeline

### Week 1: Foundation (Updated for GitHub Pages)
- **Day 1**: Repository setup + GitHub Pages configuration
- **Day 2**: Hugo site initialization in `/site` folder
- **Day 3-4**: Content processing pipeline (JSON → Hugo)
- **Day 5-7**: Basic templates and GitHub Actions workflow

### Week 2: Development 
- **Day 8-10**: Search implementation
- **Day 11-12**: Responsive design
- **Day 13-14**: Content organization

### Week 3: Deployment
- **Day 15-17**: Testing and optimization
- **Day 18-19**: GitHub Actions refinement
- **Day 20-21**: Live deployment and final testing

## 📋 GitHub Pages Checklist

### Repository Setup
- [ ] Repository is public (required for free GitHub Pages)
- [ ] GitHub Pages enabled in repository settings
- [ ] Source set to "GitHub Actions"

### Hugo Configuration
- [ ] Hugo site created in `/site` folder
- [ ] `config.yaml` configured for GitHub Pages
- [ ] Base URL set correctly for your domain

### GitHub Actions
- [ ] `.github/workflows/hugo.yml` created
- [ ] Workflow permissions configured
- [ ] Test deployment successful

### Content Processing
- [ ] JSON → Hugo conversion working
- [ ] Search index generation included
- [ ] All publications processed correctly

### Final Deployment
- [ ] Site accessible at GitHub Pages URL
- [ ] All content displays correctly
- [ ] Search functionality working
- [ ] Mobile responsiveness verified

## 🎯 Final Recommendation

**GitHub Pages is the perfect choice** for the Burra in the News archive because:

1. **🆓 Completely free** for public repositories
2. **🏛️ Academic credibility** - researchers trust GitHub
3. **🔗 Perfect integration** with your existing repository structure
4. **🚀 Automatic deployment** - push code, site updates automatically
5. **🌍 Global performance** with GitHub's CDN
6. **📚 Ideal for historical archives** - no need for advanced features

**This approach maintains the scholarly integrity of Eric Fuss's work while leveraging GitHub's excellent infrastructure for long-term preservation and global access.**