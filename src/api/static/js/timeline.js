// src/api/static/js/timeline.js
const Timeline = (() => {
  const slider      = document.getElementById('date-slider');
  const dateDisplay = document.getElementById('date-display');
  const playBtn     = document.getElementById('play-btn');

  let dates      = [];
  let currentIdx = 0;
  let playInterval = null;

  // ── Fetch real dates from GNN output ──
  async function init() {
    try {
      const res  = await fetch('/api/dates');
      const data = await res.json();
      dates = data.dates;

      if (dates.length === 0) {
        console.warn('No scored dates found - using mock range');
        const start = new Date('2023-10-03');
        dates = Array.from({ length: 90 }, (_, i) => {
          const d = new Date(start);
          d.setDate(d.getDate() + i);
          return d.toISOString().slice(0, 10);
        });
      }

      slider.max   = dates.length - 1;
      slider.value = 0;

      document.querySelector('#slider-labels span:first-child').textContent =
        dates[0]?.slice(0, 7) ?? '';
      document.querySelector('#slider-labels span:last-child').textContent =
        dates[dates.length - 1]?.slice(0, 7) ?? '';

      await MapModule.loadZones();
      await fetchAndRender(dates[0]);

    } catch (e) {
      console.error('Timeline init failed:', e);
    }
  }

  // ── Main render: scores (map) + alerts (sidebar) ──
  async function fetchAndRender(dateStr) {
    if (!dateStr) return;
    dateDisplay.textContent = dateStr;

    // Fire both requests in parallel
    const [scoresRes, alertsRes] = await Promise.allSettled([
      fetch(`/api/scores?date=${dateStr}`),
      fetch(`/api/alerts?date=${dateStr}&top_k=10`),
    ]);

    // Map heatmap
    if (scoresRes.status === 'fulfilled' && scoresRes.value.ok) {
      const data = await scoresRes.value.json();
      MapModule.renderZones(data.scores);
    } else {
      MapModule.renderZones({});
    }

    // Sidebar alerts
    if (alertsRes.status === 'fulfilled' && alertsRes.value.ok) {
      const data = await alertsRes.value.json();
      renderAlerts(data.alerts);
    } else {
      renderAlerts([]);
    }
  }

  // ── Render ranked alerts as premium cards ──
  function renderAlerts(alerts) {
    const list = document.getElementById('top-zones-list');

    if (!alerts || alerts.length === 0) {
      list.innerHTML = `
        <li class="empty-state">
          <div class="empty-icon">📡</div>
          No alerts for this date
        </li>`;
      return;
    }

    list.innerHTML = alerts.map((a, idx) => {
      const risk = Heatmap.riskLabel(a.score);
      const persHtml = a.persistence_days > 1
        ? `<span class="persistence-badge">🔄 ${a.persistence_days}d</span>`
        : '';

      return `
        <li>
          <div class="alert-card ${risk.card}" data-alert-id="${a.alert_id}" data-region="${a.region_id}">
            <div class="alert-header">
              <span class="zone-label">${a.region_id}</span>
              <span class="risk-badge ${risk.badge}">${risk.label}</span>
            </div>
            <div class="alert-body">
              <div class="score-display">
                <span class="score-value">${a.score.toFixed(2)}</span>
                <span class="score-unit">σ</span>
                ${persHtml}
              </div>
              <button class="false-alarm-btn"
                onclick="submitFeedback(${a.alert_id}, '${a.region_id}', 'FP')"
                title="Mark as False Alarm — recalibrates θ for this zone">
                ✕ False Alarm
              </button>
            </div>
            <div class="alert-meta">
              <span>θ = ${a.current_theta.toFixed(1)}</span>
              <span>chl_z = ${a.chl_z?.toFixed(2) ?? '—'}</span>
            </div>
          </div>
        </li>`;
    }).join('');
  }

  // ── Slider ──
  slider.addEventListener('input', () => {
    currentIdx = parseInt(slider.value);
    fetchAndRender(dates[currentIdx]);
  });

  // ── Play/Pause ──
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


// ── Global: False Alarm handler (called from inline onclick) ──
async function submitFeedback(alertId, regionId, label) {
  try {
    const res = await fetch(`/api/alerts/${alertId}/feedback`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ label, user_id: 'demo' }),
    });
    const data = await res.json();

    // Animate dismiss
    const card = document.querySelector(`.alert-card[data-alert-id="${alertId}"]`);
    if (card) {
      card.classList.add('dismissed');
      card.title = `θ: ${data.theta_before} → ${data.theta_after} (${data.reason})`;
    }

    console.log(`[feedback] ${regionId}: θ ${data.theta_before} → ${data.theta_after} | ${data.reason}`);
  } catch (e) {
    console.error('Feedback submission failed:', e);
  }
}
