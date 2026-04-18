// js/explain.js
// AI Explain module with premium streaming output and query input
const ExplainModule = (() => {
  const btn    = document.getElementById('explain-btn');
  const output = document.getElementById('explain-output');
  const text   = document.getElementById('explain-text');
  const query  = document.getElementById('explain-query');

  btn.addEventListener('click', async () => {
    const zoneId = btn.dataset.zoneId;
    const zscore = parseFloat(btn.dataset.zscore ?? btn.dataset.score ?? '0');

    if (!zoneId) return;

    // Show loading state with animated dots
    output.innerHTML = `
      <div class="llm-header">
        <span>⚡ Processing</span>
        <span class="model-badge">Qwen3 / Groq</span>
      </div>
      <div style="display:flex;align-items:center;gap:8px;color:var(--text-muted);font-size:0.78rem;">
        Analyzing zone ${zoneId}
        <span class="loading-dots"><span></span><span></span><span></span></span>
      </div>`;
    btn.disabled = true;

    try {
      const payload = {
        zone_id: zoneId,
        z_score: zscore,
        date: document.getElementById('date-display').textContent,
      };

      // Include optional user query if present
      const userQuery = query?.value?.trim();
      if (userQuery) payload.query = userQuery;

      const res = await fetch('/api/explain', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const data = await res.json();

      if (data.explanation) {
        // Build premium LLM output with header and streamed text
        output.innerHTML = `
          <div class="llm-header">
            <span>✨ AI Analysis</span>
            <span class="model-badge">${data.model ?? 'Qwen3'}</span>
          </div>
          <div id="explain-stream"></div>`;

        const streamEl = document.getElementById('explain-stream');
        const fullText = data.explanation;

        // Stream-style character-by-character reveal with cursor
        let i = 0;
        streamEl.innerHTML = '<span class="typing-cursor"></span>';

        const interval = setInterval(() => {
          // Remove cursor, add char, reinsert cursor
          const cursor = streamEl.querySelector('.typing-cursor');
          if (cursor) cursor.remove();

          streamEl.insertAdjacentText('beforeend', fullText[i]);
          i++;

          if (i >= fullText.length) {
            clearInterval(interval);
            // Don't show cursor after done
          } else {
            streamEl.insertAdjacentHTML('beforeend', '<span class="typing-cursor"></span>');
          }
        }, 15);

      } else {
        output.innerHTML = `
          <div class="llm-header">
            <span>⚠️ Response</span>
          </div>
          <p style="color:var(--text-muted);font-size:0.78rem;margin:0;">
            ${data.error ?? 'No explanation returned.'}
          </p>`;
      }
    } catch (e) {
      output.innerHTML = `
        <div class="llm-header">
          <span>❌ Error</span>
        </div>
        <p style="color:var(--accent-red);font-size:0.78rem;margin:0;">
          Could not reach the explain endpoint. Check API connectivity.
        </p>`;
    } finally {
      btn.disabled = false;
    }
  });

  // Allow Enter key in query input to trigger explain
  if (query) {
    query.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !btn.disabled) {
        btn.click();
      }
    });
  }
})();