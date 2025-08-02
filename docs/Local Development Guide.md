# Local Development Guide - Burra in the News

## Installing Hugo on Windows

### Option 1: Winget (Recommended)
```powershell
# Install Hugo using Windows Package Manager
winget install Hugo.Hugo.Extended
```

### Option 2: Chocolatey
```powershell
# If you have Chocolatey installed
choco install hugo-extended
```

### Option 3: Manual Installation
1. Go to [Hugo Releases](https://github.com/gohugoio/hugo/releases)
2. Download `hugo_extended_0.121.0_windows-amd64.zip`
3. Extract to `C:\Hugo\bin\`
4. Add `C:\Hugo\bin\` to your PATH environment variable

### Option 4: Scoop
```powershell
# If you have Scoop installed
scoop install hugo-extended
```

## Running the Site Locally

### 1. Navigate to Site Directory
```powershell
cd C:\Users\emlyn\Documents\bhg\bitn\site
```

### 2. Start Hugo Development Server
```powershell
hugo serve
```

### 3. View Your Site
- Open browser to: `http://localhost:1313`
- Site will auto-reload when you make changes
- Press `Ctrl+C` to stop the server

## Local Development Workflow

### Basic Commands
```powershell
# Start development server
hugo serve

# Start with drafts visible
hugo serve -D

# Start on different port
hugo serve -p 8080

# Build site for production
hugo

# Build with minification
hugo --minify
```

### File Structure for Development
```
site/
├── config.yaml          # Site configuration
├── content/              # Your content files
│   ├── _index.md        # Home page
│   ├── about/           # About section
│   ├── publications/    # Publications content
│   └── search/          # Search page
├── themes/              # Your custom theme
├── static/              # Static assets (CSS, JS)
└── public/              # Generated site (after hugo build)
```

## Development Tips

### 1. Live Reload
Hugo automatically rebuilds and refreshes your browser when you:
- Modify content files
- Update templates
- Change configuration
- Edit static assets

### 2. Draft Content
To work on content without publishing:
```yaml
---
title: "My Draft Post"
draft: true
---
```

### 3. Future Content
Content with future dates won't show unless:
```powershell
hugo serve -F  # Show future content
```

### 4. Performance
For faster builds during development:
```powershell
hugo serve --disableFastRender=false
```

## Troubleshooting

### Hugo Not Found
```powershell
# Check if Hugo is installed
hugo version

# If not found, add to PATH or reinstall
```

### Port Already in Use
```powershell
# Use different port
hugo serve -p 8080
```

### Build Errors
```powershell
# Verbose output for debugging
hugo serve --verbose

# Check for template errors
hugo serve --debug
```

### Theme Issues
```powershell
# Verify theme is properly linked
ls themes/burra-archive/

# Check config.yaml theme setting
cat config.yaml | findstr theme
```

## Content Development

### Adding New Content
```powershell
# Create new page
hugo new about/history.md

# Create new publication
hugo new publications/new-paper/_index.md
```

### Testing Search
1. Ensure `search-data.json` exists in `static/js/`
2. Check browser developer console for JavaScript errors
3. Test search functionality at `/search/`

### Checking Generated Content
```powershell
# Build site to see final output
hugo

# Check public directory
ls public/
```

## GitHub Integration

### Testing Before Push
```powershell
# Build exactly like GitHub Actions will
hugo --gc --minify

# Check for any build warnings or errors
```

### Local vs Production
- **Local**: `http://localhost:1313`
- **Production**: `https://[username].github.io/bitn/`

Make sure to test both environments for:
- Asset loading
- Link functionality  
- Search performance
- Mobile responsiveness

## Performance Monitoring

### Build Speed
```powershell
# Time the build process
Measure-Command { hugo }
```

### Site Size
```powershell
# Check generated site size
Get-ChildItem -Path public -Recurse | Measure-Object -Property Length -Sum
```

### Search Index Size
```powershell
# Check search data size
Get-Item static/js/search-data.json | Select-Object Length
```

## Next Steps After Local Testing

1. **Test thoroughly** on `localhost:1313`
2. **Verify all links** work correctly
3. **Test search functionality** 
4. **Check mobile responsiveness**
5. **Push to GitHub** for automatic deployment
6. **Verify live site** matches local version

## Quick Start Commands

```powershell
# Install Hugo (pick one method above)
winget install Hugo.Hugo.Extended

# Navigate to site
cd C:\Users\emlyn\Documents\bhg\bitn\site

# Start local server
hugo serve

# Open browser to http://localhost:1313
```

Your local development environment will give you immediate feedback and allow you to iterate quickly before deploying to GitHub Pages!