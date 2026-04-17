// js/timeline.js
const Timeline = (() => {
  const slider = document.getElementById('date-slider');
  const dateDisplay = document.getElementById('date-display');
  const playBtn = document.getElementById('play-btn');

  // Build date array: 2024-01-01 to 2024-03-31 (90 days)
  const START = new Date('2024-01-01');
  const dates = Array.from({ length: 90 }, (_, i) => {
    const d = new Date(START);
    d.setDate(d.getDate() + i);
    return d.toISOString().slice(0, 10);
  });

  let playInterval = null;
  let currentIdx = 0;

  async function fetchAndRender(dateStr) {
    dateDisplay.textContent = dateStr;
    try {
      const res = await fetch(`/api/scores?date=${dateStr}`);
      const data = await res.json();
      MapModule.renderZones(data.scores);
      renderTopZones(data.top_zones);
    } catch (e) {
      console.warn('Score fetch failed, using mock data');
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
      }, 600);  // advance one day every 600ms
    }
  });

  // Initial load
  fetchAndRender(dates[0]);
  MapModule.loadZones();
})();