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
    const manifestUrl = prefix.endsWith('/') ? prefix + 'js/search-manifest.json' : prefix + '/js/search-manifest.json';
    const mRes = await fetch(manifestUrl, { credentials: 'same-origin' });
    if (!mRes.ok) throw new Error('Failed to load search-manifest.json: ' + mRes.status);
    const manifest = await mRes.json();
    const datasets = Array.isArray(manifest && manifest.datasets) ? manifest.datasets : [];
    // Fetch all datasets concurrently
    const datasetPromises = datasets.map(async (ds) => {
      const path = (ds && ds.path) || '';
      const url = prefix.endsWith('/') ? (prefix + path.replace(/^\/?/, '')) : (prefix + '/' + path.replace(/^\/?/, ''));
      const res = await fetch(url, { credentials: 'same-origin' });
      if (!res.ok) throw new Error('Failed to load dataset ' + path + ': ' + res.status);
      const payload = await res.json();
      const arr = Array.isArray(payload && payload.docs) ? payload.docs : [];
      return arr;
    });
    const parts = await Promise.all(datasetPromises);
    docs = parts.flat();
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


