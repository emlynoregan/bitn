/**
 * Search functionality for Burra in the News Archive
 * Uses Lunr.js for client-side search
 */

class ArchiveSearch {
    constructor() {
        this.index = null;
        this.documents = [];
        this.searchInput = null;
        this.searchResults = null;
        this.isInitialized = false;
        
        this.init();
    }
    
    async init() {
        try {
            // Wait for DOM to be ready
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', () => this.setupSearch());
            } else {
                this.setupSearch();
            }
        } catch (error) {
            console.error('Search initialization failed:', error);
        }
    }
    
    async setupSearch() {
        // Get DOM elements
        this.searchInput = document.getElementById('search-input');
        this.searchResults = document.getElementById('search-results');
        
        if (!this.searchInput || !this.searchResults) {
            console.warn('Search elements not found on this page');
            return;
        }
        
        try {
            // Load search data
            await this.loadSearchData();
            
            // Build search index
            this.buildIndex();
            
            // Setup event listeners
            this.setupEventListeners();
            
            this.isInitialized = true;
            console.log('Archive search initialized successfully');
            
        } catch (error) {
            console.error('Failed to setup search:', error);
            this.showError('Search functionality is temporarily unavailable.');
        }
    }
    
    async loadSearchData() {
        try {
            // Use the base URL from Hugo if available, otherwise fall back to relative path
            const baseUrl = window.HUGO_BASE_URL || '';
            const searchDataUrl = baseUrl.endsWith('/') ? baseUrl + 'js/search-data.json' : baseUrl + '/js/search-data.json';
            
            const response = await fetch(searchDataUrl);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            this.documents = await response.json();
            console.log(`Loaded ${this.documents.length} documents for search`);
        } catch (error) {
            console.error('Failed to load search data:', error);
            throw error;
        }
    }
    
    buildIndex() {
        try {
            this.index = lunr(function () {
                this.ref('id');
                this.field('title', { boost: 10 });
                this.field('publication', { boost: 5 });
                this.field('date_range', { boost: 3 });
                this.field('content');
                
                // Add documents to index
                for (const doc of window.archiveSearch.documents) {
                    this.add(doc);
                }
            });
            console.log('Search index built successfully');
        } catch (error) {
            console.error('Failed to build search index:', error);
            throw error;
        }
    }
    
    setupEventListeners() {
        // Search input events
        this.searchInput.addEventListener('input', (e) => {
            this.debounceSearch(e.target.value);
        });
        
        this.searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.clearSearch();
            } else if (e.key === 'ArrowDown') {
                e.preventDefault();
                this.navigateResults('down');
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                this.navigateResults('up');
            } else if (e.key === 'Enter') {
                e.preventDefault();
                this.selectCurrentResult();
            }
        });
        
        this.searchInput.addEventListener('focus', () => {
            if (this.searchInput.value.trim()) {
                this.showResults();
            }
        });
        
        // Click outside to hide results
        document.addEventListener('click', (e) => {
            if (!this.searchInput.contains(e.target) && !this.searchResults.contains(e.target)) {
                this.hideResults();
            }
        });
    }
    
    debounceSearch(query) {
        clearTimeout(this.searchTimeout);
        this.searchTimeout = setTimeout(() => {
            this.performSearch(query);
        }, 300);
    }
    
    performSearch(query) {
        if (!this.isInitialized) {
            return;
        }
        
        const trimmedQuery = query.trim();
        
        if (trimmedQuery.length < 2) {
            this.hideResults();
            return;
        }
        
        try {
            // Perform search
            const results = this.index.search(trimmedQuery);
            
            // Get full document data for results
            const searchResults = results.map(result => {
                const doc = this.documents.find(d => d.id === result.ref);
                return {
                    ...doc,
                    score: result.score
                };
            }).slice(0, 10); // Limit to 10 results
            
            this.displayResults(searchResults, trimmedQuery);
            
        } catch (error) {
            console.error('Search failed:', error);
            this.showError('Search failed. Please try again.');
        }
    }
    
    displayResults(results, query) {
        if (results.length === 0) {
            this.searchResults.innerHTML = `
                <div class="search-result-item">
                    <p class="text-gray-500 text-center">No results found for "${query}"</p>
                    <p class="text-sm text-gray-400 text-center mt-2">Try different keywords or check spelling</p>
                </div>
            `;
        } else {
            this.searchResults.innerHTML = results.map((result, index) => `
                <div class="search-result-item ${index === 0 ? 'bg-gray-50' : ''}" data-url="${result.url}">
                    <h4 class="font-semibold text-gray-800 mb-1">
                        ${this.highlightMatches(result.title, query)}
                    </h4>
                    <p class="text-sm text-amber-600 mb-2">
                        ${result.publication} • ${result.date_range}
                    </p>
                    <p class="text-sm text-gray-600">
                        ${this.highlightMatches(this.truncateContent(result.content), query)}
                    </p>
                </div>
            `).join('');
            
            // Add click handlers
            this.searchResults.querySelectorAll('.search-result-item').forEach(item => {
                item.addEventListener('click', () => {
                    const url = item.getAttribute('data-url');
                    if (url) {
                        window.location.href = url;
                    }
                });
                
                item.addEventListener('mouseenter', () => {
                    this.highlightResult(item);
                });
            });
        }
        
        this.showResults();
    }
    
    highlightMatches(text, query) {
        if (!text || !query) return text;
        
        const words = query.toLowerCase().split(/\s+/);
        let highlightedText = text;
        
        words.forEach(word => {
            if (word.length > 1) {
                const regex = new RegExp(`(${this.escapeRegex(word)})`, 'gi');
                highlightedText = highlightedText.replace(regex, '<span class="search-highlight">$1</span>');
            }
        });
        
        return highlightedText;
    }
    
    truncateContent(content, maxLength = 150) {
        if (!content || content.length <= maxLength) return content;
        return content.substring(0, maxLength) + '...';
    }
    
    escapeRegex(string) {
        return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }
    
    showResults() {
        this.searchResults.classList.remove('hidden');
    }
    
    hideResults() {
        this.searchResults.classList.add('hidden');
    }
    
    clearSearch() {
        this.searchInput.value = '';
        this.hideResults();
        this.searchInput.blur();
    }
    
    navigateResults(direction) {
        const items = this.searchResults.querySelectorAll('.search-result-item');
        if (items.length === 0) return;
        
        const currentIndex = Array.from(items).findIndex(item => 
            item.classList.contains('bg-gray-50')
        );
        
        let newIndex;
        if (direction === 'down') {
            newIndex = currentIndex < items.length - 1 ? currentIndex + 1 : 0;
        } else {
            newIndex = currentIndex > 0 ? currentIndex - 1 : items.length - 1;
        }
        
        // Remove highlight from all items
        items.forEach(item => item.classList.remove('bg-gray-50'));
        
        // Highlight new item
        items[newIndex].classList.add('bg-gray-50');
        
        // Scroll into view if needed
        items[newIndex].scrollIntoView({ block: 'nearest' });
    }
    
    highlightResult(item) {
        // Remove highlight from all items
        this.searchResults.querySelectorAll('.search-result-item').forEach(el => {
            el.classList.remove('bg-gray-50');
        });
        
        // Highlight selected item
        item.classList.add('bg-gray-50');
    }
    
    selectCurrentResult() {
        const selectedItem = this.searchResults.querySelector('.search-result-item.bg-gray-50');
        if (selectedItem) {
            selectedItem.click();
        }
    }
    
    showError(message) {
        this.searchResults.innerHTML = `
            <div class="search-result-item">
                <p class="text-red-500 text-center">${message}</p>
            </div>
        `;
        this.showResults();
    }
}

// Initialize search when page loads
window.archiveSearch = new ArchiveSearch();