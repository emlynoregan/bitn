/**
 * Search functionality for Burra in the News Archive
 * Uses Lunr.js for client-side search
 */

class ArchiveSearch {
    constructor() {
        this.index = null; // unused when worker is present
        this.worker = window.BITN_SEARCH_WORKER || null;
        this.documents = [];
        this.searchInput = null;
        this.searchResults = null;
        this.isInitialized = false;
        // status helpers no timers; render via innerHTML
        
        this.init();
    }
    
    async init() {
        try {
            console.log('[search] init');
            // Wait for DOM to be ready
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', () => { console.log('[search] DOMContentLoaded'); this.setupSearch(); });
            } else {
                console.log('[search] DOM already ready');
                this.setupSearch();
            }
            // Bind for PJAX (Swup) navigations: re-bind inputs only, keep index in memory
            const onSwup = () => { console.log('[search] swup nav event -> setupSearch'); this.setupSearch(); };
            document.addEventListener('swup:contentReplaced', onSwup);
            document.addEventListener('contentReplaced', onSwup);
            document.addEventListener('content:replace', onSwup);
            document.addEventListener('swup:page:view', onSwup);
            window.addEventListener('popstate', onSwup);
            // Fallback: delayed re-check after navigation
            window.addEventListener('bitn-search-navigate', () => {
                setTimeout(() => this.setupSearch(), 0);
                setTimeout(() => this.setupSearch(), 120);
                setTimeout(() => this.setupSearch(), 400);
            });
        } catch (error) {
            console.error('Search initialization failed:', error);
        }
    }
    
    async setupSearch() {
        // Get DOM elements
        this.searchInput = document.getElementById('search-input');
        // Optional: dropdown container in header (not used for dedicated results page)
        this.searchResults = document.getElementById('search-results');
        const loadingEl = document.getElementById('search-loading');
        const searchUiEl = document.getElementById('search-ui');
        const pageResultsEl = document.getElementById('search-page-results');
        const pageIntroEl = document.getElementById('search-intro');
        const pageStatusEl = null;
        const mainContainer = document.getElementById('swup');
        const pageInput = mainContainer ? mainContainer.querySelector('#search-input') : null;
        console.log('[search] setupSearch elements', {
            hasInput: !!this.searchInput,
            hasDropdown: !!this.searchResults,
            hasPageResults: !!pageResultsEl,
            hasPageInput: !!pageInput,
            hasIntro: !!pageIntroEl,
            hasStatus: !!pageStatusEl
        });
        
        if (!this.searchInput) return;
        
        try {
            const showReady = () => {
                if (loadingEl) loadingEl.style.display = 'none';
                if (searchUiEl) searchUiEl.style.display = '';
                this.isInitialized = true;
                console.log('[search] showReady: UI ready, workerReady=', !!window.BITN_SEARCH_READY);
            };
            const showLoading = () => {
                if (loadingEl) loadingEl.style.display = '';
                if (searchUiEl) searchUiEl.style.display = 'none';
            };

            if (window.BITN_SEARCH_READY) {
                this.worker = window.BITN_SEARCH_WORKER || null;
                showReady();
            } else {
                showLoading();
                window.addEventListener('bitn-search-ready', () => {
                    this.worker = window.BITN_SEARCH_WORKER || null;
                    console.log('[search] bitn-search-ready event received');
                    showReady();
                }, { once: true });
            }
            
            // Setup event listeners
            this.setupEventListeners();
            
            console.log('Archive search initialized (UI wired)');
            
            // If we're on the dedicated search page and have a query, run it immediately
            if (pageResultsEl) {
                const params = new URLSearchParams(window.location.search);
                let q = params.get('q');
                // Fallback: if URL has no q (timing with PJAX), use current header input value
                if ((!q || q.length === 0) && pageInput && pageInput.value) {
                    q = pageInput.value;
                }
                console.log('[search] setupSearch on search page', { qParam: q, pageInputVal: pageInput ? pageInput.value : null, workerReady: !!window.BITN_SEARCH_READY });
                if (q) {
                    if (pageInput) pageInput.value = q;
                    // Try immediately, then retry a few times if container not ready
                    const tryRun = (attempt = 0) => {
                        const containerReady = document.getElementById('search-page-results');
                        console.log('[search] tryRun', { attempt, containerReady: !!containerReady });
                        if (containerReady) {
                            console.log('[search] triggering performSearch from setupSearch attempt', attempt, 'q', q);
                            if (pageIntroEl) pageIntroEl.style.display = 'none';
                            // If worker ready, search now; otherwise wait for ready event
                            if (window.BITN_SEARCH_READY && window.BITN_SEARCH_WORKER) {
                                this.performSearch(q);
                                window.BITN_NAVIGATING_TO_SEARCH = false;
                            } else {
                                console.log('[search] worker not ready; waiting for bitn-search-ready');
                                window.addEventListener('bitn-search-ready', () => { console.log('[search] bitn-search-ready -> performSearch'); this.performSearch(q); }, { once: true });
                                window.addEventListener('bitn-search-ready', () => { window.BITN_NAVIGATING_TO_SEARCH = false; }, { once: true });
                            }
                        } else if (attempt < 10) {
                            setTimeout(() => tryRun(attempt + 1), 50);
                        }
                    };
                    tryRun();
                } else {
                    // No query → reset to intro state (single intro only)
                    document.body.classList.remove('search-has-results');
                    if (pageIntroEl) pageIntroEl.style.display = 'block';
                    // no status element now
                    if (pageResultsEl) pageResultsEl.innerHTML = '';
                    console.log('[search] no query: showing intro', { hasIntro: !!pageIntroEl });
                    window.BITN_NAVIGATING_TO_SEARCH = false;
                }
            }
            
        } catch (error) {
            console.error('Failed to setup search:', error);
            this.showError('Search functionality is temporarily unavailable.');
        }
    }
    
    async loadSearchData() {
        try {
            // Build path prefix from current location to support local dev under subpaths (e.g. /bitn/)
            const segments = window.location.pathname.split('/').filter(Boolean);
            const prefix = segments.length > 0 ? `/${segments[0]}/` : '/';
            const searchDataUrl = `${prefix}js/search-data.json`;
            console.log('[search] fetching', searchDataUrl, 'prefix', prefix, 'path', window.location.pathname);
            
            const response = await fetch(searchDataUrl);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            this.documents = await response.json();
            console.log('[search] loaded documents:', this.documents.length);
        } catch (error) {
            console.error('Failed to load search data:', error);
            throw error;
        }
    }
    
    buildIndex() {
        try {
            this.index = lunr(function () {
                this.ref('url');
                this.field('title', { boost: 10 });
                this.field('type', { boost: 5 });
                this.field('date', { boost: 3 });
                this.field('content');

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
        // Dedicated search page flow: submit on Enter or button click
        const submit = () => {
            if (window.BITN_NAVIGATING_TO_SEARCH) {
                console.log('[search] submit ignored: navigating flag set');
                return;
            }
            const query = (this.searchInput.value || '').trim();
            if (!query) return;
            const baseUrl = window.HUGO_BASE_URL || '';
            const searchPath = 'search/?q=' + encodeURIComponent(query);
            const sep = baseUrl.endsWith('/') ? '' : '/';
            const url = baseUrl ? (baseUrl + sep + searchPath) : '/' + searchPath;
            const pageContainer = document.getElementById('search-page-results');
            // If already on the search page, run in-place: update URL and perform search
            if (pageContainer) {
                console.log('[search] submit in-place on search page', { url, query });
                try {
                    window.history.pushState({}, '', url);
                } catch (_) {}
                const pageIntroEl = document.getElementById('search-intro');
                if (pageIntroEl) pageIntroEl.style.display = 'none';
                // no status element now
                this.performSearch(query);
                return;
            }
            // Otherwise, navigate to search page (PJAX if available)
            console.log('[search] submit navigate', { url, hasSwup: !!window.__swupInstance });
            window.BITN_NAVIGATING_TO_SEARCH = true;
            try { this.searchInput.blur(); } catch (_) {}
            if (window.__swupInstance && typeof window.__swupInstance.navigate === 'function') {
                window.__swupInstance.navigate(url);
                try { window.dispatchEvent(new Event('bitn-search-navigate')); } catch (_) {}
            } else {
                window.location.href = url;
            }
        };

        this.searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                submit();
            } else if (e.key === 'Escape') {
                this.clearSearch();
            }
        });

        const btn = document.getElementById('search-button');
        if (btn) {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                submit();
            });
        }
    }
    
    debounceSearch(query) {
        clearTimeout(this.searchTimeout);
        this.searchTimeout = setTimeout(() => {
            this.performSearch(query);
        }, 300);
    }
    
    async performSearch(query) {
        if (!this.isInitialized) {
            return;
        }
        
        const trimmedQuery = query.trim();
        console.log('[search] performSearch', trimmedQuery);
        
        if (trimmedQuery.length < 2) {
            const pageContainer = document.getElementById('search-page-results');
            if (pageContainer) pageContainer.innerHTML = '';
            return;
        }
        
        try {
            // Show status on search page and hide intro if present
            const pageIntroEl = document.getElementById('search-intro');
            if (pageIntroEl) { pageIntroEl.style.display = 'none'; console.log('[search] hid intro'); }
            const pageSearchingEl = document.getElementById('searching');
            if (pageSearchingEl) { pageSearchingEl.style.display = 'block'; console.log('[search] showing searching'); }

            // Defer heavy work to allow searching indicator to render
            setTimeout(() => {
                try {
                    const worker = window.BITN_SEARCH_WORKER;
                    if (!worker) throw new Error('Worker not initialized');
                    const onMsg = (e) => {
                        const msg = e.data || {};
                        if (msg.type === 'search-result' && msg.q === trimmedQuery) {
                            worker.removeEventListener('message', onMsg);
                            const searchResults = msg.results || [];
                            if (pageSearchingEl) { pageSearchingEl.style.display = 'none'; console.log('[search] hiding searching'); }
                            const pageContainer = document.getElementById('search-page-results');
                            if (pageContainer) {
                                this.renderPageResults(pageContainer, searchResults, trimmedQuery);
                                document.body.classList.add('search-has-results');
                            } else {
                                this.displayResults(searchResults, trimmedQuery);
                            }
                        }
                    };
                    worker.addEventListener('message', onMsg);
                    worker.postMessage({ type: 'search', q: trimmedQuery });
                } catch (innerErr) {
                    console.error('[search] Search failed (inner):', innerErr);
                }
            }, 0);

        } catch (error) {
            console.error('[search] Search failed:', error);
            const pageContainer = document.getElementById('search-page-results');
            const pageIntroEl = document.getElementById('search-intro');
            if (pageIntroEl) { pageIntroEl.style.display = 'none'; console.log('[search] renderPageResults hid intro'); }
            // no status element now
            if (pageContainer) {
                pageContainer.innerHTML = '<p class="text-red-600">Search failed. Please try again.</p>';
            } else {
                this.showError('Search failed. Please try again.');
            }
        }
    }
    
    displayResults(results, query) {
        if (!this.searchResults) return;
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
                        ${(result.type || '').toString()} ${result.date ? ('• ' + result.date) : ''}
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
                        const baseUrl = window.HUGO_BASE_URL || '';
                        const sep = baseUrl.endsWith('/') ? '' : '/';
                        const path = url.startsWith('/') ? url.substring(1) : url;
                        const navigateUrl = baseUrl ? (baseUrl + sep + path) : url;
                        // Prefer PJAX navigation to preserve JS state
                        if (window.__swupInstance && typeof window.__swupInstance.navigate === 'function') {
                            window.__swupInstance.navigate(navigateUrl);
                        } else {
                            window.location.href = navigateUrl;
                        }
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
        if (this.searchResults) this.searchResults.classList.remove('hidden');
    }
    
    hideResults() {
        if (this.searchResults) this.searchResults.classList.add('hidden');
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

    // Render results onto the dedicated search page container
    renderPageResults(container, results, query) {
        try {
            if (!container) return;
            if (!results || results.length === 0) {
                container.innerHTML = `<p class="text-gray-500">No results match your search.</p>`;
                document.body.classList.add('search-has-results');
                return;
            }
            const header = `<h2 class="text-xl font-semibold text-gray-800 mb-4">Found ${results.length} results:</h2>`;
            container.innerHTML = header + results.map(r => `
                <div class="p-4 bg-white rounded-lg shadow border border-gray-200">
                    <a class="block" data-url="${r.url}">
                        <h4 class="font-semibold text-gray-800 mb-1">${this.highlightMatches(r.title, query)}</h4>
                        <p class="text-sm text-amber-600 mb-2">${(r.type||'').toString()} ${r.date ? ('• ' + r.date) : ''}</p>
                        <p class="text-sm text-gray-600">${this.highlightMatches(this.truncateContent(r.content), query)}</p>
                    </a>
                </div>
            `).join('');
            document.body.classList.add('search-has-results');
            // Navigation: prefer PJAX/Swup
            container.querySelectorAll('a[data-url]').forEach(a => {
                a.addEventListener('click', (e) => {
                    e.preventDefault();
                    const url = a.getAttribute('data-url');
                    if (!url) return;
                    const baseUrl = window.HUGO_BASE_URL || '';
                    const sep = baseUrl.endsWith('/') ? '' : '/';
                    const path = url.startsWith('/') ? url.substring(1) : url;
                    const navigateUrl = baseUrl ? (baseUrl + sep + path) : url;
                    if (window.__swupInstance && typeof window.__swupInstance.navigate === 'function') {
                        window.__swupInstance.navigate(navigateUrl);
                    } else {
                        window.location.href = navigateUrl;
                    }
                });
            });
            // no status element now
        } catch (err) {
            console.error('[search] renderPageResults failed', err);
        }
    }

    // Status helpers removed

    // Render intro block into results container when no search has happened
    renderIntro(container) {
        try {
            if (!container) return;
            const totalDocs = (window.BITN_TOTAL_DOCS || 14);
            const range = (window.BITN_DATE_RANGE || '1845-2016');
            container.innerHTML = `
                <div class="text-center mb-8">
                    <h1 class="text-3xl font-serif font-bold text-gray-800 mb-4">Search the Archive</h1>
                    <p class="text-lg text-gray-600">Search through ${totalDocs} historical documents spanning ${range}</p>
                </div>
            `;
        } catch (e) {
            console.warn('[search] renderIntro failed', e);
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