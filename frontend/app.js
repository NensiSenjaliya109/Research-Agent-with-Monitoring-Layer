// ── State Management & Constants ──────────────────────────────
const API_BASE = ""; // Uses relative path for convenience when hosted on same server
let currentQueryId = null;

// Tab Switching
document.querySelectorAll('.tab').forEach(button => {
  button.addEventListener('click', () => {
    const tabName = button.getAttribute('data-tab');
    
    // Toggle tab active state
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    button.classList.add('active');
    
    // Toggle panels
    document.querySelectorAll('.tab-panel').forEach(panel => panel.classList.remove('active'));
    document.getElementById(`panel-${tabName}`).classList.add('active');
    
    if (tabName === 'history') {
      loadHistory();
    }
  });
});

// Character Counter
const textarea = document.getElementById('query-input');
const charCount = document.getElementById('char-count');
textarea.addEventListener('input', () => {
  charCount.textContent = `${textarea.value.length} / 500`;
});

function setQuery(text) {
  textarea.value = text;
  charCount.textContent = `${text.length} / 500`;
}

// ── Submit Query ───────────────────────────────────────────────
async function submitQuery() {
  const query = textarea.value.trim();
  if (!query || query.length < 3) {
    alert("Please enter a research question (at least 3 characters)");
    return;
  }

  // 1. Reset state & show loaders
  document.getElementById('ask-btn').disabled = true;
  document.getElementById('progress-card').classList.remove('hidden');
  document.getElementById('answer-card').classList.add('hidden');
  document.getElementById('error-card').classList.add('hidden');
  document.getElementById('score-card').classList.add('hidden');
  document.getElementById('metrics-card').classList.add('hidden');
  document.getElementById('issues-card').classList.add('hidden');

  updateStep('step-1', 'active', '⌛');
  updateStep('step-2', 'pending', '○');
  updateStep('step-3', 'pending', '○');
  updateStep('step-4', 'pending', '○');

  // Simple step intervals to simulate visual progress updates
  let stepTimeout1 = setTimeout(() => {
    updateStep('step-1', 'done', '✓');
    updateStep('step-2', 'active', '⌛');
  }, 1800);

  let stepTimeout2 = setTimeout(() => {
    updateStep('step-2', 'done', '✓');
    updateStep('step-3', 'active', '⌛');
  }, 4500);

  try {
    const response = await fetch(`${API_BASE}/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: query })
    });

    // Clear step updates simulation
    clearTimeout(stepTimeout1);
    clearTimeout(stepTimeout2);

    if (!response.ok) {
      throw new Error(`Server returned error status: ${response.status}`);
    }

    const data = await response.json();
    
    // Complete all steps in loading card
    updateStep('step-1', 'done', '✓');
    updateStep('step-2', 'done', '✓');
    updateStep('step-3', 'done', '✓');
    updateStep('step-4', 'done', '✓');

    setTimeout(() => {
      document.getElementById('progress-card').classList.add('hidden');
      renderResults(data);
    }, 600);

  } catch (err) {
    clearTimeout(stepTimeout1);
    clearTimeout(stepTimeout2);
    document.getElementById('progress-card').classList.add('hidden');
    document.getElementById('error-card').classList.remove('hidden');
    document.getElementById('error-text').textContent = err.message || "An unexpected network error occurred.";
    document.getElementById('ask-btn').disabled = false;
  }
}

// Update loader step UI
function updateStep(stepId, state, icon) {
  const element = document.getElementById(stepId);
  element.className = `step ${state}`;
  document.getElementById(`${stepId}-status`).textContent = icon;
}

let lastData = null;

function renderResults(data) {
  lastData = data;
  document.getElementById('ask-btn').disabled = false;
  
  if (data.error) {
    document.getElementById('error-card').classList.remove('hidden');
    document.getElementById('error-text').textContent = data.error;
    return;
  }

  // 1. Render Main Answer & Request ID
  document.getElementById('answer-card').classList.remove('hidden');
  document.getElementById('answer-text').innerHTML = formatMarkdown(data.answer);
  document.getElementById('request-id-badge').textContent = `ID: ${data.request_id || 'n/a'}`;

  // 2. Render Sources
  const sourceChips = document.getElementById('source-chips');
  sourceChips.innerHTML = '';
  if (data.sources && data.sources.length > 0) {
    document.getElementById('sources-section').classList.remove('hidden');
    data.sources.forEach(src => {
      const chip = document.createElement('a');
      chip.className = 'source-chip';
      chip.href = src;
      chip.target = '_blank';
      // extract host name
      try {
        const url = new URL(src);
        chip.textContent = url.hostname;
      } catch {
        chip.textContent = src;
      }
      sourceChips.appendChild(chip);
    });
  } else {
    document.getElementById('sources-section').classList.add('hidden');
  }

  // 3. Render Score Gauge
  const scoreVal = data.validation_score || 0;
  document.getElementById('score-card').classList.remove('hidden');
  document.getElementById('score-number').textContent = scoreVal.toFixed(2);
  
  const gaugeFill = document.getElementById('gauge-fill');
  // stroke-dashoffset: circle circumference is 314px (2 * PI * r=50). Offset = 314 * (1 - score)
  const offset = 314 * (1 - scoreVal);
  gaugeFill.style.strokeDashoffset = offset;

  // Set score label color
  const scoreLabel = document.getElementById('score-label');
  if (scoreVal >= 0.75) {
    scoreLabel.textContent = "Excellent";
    gaugeFill.style.stroke = "var(--emerald)";
  } else if (scoreVal >= 0.6) {
    scoreLabel.textContent = "Acceptable";
    gaugeFill.style.stroke = "var(--amber)";
  } else {
    scoreLabel.textContent = "Poor / Invalid";
    gaugeFill.style.stroke = "var(--red)";
  }

  // Score Breakdown
  const breakdown = document.getElementById('score-breakdown');
  breakdown.innerHTML = '';
  const validationDetails = data.validation || {};
  const metrics = [
    { label: 'Relevance', val: validationDetails.relevance_score },
    { label: 'Completeness', val: validationDetails.completeness_score },
    { label: 'Accuracy & Confidence', val: validationDetails.accuracy_confidence }
  ];

  metrics.forEach(m => {
    if (m.val !== undefined) {
      const item = document.createElement('div');
      item.className = 'breakdown-item';
      item.innerHTML = `
        <div class="breakdown-label">
          <span>${m.label}</span>
          <span>${(m.val * 100).toFixed(0)}%</span>
        </div>
        <div class="breakdown-bar">
          <div class="breakdown-fill" style="width: ${m.val * 100}%"></div>
        </div>
      `;
      breakdown.appendChild(item);
    }
  });

  // 4. Render Metrics
  document.getElementById('metrics-card').classList.remove('hidden');
  const metricsGrid = document.getElementById('metrics-grid');
  const rawMetrics = data.metrics || {};
  
  metricsGrid.innerHTML = `
    <div class="metric-item">
      <div class="metric-label">Latency</div>
      <div class="metric-value indigo">${rawMetrics.latency_seconds || '—'}s</div>
    </div>
    <div class="metric-item">
      <div class="metric-label">Est. Cost</div>
      <div class="metric-value emerald">$${(rawMetrics.estimated_cost_usd || 0).toFixed(5)}</div>
    </div>
    <div class="metric-item">
      <div class="metric-label">Tokens Used</div>
      <div class="metric-value cyan">${rawMetrics.total_tokens || '—'}</div>
    </div>
    <div class="metric-item">
      <div class="metric-label">DB Chunks</div>
      <div class="metric-value amber">${rawMetrics.breakdown?.chunks_stored || '0'}</div>
    </div>
  `;

  // Latency Breakdown Bars
  const latencyBars = document.getElementById('latency-bars');
  latencyBars.innerHTML = '<div class="latency-label">Pipeline Latency</div>';
  const bd = rawMetrics.breakdown || {};
  const total = rawMetrics.latency_seconds || 1;

  const latencies = [
    { name: 'Research & DB', val: bd.research_latency || 0 },
    { name: 'RAG Summarizer', val: bd.summarizer_latency || 0 },
    { name: 'AI Judge Validation', val: bd.validator_latency || 0 }
  ];

  latencies.forEach(l => {
    const pct = Math.max(5, Math.min(100, (l.val / total) * 100));
    const bar = document.createElement('div');
    bar.className = 'latency-bar-item';
    bar.innerHTML = `
      <span class="latency-bar-name">${l.name}</span>
      <div class="latency-bar-track">
        <div class="latency-bar-fill" style="width: ${pct}%"></div>
      </div>
      <span class="latency-bar-val">${l.val.toFixed(2)}s</span>
    `;
    latencyBars.appendChild(bar);
  });

  // 5. Validator Issues & Suggestions
  const validatorIssues = validationDetails.issues || [];
  const suggestion = validationDetails.improvement_suggestions || "None";
  
  if (validatorIssues.length > 0 || (suggestion && suggestion !== "None")) {
    document.getElementById('issues-card').classList.remove('hidden');
    const issuesList = document.getElementById('issues-list');
    issuesList.innerHTML = '';
    
    validatorIssues.forEach(issue => {
      const el = document.createElement('div');
      el.className = 'issue-item';
      el.innerHTML = `⚠️ <span>${issue}</span>`;
      issuesList.appendChild(el);
    });

    document.getElementById('suggestion-text').textContent = suggestion !== "None" ? `Suggestion: "${suggestion}"` : "";
  } else {
    document.getElementById('issues-card').classList.add('hidden');
  }
}

// ── Load History ────────────────────────────────────────────────
async function loadHistory() {
  const listEl = document.getElementById('history-list');
  listEl.innerHTML = '<div class="empty-state"><div class="spinner"></div><p style="margin-top: 10px;">Loading history...</p></div>';

  try {
    const response = await fetch(`${API_BASE}/logs?limit=30`);
    if (!response.ok) throw new Error("Could not load logs");
    const data = await response.json();
    const logs = data.logs || [];

    listEl.innerHTML = '';
    if (logs.length === 0) {
      listEl.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">📋</div>
          <p>No history yet. Run a research query first!</p>
        </div>
      `;
      return;
    }

    logs.forEach(log => {
      const score = log.validation_score || 0;
      let badgeClass = 'badge-red';
      if (score >= 0.75) badgeClass = 'badge-green';
      else if (score >= 0.6) badgeClass = 'badge-amber';

      const item = document.createElement('div');
      item.className = 'history-item';
      item.onclick = () => {
        // Switch to research tab and populate
        document.getElementById('tab-research').click();
        setQuery(log.query);
        renderResults(log);
      };

      // Format date from log timestamp
      const dateStr = log.timestamp ? log.timestamp.substring(0, 19).replace('T', ' ') : 'Unknown Date';

      item.innerHTML = `
        <div class="history-query">${log.query}</div>
        <div class="history-meta">
          <span class="history-badge ${badgeClass}">Score: ${score.toFixed(2)}</span>
          <span class="history-badge badge-indigo">Latency: ${log.metrics?.total_latency_s?.toFixed(2) || '0'}s</span>
          <span class="history-badge badge-cyan">Cost: $${(log.metrics?.estimated_cost_usd || 0).toFixed(5)}</span>
          <span class="history-badge badge-indigo">${dateStr}</span>
        </div>
      `;
      listEl.appendChild(item);
    });

  } catch (err) {
    listEl.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">❌</div>
        <p>Error loading logs: ${err.message}</p>
      </div>
    `;
  }
}

// ── Markdown Parser Helper ─────────────────────────────────────
function formatMarkdown(text) {
  if (!text) return '';
  let html = text;
  
  // Headers
  html = html.replace(/^### (.*?)$/gm, '<h3>$1</h3>');
  html = html.replace(/^## (.*?)$/gm, '<h2>$1</h2>');
  html = html.replace(/^# (.*?)$/gm, '<h1>$1</h1>');
  
  // Bold
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  
  // Lists
  html = html.replace(/^\- (.*?)$/gm, '<li>$1</li>');
  html = html.replace(/^\* (.*?)$/gm, '<li>$1</li>');
  
  return html;
}

function exportPDF() {
  if (!lastData) return;
  window.print();
}
