// js/resize.js
// Sidebar resize handle — drag to resize the right panel
(() => {
  const handle  = document.getElementById('panel-resize-handle');
  const panel   = document.getElementById('panel');
  const app     = document.getElementById('app');

  if (!handle || !panel) return;

  let isResizing = false;
  let startX     = 0;
  let startWidth = 0;

  handle.addEventListener('mousedown', (e) => {
    e.preventDefault();
    isResizing = true;
    startX     = e.clientX;
    startWidth = panel.getBoundingClientRect().width;
    document.body.classList.add('resizing');
  });

  document.addEventListener('mousemove', (e) => {
    if (!isResizing) return;
    e.preventDefault();

    // Panel is on the right, so dragging left = wider, right = narrower
    const dx       = startX - e.clientX;
    const newWidth = Math.min(600, Math.max(240, startWidth + dx));

    panel.style.width = newWidth + 'px';

    // Invalidate the Leaflet map so it recalculates its container size
    if (typeof MapModule !== 'undefined' && MapModule._map) {
      MapModule._map.invalidateSize();
    }
  });

  document.addEventListener('mouseup', () => {
    if (!isResizing) return;
    isResizing = false;
    document.body.classList.remove('resizing');

    // Final map invalidation
    try {
      const mapEl = document.getElementById('map');
      if (mapEl && mapEl._leaflet_id) {
        // Leaflet stores map instance on the element
        setTimeout(() => {
          window.dispatchEvent(new Event('resize'));
        }, 50);
      }
    } catch (_) {}
  });

  // Also handle touch for mobile
  handle.addEventListener('touchstart', (e) => {
    const touch = e.touches[0];
    isResizing = true;
    startX     = touch.clientX;
    startWidth = panel.getBoundingClientRect().width;
    document.body.classList.add('resizing');
  }, { passive: false });

  document.addEventListener('touchmove', (e) => {
    if (!isResizing) return;
    e.preventDefault();
    const touch  = e.touches[0];
    const dx     = startX - touch.clientX;
    const newWidth = Math.min(600, Math.max(240, startWidth + dx));
    panel.style.width = newWidth + 'px';
  }, { passive: false });

  document.addEventListener('touchend', () => {
    if (!isResizing) return;
    isResizing = false;
    document.body.classList.remove('resizing');
    setTimeout(() => window.dispatchEvent(new Event('resize')), 50);
  });
})();
