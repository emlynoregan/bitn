/* Web Worker: fetch and build Lunr index off the main thread */

let docs = [];
let index = null;
let docByRef = null; // url -> doc for O(1) lookup
let totalDatasets = 0;
let loadedDatasets = 0;
let loadedDocs = 0;

function buildIndex() {
  const total = docs.length;
  try { postMessage({ type: 'progress', phase: 'index-start', totalDocs: total }); } catch(_) {}
  let added = 0;
  const CHUNK = 2000; // coarse progress; avoid spamming
  index = lunr(function () {
    this.ref('url');
    this.field('title', { boost: 10 });
    this.field('type', { boost: 5 });
    this.field('date', { boost: 3 });
    this.field('content');
    for (const d of docs) {
      this.add(d);
      added++;
      if (added % CHUNK === 0) {
        try { postMessage({ type: 'progress', phase: 'index-progress', addedDocs: added, totalDocs: total }); } catch(_) {}
      }
    }
  });
  try { postMessage({ type: 'progress', phase: 'index-complete', totalDocs: total }); } catch(_) {}
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
    totalDatasets = datasets.length;
    loadedDatasets = 0;
    loadedDocs = 0;
    try { postMessage({ type: 'progress', phase: 'manifest', totalDatasets }); } catch(_) {}
    // Fetch all datasets concurrently
    const datasetPromises = datasets.map(async (ds) => {
      const path = (ds && ds.path) || '';
      const url = prefix.endsWith('/') ? (prefix + path.replace(/^\/?/, '')) : (prefix + '/' + path.replace(/^\/?/, ''));
      const res = await fetch(url, { credentials: 'same-origin' });
      if (!res.ok) throw new Error('Failed to load dataset ' + path + ': ' + res.status);
      const payload = await res.json();
      const arr = Array.isArray(payload && payload.docs) ? payload.docs : [];
      // Update progress after each dataset loads
      loadedDatasets++;
      loadedDocs += arr.length;
      try { postMessage({ type: 'progress', phase: 'dataset', loadedDatasets, totalDatasets, loadedDocs }); } catch(_) {}
      return arr;
    });
    const parts = await Promise.all(datasetPromises);
    docs = parts.flat();
    try { postMessage({ type: 'progress', phase: 'datasets-complete', totalDatasets, loadedDocs: docs.length }); } catch(_) {}
    // Build a dictionary for fast ref->doc lookups
    docByRef = Object.create(null);
    for (const d of docs) {
      if (d && typeof d.url === 'string') docByRef[d.url] = d;
    }
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
    if (!docByRef) throw new Error('docByRef not initialized');

    const t0 = (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now();
    const hits = index.search(q);
    const t1 = (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now();

    const out = [];
    for (let i = 0; i < hits.length && out.length < 50; i++) {
      const ref = hits[i].ref;
      const d = docByRef[ref];
      if (!d) throw new Error('No document found for ref: ' + ref);
      out.push(d);
    }
    const t2 = (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now();

    try { console.log('[worker] search timing', { q, hits: hits.length, indexMs: (t1 - t0).toFixed(1), mapMs: (t2 - t1).toFixed(1), totalMs: (t2 - t0).toFixed(1) }); } catch(_) {}
    postMessage({ type: 'search-result', q, results: out });
  } catch (e) {
    try { console.error('[worker] search error', e); } catch(_) {}
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


