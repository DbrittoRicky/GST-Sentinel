// src/api/static/js/history.js
// M6 - 30-day zone history sparkline using Chart.js
// Called by map.js on zone click: HistoryChart.load(zone_id)
// Also powers the graph modal popup on double-click or via button

const HistoryChart = (() => {
  const container = document.getElementById('history-chart-container');
  const canvas    = document.getElementById('history-chart');
  const histMax   = document.getElementById('hist-max');
  const histMean  = document.getElementById('hist-mean');
  const histDays  = document.getElementById('hist-days');

  // Graph modal elements
  const graphOverlay   = document.getElementById('graph-overlay');
  const graphCloseBtn  = document.getElementById('graph-close-btn');
  const graphZoneChip  = document.getElementById('graph-zone-chip');
  const graphChart     = document.getElementById('graph-chart');
  const graphStatPeak  = document.getElementById('graph-stat-peak');
  const graphStatAvg   = document.getElementById('graph-stat-avg');
  const graphStatTrend = document.getElementById('graph-stat-trend');
  const graphStatDays  = document.getElementById('graph-stat-days');

  let chartInstance = null;
  let graphChartInstance = null;
  let lastZoneId = null;
  let lastHistory = null;

  // Risk-based point colors
  function _pointColor(score) {
    if (score >= 2.5) return '#ef4444';   // CRITICAL
    if (score >= 1.5) return '#f97316';   // HIGH
    if (score >= 0.8) return '#eab308';   // ELEVATED
    return '#22d3ee';                     // NORMAL
  }

  function _segmentColors(scores) {
    return scores.map(s => _pointColor(s));
  }

  // Compute linear regression trend
  function _computeTrend(scores) {
    const n = scores.length;
    if (n < 2) return 0;
    let sumX = 0, sumY = 0, sumXY = 0, sumXX = 0;
    for (let i = 0; i < n; i++) {
      sumX += i; sumY += scores[i];
      sumXY += i * scores[i]; sumXX += i * i;
    }
    return (n * sumXY - sumX * sumY) / (n * sumXX - sumX * sumX);
  }

  // ── Sparkline in sidebar ──
  async function load(zoneId, days = 30) {
    lastZoneId = zoneId;
    try {
      const res  = await fetch(`/api/zones/${zoneId}/history?days=${days}`);
      if (!res.ok) { hide(); return; }
      const data = await res.json();

      if (!data.history || data.history.length === 0) { hide(); return; }

      lastHistory = data.history;
      const labels = data.history.map(h => h.date.slice(5));   // MM-DD
      const scores = data.history.map(h => h.score);
      const colors = _segmentColors(scores);

      // Summary stats
      const maxScore  = Math.max(...scores);
      const meanScore = scores.reduce((a, b) => a + b, 0) / scores.length;
      const daysAbove = scores.filter(s => s >= 2.0).length;

      histMax.textContent  = `Max: ${maxScore.toFixed(2)}σ`;
      histMean.textContent = `Avg: ${meanScore.toFixed(2)}σ`;
      histDays.textContent = `Days > θ: ${daysAbove}`;

      // Destroy existing chart before redrawing
      if (chartInstance) {
        chartInstance.destroy();
        chartInstance = null;
      }

      chartInstance = new Chart(canvas, {
        type: 'line',
        data: {
          labels,
          datasets: [{
            label:           'Anomaly (σ)',
            data:            scores,
            borderColor:     '#38bdf8',
            backgroundColor: _createGradient(canvas, 'rgba(56,189,248,0.15)', 'rgba(56,189,248,0.01)'),
            pointBackgroundColor: colors,
            pointBorderColor: 'transparent',
            pointRadius:     3,
            pointHoverRadius: 6,
            pointHoverBorderWidth: 2,
            pointHoverBorderColor: '#fff',
            borderWidth:     2,
            fill:            true,
            tension:         0.35,
          }],
        },
        options: {
          responsive:          true,
          maintainAspectRatio: false,
          animation:           { duration: 400, easing: 'easeOutCubic' },
          interaction:         { mode: 'nearest', intersect: false },
          plugins: {
            legend: { display: false },
            tooltip: {
              backgroundColor: 'rgba(15, 23, 42, 0.9)',
              borderColor: 'rgba(148, 163, 184, 0.15)',
              borderWidth: 1,
              cornerRadius: 8,
              padding: 10,
              titleFont: { family: 'JetBrains Mono', size: 11 },
              bodyFont: { family: 'Inter', size: 12 },
              titleColor: '#94a3b8',
              bodyColor: '#f1f5f9',
              displayColors: false,
              callbacks: {
                label: ctx => `${ctx.parsed.y.toFixed(2)}σ`,
              },
            },
          },
          scales: {
            x: {
              ticks: {
                color:    '#475569',
                font:     { family: 'JetBrains Mono', size: 9 },
                maxTicksLimit: 6,
              },
              grid: { color: 'rgba(255,255,255,0.03)', drawBorder: false },
              border: { display: false },
            },
            y: {
              ticks: {
                color: '#475569',
                font:  { family: 'JetBrains Mono', size: 9 },
              },
              grid:  { color: 'rgba(255,255,255,0.03)', drawBorder: false },
              border: { display: false },
              afterDataLimits(axis) {
                axis.max = Math.max(axis.max, 2.5);
              },
            },
          },
          onClick: () => {
            if (lastHistory && lastZoneId) {
              openGraphModal(lastZoneId, lastHistory);
            }
          },
        },
        plugins: [{
          // θ = 2.0 dashed reference line
          id: 'thetaLine',
          afterDraw(chart) {
            const { ctx, scales: { x, y } } = chart;
            const yPx = y.getPixelForValue(2.0);
            ctx.save();
            ctx.setLineDash([4, 3]);
            ctx.strokeStyle = 'rgba(251,191,36,0.35)';
            ctx.lineWidth   = 1;
            ctx.beginPath();
            ctx.moveTo(x.left,  yPx);
            ctx.lineTo(x.right, yPx);
            ctx.stroke();

            // Label
            ctx.setLineDash([]);
            ctx.fillStyle = 'rgba(251,191,36,0.5)';
            ctx.font = '500 9px "JetBrains Mono"';
            ctx.fillText('θ', x.right + 4, yPx + 3);
            ctx.restore();
          },
        }],
      });

      container.style.display = 'block';

    } catch (e) {
      console.warn('[history] Failed to load zone history:', e);
      hide();
    }
  }

  function _createGradient(canvasEl, colorStart, colorEnd) {
    const ctx = canvasEl.getContext('2d');
    const h = canvasEl.clientHeight || canvasEl.height || 300;
    const gradient = ctx.createLinearGradient(0, 0, 0, h);
    gradient.addColorStop(0, colorStart);
    gradient.addColorStop(1, colorEnd);
    return gradient;
  }

  function hide() {
    container.style.display = 'none';
    if (chartInstance) {
      chartInstance.destroy();
      chartInstance = null;
    }
  }

  // ═══════════════════════════════════════════
  // GRAPH MODAL
  // ═══════════════════════════════════════════
  function openGraphModal(zoneId, history) {
    if (!history || history.length === 0) return;

    const labels = history.map(h => h.date.slice(5));
    const scores = history.map(h => h.score);
    const colors = _segmentColors(scores);

    const maxScore  = Math.max(...scores);
    const meanScore = scores.reduce((a, b) => a + b, 0) / scores.length;
    const daysAbove = scores.filter(s => s >= 2.0).length;
    const trend     = _computeTrend(scores);

    // Populate modal
    graphZoneChip.textContent = `Zone ${zoneId}`;
    graphStatPeak.textContent = maxScore.toFixed(2) + 'σ';
    graphStatAvg.textContent  = meanScore.toFixed(2) + 'σ';
    graphStatDays.textContent = daysAbove.toString();

    // Trend display
    const trendDir = trend > 0.02 ? '↑ Rising' : trend < -0.02 ? '↓ Falling' : '→ Stable';
    graphStatTrend.textContent = trendDir;
    graphStatTrend.style.color = trend > 0.02 ? '#ef4444' : trend < -0.02 ? '#34d399' : '#94a3b8';

    // Risk color for peak
    graphStatPeak.style.color = _pointColor(maxScore);

    // Show modal BEFORE chart creation so canvas has proper dimensions
    graphOverlay.classList.add('active');

    // Wait a frame so layout properties (display: none -> flex) are applied
    // and Chart.js can read the actual clientWidth/Height.
    requestAnimationFrame(() => {
      // Destroy previous
      if (graphChartInstance) {
        graphChartInstance.destroy();
        graphChartInstance = null;
      }

      graphChartInstance = new Chart(graphChart, {
        type: 'line',
        data: {
          labels,
          datasets: [
            {
              label: 'Anomaly Score (σ)',
              data: scores,
              borderColor: '#818cf8',
              backgroundColor: _createGradient(graphChart, 'rgba(129,140,248,0.20)', 'rgba(129,140,248,0.02)'),
              pointBackgroundColor: colors,
              pointBorderColor: 'transparent',
              pointRadius: 4,
              pointHoverRadius: 7,
              pointHoverBorderWidth: 2,
              pointHoverBorderColor: '#fff',
              borderWidth: 2.5,
              fill: true,
              tension: 0.35,
            },
            {
              label: 'Trend',
              data: scores.map((_, i) => meanScore + trend * (i - scores.length / 2)),
              borderColor: 'rgba(148, 163, 184, 0.3)',
              borderDash: [6, 4],
              borderWidth: 1,
              pointRadius: 0,
              fill: false,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          animation: { duration: 500, easing: 'easeOutCubic' },
          interaction: { mode: 'index', intersect: false },
          plugins: {
            legend: {
              display: true,
              position: 'top',
              align: 'end',
              labels: {
                color: '#94a3b8',
                font: { family: 'Inter', size: 11 },
                boxWidth: 12,
                boxHeight: 2,
                useBorderRadius: true,
                borderRadius: 1,
                padding: 16,
              },
            },
            tooltip: {
              backgroundColor: 'rgba(15, 23, 42, 0.95)',
              borderColor: 'rgba(148, 163, 184, 0.15)',
              borderWidth: 1,
              cornerRadius: 10,
              padding: 14,
              titleFont: { family: 'JetBrains Mono', size: 12 },
              bodyFont: { family: 'Inter', size: 13 },
              titleColor: '#94a3b8',
              bodyColor: '#f1f5f9',
              callbacks: {
                label: ctx => {
                  if (ctx.datasetIndex === 0) return `Score: ${ctx.parsed.y.toFixed(3)}σ`;
                  return null;
                },
              },
            },
          },
          scales: {
            x: {
              ticks: {
                color: '#475569',
                font: { family: 'JetBrains Mono', size: 10 },
                maxTicksLimit: 10,
              },
              grid: { color: 'rgba(255,255,255,0.03)', drawBorder: false },
              border: { display: false },
            },
            y: {
              ticks: {
                color: '#475569',
                font: { family: 'JetBrains Mono', size: 10 },
              },
              grid: { color: 'rgba(255,255,255,0.03)', drawBorder: false },
              border: { display: false },
              afterDataLimits(axis) {
                axis.max = Math.max(axis.max, 3.0);
                axis.min = Math.min(axis.min, -0.5);
              },
            },
          },
        },
        plugins: [{
          id: 'graphThetaLine',
          afterDraw(chart) {
            const { ctx, scales: { x, y } } = chart;
            const yPx = y.getPixelForValue(2.0);
            ctx.save();
            ctx.setLineDash([6, 4]);
            ctx.strokeStyle = 'rgba(251,191,36,0.4)';
            ctx.lineWidth = 1.5;
            ctx.beginPath();
            ctx.moveTo(x.left, yPx);
            ctx.lineTo(x.right, yPx);
            ctx.stroke();

            // Label
            ctx.setLineDash([]);
            ctx.fillStyle = 'rgba(251,191,36,0.6)';
            ctx.font = '600 10px "JetBrains Mono"';
            ctx.fillText('θ = 2.0', x.right - 48, yPx - 6);
            ctx.restore();
          },
        }],
      });
    });
  }

  function closeGraphModal() {
    graphOverlay.classList.remove('active');
    if (graphChartInstance) {
      graphChartInstance.destroy();
      graphChartInstance = null;
    }
  }

  // Modal close handlers
  if (graphCloseBtn) {
    graphCloseBtn.addEventListener('click', closeGraphModal);
  }
  if (graphOverlay) {
    graphOverlay.addEventListener('click', (e) => {
      if (e.target === graphOverlay) closeGraphModal();
    });
  }

  // ESC to close
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && graphOverlay?.classList.contains('active')) {
      closeGraphModal();
    }
  });

  return { load, hide, openGraphModal };
})();
