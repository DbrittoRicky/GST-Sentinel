// src/api/static/js/history.js
// M6 — 30-day zone history sparkline using Chart.js
// Called by map.js on zone click: HistoryChart.load(zone_id)

const HistoryChart = (() => {
  const container = document.getElementById('history-chart-container');
  const canvas    = document.getElementById('history-chart');
  const histMax   = document.getElementById('hist-max');
  const histMean  = document.getElementById('hist-mean');
  const histDays  = document.getElementById('hist-days');

  let chartInstance = null;

  // Colour a single point based on score
  function _pointColor(score) {
    if (score >= 10) return '#ef4444';   // CRITICAL — red
    if (score >= 5)  return '#f97316';   // HIGH — orange
    if (score >= 2)  return '#eab308';   // ELEVATED — yellow
    return '#22d3ee';                    // NORMAL — cyan
  }

  // Build per-point color arrays for the line segments
  function _segmentColors(scores) {
    return scores.map(s => _pointColor(s));
  }

  async function load(zoneId, days = 30) {
    try {
      const res  = await fetch(`/api/zones/${zoneId}/history?days=${days}`);
      if (!res.ok) { hide(); return; }
      const data = await res.json();

      if (!data.history || data.history.length === 0) { hide(); return; }

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
            backgroundColor: 'rgba(56,189,248,0.08)',
            pointBackgroundColor: colors,
            pointRadius:     3,
            pointHoverRadius: 5,
            borderWidth:     1.5,
            fill:            true,
            tension:         0.3,
          }],
        },
        options: {
          responsive:          true,
          maintainAspectRatio: false,
          animation:           { duration: 300 },
          plugins: {
            legend: { display: false },
            tooltip: {
              callbacks: {
                label: ctx => `${ctx.parsed.y.toFixed(2)}σ`,
              },
            },
          },
          scales: {
            x: {
              ticks: {
                color:    '#64748b',
                font:     { size: 9 },
                maxTicksLimit: 6,
              },
              grid: { color: 'rgba(255,255,255,0.05)' },
            },
            y: {
              ticks: {
                color: '#64748b',
                font:  { size: 9 },
              },
              grid:  { color: 'rgba(255,255,255,0.05)' },
              // Draw θ=2.0 reference line
              afterDataLimits(axis) {
                axis.max = Math.max(axis.max, 2.5);
              },
            },
          },
        },
        plugins: [{
          // Draw θᵢ = 2.0 dashed reference line
          id: 'thetaLine',
          afterDraw(chart) {
            const { ctx, scales: { x, y } } = chart;
            const yPx = y.getPixelForValue(2.0);
            ctx.save();
            ctx.setLineDash([4, 3]);
            ctx.strokeStyle = 'rgba(251,191,36,0.5)';
            ctx.lineWidth   = 1;
            ctx.beginPath();
            ctx.moveTo(x.left,  yPx);
            ctx.lineTo(x.right, yPx);
            ctx.stroke();
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

  function hide() {
    container.style.display = 'none';
    if (chartInstance) {
      chartInstance.destroy();
      chartInstance = null;
    }
  }

  return { load, hide };
})();
