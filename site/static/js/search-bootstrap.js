// Bootstrap: start search worker early without blocking paint
(function(){
  try {
    // Compute path prefix from current location so worker stays same-origin in dev and prod
    const segs = (window.location && window.location.pathname || '').split('/').filter(Boolean);
    const prefix = '/' + (segs.length ? (segs[0] + '/') : '');
    if (!window.BITN_SEARCH_WORKER) {
      const workerUrl = prefix + 'js/search-worker.js';
      const worker = new Worker(workerUrl);
      window.BITN_SEARCH_WORKER = worker;
      worker.addEventListener('message', (e) => {
        const msg = e.data || {};
        // Progress updates
        if (msg.type === 'progress') {
          try {
            const el = document.getElementById('search-loading');
            if (!el) return;
            if (msg.phase === 'manifest') {
              el.textContent = `Loading search index… fetching ${msg.totalDatasets || 0} datasets`;
            } else if (msg.phase === 'dataset') {
              const a = msg.loadedDatasets || 0;
              const b = msg.totalDatasets || 0;
              const n = msg.loadedDocs || 0;
              el.textContent = `Loading search index… datasets ${a}/${b}, documents ${n.toLocaleString()}`;
            } else if (msg.phase === 'datasets-complete') {
              el.textContent = `Building index… ${msg.loadedDocs ? msg.loadedDocs.toLocaleString() : ''} documents`;
            } else if (msg.phase === 'index-start') {
              el.textContent = `Building index… ${msg.totalDocs ? msg.totalDocs.toLocaleString() : ''} documents`;
            } else if (msg.phase === 'index-progress') {
              const a = msg.addedDocs || 0; const b = msg.totalDocs || 0;
              el.textContent = `Building index… ${a.toLocaleString()}/${b.toLocaleString()}`;
            } else if (msg.phase === 'index-complete') {
              el.textContent = 'Finalizing…';
            }
          } catch (_) {}
          return;
        }
        if (msg.type === 'ready') {
          window.BITN_SEARCH_READY = true;
          try {
            window.BITN_TOTAL_DOCS = (typeof msg.count === 'number') ? msg.count : 0;
            console.log('[search] ready:', window.BITN_TOTAL_DOCS, 'docs indexed');
          } catch (_) { /* no-op */ }
          window.dispatchEvent(new Event('bitn-search-ready'));
        } else if (msg.type === 'error') {
          console.warn('Search worker error:', msg.error);
        }
      });
      worker.postMessage({ type: 'init', baseUrl: prefix });
    }
  } catch (e) {
    console.warn('Search worker bootstrap failed', e);
  }
})();


