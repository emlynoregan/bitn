# Burra in the News - Static Site Design Plan

## Target Audiences & Use Cases

### Primary Users
1. **Genealogists/Family Historians**
   - Need: Search by person names, dates, birth/death/marriage records
   - Behavior: Targeted searches, following family connections

2. **Local Historians & Researchers**
   - Need: Browse by time period, topic, publication source
   - Behavior: Deep reading, cross-referencing, timeline exploration

3. **Community Members**
   - Need: Discover family/property history, understand heritage
   - Behavior: Casual browsing, story discovery, sharing

4. **Academic Researchers**
   - Need: Comprehensive data access, citation tools, trend analysis
   - Behavior: Systematic research, data export, comparative studies

5. **Tourists & Heritage Visitors**
   - Need: Historical context, interesting stories, visual engagement
   - Behavior: Quick browsing, discovery, mobile access

## Site Architecture

### Homepage
**"Burra in the News: 170 Years of Community History"**
- Hero section with timeline visualization (1845-2016)
- Quick stats: "250,000+ entries • 9,168 historical items • 14 publications"
- Featured stories/discoveries
- Multiple entry points for different user types

### Core Navigation Structure

#### 1. **BROWSE BY TIME**
```
/timeline/
├── 1845-1876/ (Mining Boom Era)
├── 1876-1900/ (Early Settlement)
├── 1900-1920/ (Consolidation)
├── 1920-1940/ (Between Wars)
├── 1940-1960/ (Post-War Growth)
├── 1960-1980/ (Transition)
├── 1980-2000/ (Heritage Development)
└── 2000-2016/ (Modern Era)
```

#### 2. **BROWSE BY PUBLICATION**
```
/publications/
├── sa-register/ (1845-1876)
├── burra-record/ (1876-1977)
├── review-times/ (1977-1987)
├── northern-argus/ (1985-1987)
├── school-community-news/ (1978-1993)
├── burra-broadcaster/ (1991-2016)
└── mid-north-broadcaster/ (2006-2013)
```

#### 3. **SEARCH & DISCOVER**
```
/search/
├── people/ (Genealogical search)
├── places/ (Location-based)
├── topics/ (Subject categories)
└── advanced/ (Multi-field search)
```

#### 4. **RESEARCH TOOLS**
```
/research/
├── genealogy/ (Family history tools)
├── citations/ (Academic reference)
├── timeline/ (Interactive timeline)
└── analysis/ (Eric Fuss's methodology)
```

## Key Features & Functionality

### 1. **Powerful Search System**
- **Full-text search** across all content
- **People search** with genealogical connections
- **Date range filtering**
- **Publication filtering**
- **Advanced filters**: births, deaths, marriages, businesses, events

### 2. **Interactive Timeline**
- **Visual timeline** with major events
- **Zoom levels**: Decade → Year → Month → Day
- **Event clustering** for busy periods
- **Publication transitions** clearly marked

### 3. **People Directory**
- **Alphabetical index** of all mentioned people
- **Family connections** where identified by Eric
- **Birth/death dates** from verified records
- **Cross-references** between mentions

### 4. **Smart Content Organization**
- **Article classification**: News, Obituaries, Advertisements, Social Notes
- **Topic tagging**: Mining, Agriculture, Sports, Religion, Business
- **Importance flagging**: Major events vs routine notices

### 5. **Mobile-First Design**
- **Responsive layout** for phone/tablet browsing
- **Touch-friendly** navigation
- **Offline reading** capability for popular sections

## Technical Implementation

### Static Site Generator: **Hugo** (Recommended)
**Why Hugo:**
- Extremely fast build times (crucial for 30+ MB content)
- Excellent search integration
- Powerful content organization
- Great mobile performance

### Content Processing Pipeline
```
Raw Data → Content Parser → Hugo Content → Static Site
   ↓              ↓              ↓            ↓
JSON Files → Markdown Pages → HTML/CSS/JS → CDN Deploy
```

### Search Implementation: **Lunr.js**
- Client-side search (no server needed)
- Indexes all content at build time
- Fast, responsive search experience
- Works offline once loaded

### Content Structure Example
```markdown
---
title: "Northern Mail - 30 June 1876"
date: 1876-06-30
publication: "northern-mail"
volume: "I"
issue: "1"
pages: [1, 2, 3, 4]
content_types: ["editorial", "advertisements", "news"]
people: ["John D. Cave", "Thomas Richardson", "Romeo"]
places: ["Kooringa", "Aberdeen", "Market Square"]
topics: ["mining", "business", "social"]
---

## Advertisements, page 1

**John D. Cave** - Auctioneer & General Commission Agent, Farrell's Flat
[Editorial note: Birth date verified as...]
```

## Content Presentation Strategies

### 1. **Faithful Reproduction**
- Preserve Eric's **square bracket annotations**
- Maintain original **citation format**
- Keep **chronological structure** intact

### 2. **Enhanced Readability**
- **Typography** appropriate to era (serif for historical, sans-serif for modern)
- **Color coding** by publication/era
- **Expandable sections** for long entries

### 3. **Visual Enhancements**
- **Historical photographs** where available
- **Maps** showing location references
- **Publication mastheads** and historical context

### 4. **Smart Linking**
- **Auto-link** person names to their directory pages
- **Cross-reference** Eric's annotations
- **Related content** suggestions

## User Experience Flows

### Genealogist Journey
1. **Search person name** → Results list with dates
2. **Click specific mention** → Full article context
3. **See related people** → Follow family connections
4. **Export citations** → Academic format

### Historian Journey
1. **Browse time period** → Overview of era
2. **Filter by topic** → Mining/agriculture/social
3. **Read sequential issues** → Understand development
4. **Cross-reference** → Verify information

### Tourist Journey
1. **Discover interesting stories** → Featured content
2. **Learn about locations** → Map integration
3. **Share discoveries** → Social media friendly
4. **Plan visit** → Modern Burra connections

## Performance Considerations

### Content Volume Management
- **Lazy loading** for large documents
- **Progressive enhancement** for search features
- **CDN deployment** for global access
- **Compression** for text-heavy content

### Search Optimization
- **Indexed search** for instant results
- **Faceted filtering** for refinement
- **Autocomplete** for person/place names
- **Search suggestions** for common terms

## Future Enhancement Opportunities

### Phase 1: Basic Site
- Static content browsing
- Basic search functionality
- Mobile-responsive design

### Phase 2: Enhanced Features
- Advanced search with filters
- Interactive timeline
- People directory with connections

### Phase 3: Community Features
- User contributions (photos, stories)
- Community annotations
- Modern Burra connections

### Phase 4: Research Tools
- Data visualization
- Trend analysis
- Export capabilities
- API for researchers

## Success Metrics

### Engagement
- **Search usage** patterns
- **Content depth** (pages per session)
- **Return visits** (research continuity)

### Research Value
- **Citation usage** in academic work
- **Genealogical discoveries** reported
- **Community connections** made

### Heritage Impact
- **Tourism integration** with physical sites
- **Educational adoption** by schools
- **Media coverage** and recognition

## Technical Requirements

### Build System
- **Hugo static site generator**
- **GitHub Pages** or **Netlify** hosting
- **Automated builds** from content updates

### Search Infrastructure
- **Lunr.js** for client-side search
- **JSON indexes** for fast querying
- **Progressive loading** for large datasets

### Content Management
- **Markdown-based** content structure
- **YAML frontmatter** for metadata
- **Git-based** version control

This design balances the scholarly rigor of Eric Fuss's work with modern web usability, creating a digital monument to this extraordinary historical archive.