/* Web Worker: fetch and build Lunr index off the main thread */

let docs = [];
let index = null;

function buildIndex() {
  index = lunr(function () {
    this.ref('url');
    this.field('title', { boost: 10 });
    this.field('type', { boost: 5 });
    this.field('date', { boost: 3 });
    this.field('content');
    for (const d of docs) this.add(d);
  });
}

async function init(baseUrl) {
  try {
    const prefix = baseUrl || '';
    // Load lunr inside worker context
    try { importScripts(prefix + 'js/lunr.min.js'); } catch (e) { /* ignore, will error below if missing */ }
    const url = prefix.endsWith('/') ? prefix + 'js/search-data.json' : prefix + '/js/search-data.json';
    const res = await fetch(url, { credentials: 'same-origin' });
    const data = await res.json();
    docs = Array.isArray(data) ? data : [];
    if (typeof lunr !== 'undefined') {
      buildIndex();
    } else {
      throw new Error('lunr not loaded in worker');
    }
    postMessage({ type: 'ready', count: docs.length });
  } catch (e) {
    postMessage({ type: 'error', error: String(e) });
  }
}

function handleSearch(q) {
  if (!index) return postMessage({ type: 'search-result', q, results: [] });
  try {
    const hits = index.search(q);
    const out = hits.map(h => docs.find(d => d.url === h.ref)).filter(Boolean).slice(0, 50);
    postMessage({ type: 'search-result', q, results: out });
  } catch (e) {
    postMessage({ type: 'search-result', q, results: [] });
  }
}

self.onmessage = (e) => {
  const msg = e.data || {};
  if (msg.type === 'init') {
    // Expect msg.baseUrl
    init(msg.baseUrl || '');
  } else if (msg.type === 'search') {
    handleSearch(msg.q || '');
  }
};


