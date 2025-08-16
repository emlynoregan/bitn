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
        if (msg.type === 'ready') {
          window.BITN_SEARCH_READY = true;
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


