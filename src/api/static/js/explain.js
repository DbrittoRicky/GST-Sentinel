// js/explain.js
const ExplainModule = (() => {
  const btn = document.getElementById('explain-btn');
  const output = document.getElementById('explain-text');

  btn.addEventListener('click', async () => {
    const zoneId = btn.dataset.zoneId;
    const zscore = parseFloat(btn.dataset.zscore);

    if (!zoneId) return;

    output.textContent = '⏳ Generating explanation...';
    btn.disabled = true;

    try {
      const res = await fetch('/api/explain', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          zone_id: zoneId,
          z_score: zscore,
          date: document.getElementById('date-display').textContent,
        }),
      });

      const data = await res.json();

      if (data.explanation) {
        // Stream-style character-by-character reveal
        output.textContent = '';
        let i = 0;
        const text = data.explanation;
        const interval = setInterval(() => {
          output.textContent += text[i++];
          if (i >= text.length) clearInterval(interval);
        }, 18);
      } else {
        output.textContent = data.error ?? 'No explanation returned.';
      }
    } catch (e) {
      output.textContent = '⚠️ Could not reach explain endpoint.';
    } finally {
      btn.disabled = false;
    }
  });
})();