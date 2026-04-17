// js/timeline.js — REPLACE ENTIRE FILE
const Timeline = (() => {
  const slider      = document.getElementById('date-slider');
  const dateDisplay = document.getElementById('date-display');
  const playBtn     = document.getElementById('play-btn');

  let dates = [];
  let currentIdx = 0;
  let playInterval = null;

  // ── Fetch real dates from GNN output ──
  async function init() {
    try {
      const res = await fetch('/api/dates');
      const data = await res.json();
      dates = data.dates;

      if (dates.length === 0) {
        console.warn('No scored dates found — using mock range');
        const start = new Date('2023-10-03');
        dates = Array.from({ length: 90 }, (_, i) => {
          const d = new Date(start);
          d.setDate(d.getDate() + i);
          return d.toISOString().slice(0, 10);
        });
      }

      // Update slider range to match real dates
      slider.max = dates.length - 1;
      slider.value = 0;

      // Update slider labels to real date range
      document.querySelector('#slider-labels span:first-child').textContent =
        dates[0]?.slice(0, 7) ?? '';
      document.querySelector('#slider-labels span:last-child').textContent =
        dates[dates.length - 1]?.slice(0, 7) ?? '';

      // Load zones and first date
      await MapModule.loadZones();
      await fetchAndRender(dates[0]);

    } catch (e) {
      console.error('Timeline init failed:', e);
    }
  }

  async function fetchAndRender(dateStr) {
    if (!dateStr) return;
    dateDisplay.textContent = dateStr;
    try {
      const res = await fetch(`/api/scores?date=${dateStr}`);
      const data = await res.json();
      MapModule.renderZones(data.scores);
      renderTopZones(data.top_zones);
    } catch (e) {
      console.warn('Score fetch failed:', e);
      MapModule.renderZones({});
    }
  }

  function renderTopZones(topZones) {
    const list = document.getElementById('top-zones-list');
    if (!topZones || topZones.length === 0) {
      list.innerHTML = '<li>No anomalies detected</li>';
      return;
    }
    list.innerHTML = topZones.map(z => {
      const risk = Heatmap.riskLabel(z.z_score);
      return `<li>${z.zone_id} — <span class="${risk.cls}">${z.z_score.toFixed(2)}σ ${risk.label}</span></li>`;
    }).join('');
  }

  slider.addEventListener('input', () => {
    currentIdx = parseInt(slider.value);
    fetchAndRender(dates[currentIdx]);
  });

  playBtn.addEventListener('click', () => {
    if (playInterval) {
      clearInterval(playInterval);
      playInterval = null;
      playBtn.textContent = '▶ Play';
    } else {
      playBtn.textContent = '⏸ Pause';
      playInterval = setInterval(() => {
        currentIdx = (currentIdx + 1) % dates.length;
        slider.value = currentIdx;
        fetchAndRender(dates[currentIdx]);
      }, 600);
    }
  });

  // Boot
  init();
})();