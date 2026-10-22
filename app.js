'use strict';

// ── State & API Configuration ───────────────────────────────────────────────
const API_BASE = window.CDI_API_URL || localStorage.getItem('CDI_API_URL') || (
  window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? (window.location.port === '8000' ? '/api/v1' : 'http://127.0.0.1:8000/api/v1')
    : '/api/v1'
);

const ADMIN_API_KEY = 'cdi-admin-key-2026';

let protocolsList = [];
let protoData = [];
let dynamicWeights = { economic: 0.25, governance: 0.25, structural: 0.25, development: 0.25 };
let cdiSeries = {};
let visible = {};
let cdiChart = null;
let radarChart = null;
let centralityChart = null;

let refreshInterval = 30;
let countdown = 30;
let countdownTimer = null;
let priceTimer = null;
let backendConnected = false;

const DIMENSIONS = [
  { key: 'economic', label: 'Economic Decentralization', color: '#378ADD' },
  { key: 'governance', label: 'Governance Decentralization', color: '#EF9F27' },
  { key: 'structural', label: 'Structural Network Decentralization', color: '#1D9E75' },
  { key: 'development', label: 'Development Decentralization', color: '#D85A30' },
];

const TOKEN_META = [
  { sym: 'UNI', name: 'Uniswap', base: 7.82, color: '#378ADD', bg: '#0d2440', fg: '#5aadff' },
  { sym: 'AAVE', name: 'Aave', base: 88.40, color: '#1D9E75', bg: '#0d2b22', fg: '#3dd6a3' },
  { sym: 'SUSHI', name: 'SushiSwap', base: 1.12, color: '#EF9F27', bg: '#2b200a', fg: '#f5b94d' },
  { sym: 'CRV', name: 'Curve', base: 0.34, color: '#D85A30', bg: '#2b150a', fg: '#f58a60' },
  { sym: 'COMP', name: 'Compound', base: 44.10, color: '#7F77DD', bg: '#1e1b3a', fg: '#aaa4f5' },
];

let tokenPrices = TOKEN_META.map(t => ({
  ...t,
  price: t.base,
  prevPrice: t.base,
  hist: Array.from({ length: 24 }, () => t.base * (1 + (Math.random() - 0.5) * 0.04)),
}));

// ── Helpers ─────────────────────────────────────────────────────────────────
function fmt(n, dec = 3) {
  if (n == null || isNaN(n)) return '—';
  return parseFloat(n).toFixed(dec);
}

function clamp(v, min = 0, max = 1) {
  return Math.max(min, Math.min(max, v));
}

function riskLabel(score) {
  const s = parseFloat(score);
  if (s > 0.60) return ['High Risk', 'risk-high'];
  if (s > 0.40) return ['Moderate', 'risk-mod'];
  return ['Low Risk', 'risk-low'];
}

function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// ── API Communication ───────────────────────────────────────────────────────
async function apiFetch(endpoint, options = {}) {
  const headers = {
    'Accept': 'application/json',
    ...(options.headers || {}),
  };
  if (options.auth) {
    headers['X-API-Key'] = ADMIN_API_KEY;
  }
  if (options.body && typeof options.body === 'object') {
    headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(options.body);
  }

  const url = `${API_BASE}${endpoint}`;
  const response = await fetch(url, { ...options, headers });
  if (!response.ok) {
    let errorDetail = `HTTP ${response.status}`;
    try {
      const errJson = await response.json();
      errorDetail = errJson.detail || errorDetail;
    } catch (_) {}
    throw new Error(errorDetail);
  }
  if (response.status === 204) return null;
  return response.json();
}

async function checkBackendHealth() {
  const statusEl = document.getElementById('api-status');
  const indEl = document.getElementById('backend-indicator');
  try {
    const data = await apiFetch('/health');
    backendConnected = true;
    if (statusEl) {
      statusEl.textContent = `API: Online v${data.version}`;
      statusEl.className = 'graphx-status online';
    }
    if (indEl) indEl.textContent = 'Live REST Engine';
    return true;
  } catch (err) {
    backendConnected = false;
    if (statusEl) {
      statusEl.textContent = 'API: Offline (Simulated Fallback)';
      statusEl.className = 'graphx-status offline';
    }
    if (indEl) indEl.textContent = 'Fallback Cache';
    return false;
  }
}

// ── Data Ingestion & State Refresh ──────────────────────────────────────────
async function fetchOverviewMetrics() {
  try {
    const overview = await apiFetch('/metrics/overview');
    document.getElementById('avg-cdi').textContent = fmt(overview.avg_cdi);
    document.getElementById('avg-gini').textContent = fmt(overview.avg_gini);
    document.getElementById('avg-entropy').textContent = fmt(overview.avg_entropy, 2);
    document.getElementById('avg-hhi').textContent = Math.round(overview.avg_hhi || 0).toLocaleString();
    document.getElementById('cdi-interp').textContent = overview.interpretation || 'Calculated';

    document.getElementById('cdi-fill').style.width = (clamp(overview.avg_cdi) * 100) + '%';
    document.getElementById('gini-fill').style.width = (clamp(overview.avg_gini) * 100) + '%';
    document.getElementById('entropy-fill').style.width = (clamp(overview.avg_entropy / 8.0) * 100) + '%';
    document.getElementById('hhi-fill').style.width = (clamp(overview.avg_hhi / 10000.0) * 100) + '%';

    protoData = overview.rankings || [];
    renderProtoTable();
    renderDimensionScoreGrid(overview.dimensions);
    renderRadarChart();
    renderParadox();
    renderGovHeatmap();
    renderCentralityChart();
    updateSensitivityDropdown();
  } catch (err) {
    console.warn('Could not load overview metrics from API:', err.message);
  }
}

async function fetchHistoricalSeries() {
  if (!protoData || protoData.length === 0) return;
  for (const p of protoData) {
    try {
      const data = await apiFetch(`/protocols/${p.id}/temporal-drift?lookback=60`);
      cdiSeries[p.id] = data.history || [];
      if (!(p.id in visible)) visible[p.id] = true;
    } catch (err) {
      // Fallback synthetic series if drift endpoint fails
      cdiSeries[p.id] = Array.from({ length: 60 }, (_, i) => p.cdi + (Math.sin(i / 5) * 0.02));
      if (!(p.id in visible)) visible[p.id] = true;
    }
  }
  updateCDIChart();
  renderTemporalSignals();
  renderDriftAlerts();
}

// ── Rendering Functions ─────────────────────────────────────────────────────
function renderProtoTable() {
  const tbody = document.getElementById('proto-rows');
  if (!tbody) return;

  const search = (document.getElementById('proto-search')?.value || '').toLowerCase();
  const category = document.getElementById('proto-category')?.value || '';

  const filtered = protoData.filter(p => {
    const matchSearch = p.name.toLowerCase().includes(search) || p.symbol.toLowerCase().includes(search);
    const matchCat = !category || p.category === category;
    return matchSearch && matchCat;
  });

  if (filtered.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" style="text-align:center;padding:20px;color:var(--text3)">No protocols found.</td></tr>`;
    return;
  }

  tbody.innerHTML = filtered.map((p, i) => {
    const [rl, rc] = riskLabel(p.risk);
    const barW = Math.round(p.cdi * 100);
    return `
      <tr>
        <td><span class="rank-num">${i + 1}</span></td>
        <td>
          <div class="proto-name-cell">
            <div class="name">${p.name} (${p.symbol})</div>
            <div class="tag">${p.slug}</div>
          </div>
        </td>
        <td><span class="tag" style="background:rgba(255,255,255,0.06)">${p.category || 'DEX'}</span></td>
        <td>
          <div class="cdi-cell">
            <div class="cdi-bar-bg">
              <div class="cdi-bar-fg" style="width:${barW}%;background:${p.color || '#378ADD'}"></div>
            </div>
            <span class="cdi-num">${fmt(p.cdi)}</span>
          </div>
        </td>
        <td><span class="gini-num">${fmt(p.gini)}</span></td>
        <td><span class="entropy-num">${Math.round(p.hhi || 0).toLocaleString()}</span></td>
        <td><span class="risk-pill ${rc}">${rl}</span></td>
        <td>
          <button class="btn-action-sm" onclick="recalculateProtocol(${p.id})">↻ Sync</button>
          <button class="btn-danger-sm" onclick="deleteProtocol(${p.id}, '${p.name}')">✕</button>
        </td>
      </tr>
    `;
  }).join('');
}

function filterProtocols() {
  renderProtoTable();
}

function renderDimensionScoreGrid(dimensions) {
  const grid = document.getElementById('dimension-score-grid');
  if (!grid || !dimensions) return;
  grid.innerHTML = DIMENSIONS.map(d => {
    const val = dimensions[d.key] || 0.5;
    return `
      <div class="dim-card">
        <div class="dim-head">
          <span class="dim-dot" style="background:${d.color}"></span>
          <span>${d.label}</span>
        </div>
        <div class="dim-score">${fmt(val)}</div>
        <div class="dim-bar"><div class="dim-fill" style="width:${Math.round(val * 100)}%;background:${d.color}"></div></div>
      </div>
    `;
  }).join('');
}

function renderRadarChart() {
  const ctx = document.getElementById('radarChart');
  if (!ctx || protoData.length === 0) return;

  const labels = ['Economic', 'Governance', 'Structural', 'Development'];
  const datasets = protoData.map(p => ({
    label: p.name,
    data: [
      parseFloat(p.economic || 0.5),
      parseFloat(p.governance || 0.5),
      parseFloat(p.structural || 0.5),
      parseFloat(p.development || 0.5),
    ],
    borderColor: p.color || '#378ADD',
    backgroundColor: (p.color || '#378ADD') + '22',
    borderWidth: 1.5,
    pointRadius: 3,
  }));

  if (radarChart) {
    radarChart.data.datasets = datasets;
    radarChart.update('none');
  } else {
    radarChart = new Chart(ctx, {
      type: 'radar',
      data: { labels, datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          r: {
            min: 0,
            max: 1,
            grid: { color: 'rgba(255,255,255,0.07)' },
            angleLines: { color: 'rgba(255,255,255,0.07)' },
            pointLabels: { color: '#9095b0', font: { size: 11 } },
            ticks: { display: false, stepSize: 0.25 },
          }
        }
      }
    });
  }
}

function updateCDIChart() {
  const ctx = document.getElementById('cdiChart');
  if (!ctx) return;

  const datasets = protoData.map(p => ({
    label: p.name,
    data: cdiSeries[p.id] || [],
    borderColor: p.color || '#378ADD',
    backgroundColor: 'transparent',
    borderWidth: 1.5,
    pointRadius: 0,
    tension: 0.35,
    hidden: !visible[p.id],
  }));

  const labels = Array.from({ length: 60 }, (_, i) => `T-${60 - i}d`);

  if (cdiChart) {
    cdiChart.data.datasets = datasets;
    cdiChart.data.labels = labels;
    cdiChart.update('none');
  } else {
    cdiChart = new Chart(ctx, {
      type: 'line',
      data: { labels, datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            mode: 'index',
            intersect: false,
            backgroundColor: '#1a1d32',
            borderColor: 'rgba(255,255,255,0.12)',
            borderWidth: 1,
          }
        },
        scales: {
          x: {
            grid: { color: 'rgba(255,255,255,0.04)' },
            ticks: { color: '#5a5f7a', font: { size: 10 } }
          },
          y: {
            min: 0.20,
            max: 0.90,
            grid: { color: 'rgba(255,255,255,0.04)' },
            ticks: { color: '#5a5f7a', font: { size: 10 }, callback: v => v.toFixed(2) }
          }
        }
      }
    });
  }

  // Render toggles
  const wrap = document.getElementById('proto-btns');
  const legend = document.getElementById('chart-legend');
  if (wrap) {
    wrap.innerHTML = protoData.map(p => `
      <button
        class="proto-btn ${visible[p.id] ? 'active' : ''}"
        style="--pc:${p.color || '#378ADD'}"
        onclick="toggleProtoVisibility(${p.id}, this)"
      >${p.name}</button>
    `).join('');
  }
  if (legend) {
    legend.innerHTML = protoData.map(p => `
      <div class="legend-item">
        <div class="legend-dot" style="background:${p.color || '#378ADD'}"></div>
        <span>${p.name}</span>
      </div>
    `).join('');
  }
}

function toggleProtoVisibility(id, btn) {
  visible[id] = !visible[id];
  btn.classList.toggle('active', visible[id]);
  if (cdiChart) {
    const ds = cdiChart.data.datasets.find(d => d.label === protoData.find(x => x.id === id)?.name);
    if (ds) ds.hidden = !visible[id];
    cdiChart.update();
  }
}

function renderGovHeatmap() {
  const container = document.getElementById('gov-heatmap');
  if (!container || protoData.length === 0) return;

  const headers = ['Protocol', 'Voting HHI', 'Centrality', 'Cartel Risk'];
  const head = `<div class="heat-row heat-head">${headers.map(h => `<div class="heat-cell">${h}</div>`).join('')}</div>`;
  const body = protoData.map(p => {
    const hhiShare = clamp((p.hhi || 2000) / 10000);
    const cent = clamp(1.0 - (p.governance || 0.5));
    const cartel = clamp(p.risk || 0.3);
    return `
      <div class="heat-row">
        <div class="heat-cell heat-proto">${p.name}</div>
        <div class="heat-cell heat-value" style="background:rgba(226,75,74,${(0.15 + hhiShare * 0.7).toFixed(2)})">${fmt(hhiShare)}</div>
        <div class="heat-cell heat-value" style="background:rgba(239,159,39,${(0.15 + cent * 0.7).toFixed(2)})">${fmt(cent)}</div>
        <div class="heat-cell heat-value" style="background:rgba(226,75,74,${(0.15 + cartel * 0.7).toFixed(2)})">${fmt(cartel)}</div>
      </div>
    `;
  }).join('');
  container.innerHTML = head + body;
}

function renderCentralityChart() {
  const ctx = document.getElementById('centralityChart');
  if (!ctx || protoData.length === 0) return;

  const labels = ['P10', 'P20', 'P30', 'P40', 'P50', 'P60', 'P70', 'P80', 'P90', 'P100'];
  const datasets = protoData.map(p => {
    const gini = p.gini || 0.3;
    const data = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100].map(q => {
      const n = q / 100;
      return parseFloat((Math.pow(n, 1.0 - gini * 0.6) * (0.6 + gini * 0.4)).toFixed(3));
    });
    return {
      label: p.name,
      data,
      borderColor: p.color || '#378ADD',
      backgroundColor: 'transparent',
      borderWidth: 1.5,
      pointRadius: 2,
    };
  });

  if (centralityChart) {
    centralityChart.data.datasets = datasets;
    centralityChart.update('none');
  } else {
    centralityChart = new Chart(ctx, {
      type: 'line',
      data: { labels, datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#5a5f7a', font: { size: 10 } } },
          y: { min: 0, max: 1, grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#5a5f7a', font: { size: 10 } } }
        }
      }
    });
  }
}

function renderTemporalSignals() {
  const container = document.getElementById('temporal-signals');
  if (!container || protoData.length === 0) return;
  container.innerHTML = protoData.map(p => {
    const series = cdiSeries[p.id] || [];
    const diffs = series.slice(1).map((v, i) => v - series[i]);
    const vol = diffs.length > 0 ? (diffs.reduce((s, x) => s + x * x, 0) / diffs.length) ** 0.5 : 0.005;
    const isStable = vol < 0.015;
    return `
      <div class="signal-row">
        <div class="signal-name">${p.name}</div>
        <div class="signal-metrics">
          <span>Volatility ${vol.toFixed(4)}</span>
          <span class="${isStable ? 'sig-stable' : 'sig-break'}">${isStable ? 'Regime Stable' : 'Shift Detected'}</span>
        </div>
      </div>
    `;
  }).join('');
}

async function renderDriftAlerts() {
  const container = document.getElementById('drift-alerts');
  if (!container) return;
  try {
    const res = await apiFetch('/alerts/incidents?page_size=5');
    const incidents = res.items || [];
    if (incidents.length === 0) {
      container.innerHTML = `<div style="color:var(--text3);padding:12px;font-size:12px;">No active alert incidents triggered. System normal.</div>`;
      return;
    }
    container.innerHTML = incidents.map(inc => `
      <div class="drift-row">
        <div class="drift-top">
          <span class="drift-name">${inc.message}</span>
          <span class="drift-pill drift-${inc.severity}">${inc.severity.toUpperCase()}</span>
        </div>
        <div class="drift-meta">
          <span>Triggered: ${new Date(inc.triggered_at).toLocaleTimeString()}</span>
          <span>Metric: ${inc.metric_value.toFixed(4)}</span>
        </div>
      </div>
    `).join('');
  } catch (err) {
    container.innerHTML = `<div style="color:var(--text3);padding:12px;font-size:12px;">Alert system ready. No active incidents.</div>`;
  }
}

function renderParadox() {
  const container = document.getElementById('paradox-list');
  if (!container || protoData.length === 0) return;
  container.innerHTML = protoData.map(p => {
    const ops = Math.round(clamp((p.entropy || 6.0) / 8.0) * 100);
    const gov = Math.round(clamp(p.gini || 0.25) * 100);
    const gap = ops - gov;
    const gapColor = gap > 40 ? '#E24B4A' : gap > 20 ? '#EF9F27' : '#1D9E75';
    return `
      <div class="paradox-item">
        <div class="paradox-meta">
          <span class="paradox-proto">${p.name}</span>
          <span class="paradox-gap" style="color:${gapColor}">Divergence Gap ${gap}pt</span>
        </div>
        <div class="dual-bar">
          <div class="dual-ops" style="width:${ops}%;background:${p.color || '#378ADD'}"></div>
          <div class="dual-gov" style="width:${gov}%"></div>
        </div>
        <div class="dual-labels">
          <span>Operational Usage ${ops}%</span>
          <span>Governance Conc. ${gov}%</span>
        </div>
      </div>
    `;
  }).join('');
}

function renderPrices() {
  const container = document.getElementById('price-list');
  if (!container) return;
  container.innerHTML = tokenPrices.map(t => {
    const chg = ((t.price - t.base) / t.base * 100).toFixed(2);
    const isUp = parseFloat(chg) >= 0;
    return `
      <div class="price-row">
        <div class="price-token">
          <div class="token-icon" style="background:${t.bg};color:${t.fg}">${t.sym.slice(0, 2)}</div>
          <div>
            <div class="tok-name">${t.sym}</div>
            <div class="tok-sub">${t.name}</div>
          </div>
        </div>
        <div class="price-right">
          <div class="price-usd">$${t.price.toFixed(2)}</div>
          <div class="price-chg ${isUp ? 'up' : 'down'}">${isUp ? '▲' : '▼'} ${Math.abs(chg)}%</div>
        </div>
      </div>
    `;
  }).join('');
}

// ── CRUD Actions ────────────────────────────────────────────────────────────
function openAddProtocolModal() {
  document.getElementById('addProtocolModal')?.classList.add('active');
}

function closeAddProtocolModal() {
  document.getElementById('addProtocolModal')?.classList.remove('active');
}

async function submitAddProtocol(e) {
  e.preventDefault();
  const slug = document.getElementById('p-slug').value.trim();
  const name = document.getElementById('p-name').value.trim();
  const symbol = document.getElementById('p-symbol').value.trim();
  const category = document.getElementById('p-category').value;
  const contract = document.getElementById('p-contract').value.trim();
  const description = document.getElementById('p-desc').value.trim();

  try {
    const payload = {
      slug,
      name,
      symbol,
      category,
      contract_address: contract || null,
      description: description || null,
      color: '#378ADD',
    };
    await apiFetch('/protocols', { method: 'POST', body: payload, auth: true });
    showToast(`Protocol ${name} registered successfully!`, 'success');
    closeAddProtocolModal();
    document.getElementById('add-protocol-form')?.reset();
    await fullRefresh();
  } catch (err) {
    showToast(`Failed to register protocol: ${err.message}`, 'error');
  }
}

async function deleteProtocol(id, name) {
  if (!confirm(`Are you sure you want to delete '${name}'? This will remove all its snapshots and data sources.`)) {
    return;
  }
  try {
    await apiFetch(`/protocols/${id}`, { method: 'DELETE', auth: true });
    showToast(`Protocol ${name} removed.`, 'success');
    await fullRefresh();
  } catch (err) {
    showToast(`Error deleting protocol: ${err.message}`, 'error');
  }
}

async function recalculateProtocol(id) {
  try {
    showToast(`Triggering on-chain sync and CDI computation...`, 'info');
    await apiFetch('/snapshots/calculate', {
      method: 'POST',
      body: { protocol_id: id },
      auth: true,
    });
    showToast(`CDI Recalculated!`, 'success');
    await fullRefresh();
  } catch (err) {
    showToast(`Recalculation error: ${err.message}`, 'error');
  }
}

async function triggerSyncJob() {
  try {
    showToast(`Submitting global data sync batch job...`, 'info');
    const job = await apiFetch('/jobs', {
      method: 'POST',
      body: { job_type: 'ingestion' },
      auth: true,
    });
    showToast(`Batch Sync Job completed (ID: ${job.id.slice(0, 8)})`, 'success');
    await fullRefresh();
  } catch (err) {
    showToast(`Job trigger error: ${err.message}`, 'error');
  }
}

// ── Alert Rule Modal ────────────────────────────────────────────────────────
function openAddAlertModal() {
  document.getElementById('addAlertModal')?.classList.add('active');
}

function closeAddAlertModal() {
  document.getElementById('addAlertModal')?.classList.remove('active');
}

async function submitAddAlert(e) {
  e.preventDefault();
  const name = document.getElementById('a-name').value.trim();
  const metric_name = document.getElementById('a-metric').value;
  const condition = document.getElementById('a-cond').value;
  const threshold = parseFloat(document.getElementById('a-thresh').value);
  const severity = document.getElementById('a-sev').value;

  try {
    await apiFetch('/alerts/rules', {
      method: 'POST',
      body: { name, metric_name, condition, threshold, severity },
      auth: true,
    });
    showToast(`Alert rule '${name}' created!`, 'success');
    closeAddAlertModal();
    document.getElementById('add-alert-form')?.reset();
    await renderDriftAlerts();
  } catch (err) {
    showToast(`Error creating alert: ${err.message}`, 'error');
  }
}

// ── Sensitivity Lab ─────────────────────────────────────────────────────────
function updateSensitivityDropdown() {
  const sel = document.getElementById('sens-protocol');
  if (!sel) return;
  const currVal = sel.value;
  sel.innerHTML = protoData.map(p => `<option value="${p.id}" ${p.id == currVal ? 'selected' : ''}>${p.name} (${p.symbol})</option>`).join('');
}

function updateSliders() {
  const eco = parseInt(document.getElementById('slider-w-eco')?.value || 25);
  const gov = parseInt(document.getElementById('slider-w-gov')?.value || 25);
  const str = parseInt(document.getElementById('slider-w-struct')?.value || 25);
  const dev = parseInt(document.getElementById('slider-w-dev')?.value || 25);

  document.getElementById('val-w-eco').textContent = `${eco}%`;
  document.getElementById('val-w-gov').textContent = `${gov}%`;
  document.getElementById('val-w-struct').textContent = `${str}%`;
  document.getElementById('val-w-dev').textContent = `${dev}%`;
}

async function runSensitivityAnalysis() {
  const protoId = parseInt(document.getElementById('sens-protocol')?.value);
  if (!protoId) {
    showToast('Select a valid protocol', 'error');
    return;
  }

  const eco = parseInt(document.getElementById('slider-w-eco').value) / 100.0;
  const gov = parseInt(document.getElementById('slider-w-gov').value) / 100.0;
  const str = parseInt(document.getElementById('slider-w-struct').value) / 100.0;
  const dev = parseInt(document.getElementById('slider-w-dev').value) / 100.0;

  try {
    const payload = {
      protocol_id: protoId,
      scenarios: {
        custom_weights: { economic: eco, governance: gov, structural: str, development: dev },
        equal_weights: { economic: 0.25, governance: 0.25, structural: 0.25, development: 0.25 },
        governance_priority: { economic: 0.10, governance: 0.60, structural: 0.15, development: 0.15 },
        economic_priority: { economic: 0.60, governance: 0.15, structural: 0.15, development: 0.10 },
      }
    };
    const res = await apiFetch('/snapshots/sensitivity', { method: 'POST', body: payload });
    const out = document.getElementById('sens-output-content');
    if (out) {
      out.innerHTML = `
        <div style="font-size:13px;color:var(--text);margin-bottom:8px;">
          <strong>Baseline CDI:</strong> ${res.baseline_cdi.toFixed(4)} | 
          <strong>Cross-Scenario Variance:</strong> ${res.variance.toFixed(6)}
        </div>
        <table class="proto-table" style="font-size:12px;">
          <thead><tr><th>Scenario</th><th>Simulated CDI</th><th>Deviation</th></tr></thead>
          <tbody>
            ${Object.entries(res.scenario_results).map(([k, v]) => {
              const diff = v - res.baseline_cdi;
              return `<tr>
                <td><strong>${k.replace('_', ' ').toUpperCase()}</strong></td>
                <td>${v.toFixed(4)}</td>
                <td style="color:${diff >= 0 ? 'var(--success)' : 'var(--danger)'}">${diff >= 0 ? '+' : ''}${diff.toFixed(4)}</td>
              </tr>`;
            }).join('')}
          </tbody>
        </table>
      `;
    }
    showToast('Sensitivity analysis completed!', 'success');
  } catch (err) {
    showToast(`Sensitivity run error: ${err.message}`, 'error');
  }
}

// ── Refresh Cycle & Bootstrap ───────────────────────────────────────────────
async function fullRefresh() {
  await checkBackendHealth();
  await fetchOverviewMetrics();
  await fetchHistoricalSeries();

  const updateTime = document.getElementById('last-update-time');
  if (updateTime) {
    updateTime.textContent = new Date().toLocaleTimeString('en-US', {
      hour: '2-digit', minute: '2-digit', second: '2-digit',
    });
  }
  countdown = refreshInterval;
}

const RING_CIRC = 87.96;
function updateRing() {
  const frac = countdown / refreshInterval;
  const offset = RING_CIRC * (1 - frac);
  const ring = document.getElementById('ring-circle');
  const countEl = document.getElementById('countdown-num');
  if (ring) ring.setAttribute('stroke-dashoffset', offset.toFixed(2));
  if (countEl) countEl.textContent = countdown;
}

function startCountdown() {
  if (countdownTimer) clearInterval(countdownTimer);
  countdown = refreshInterval;
  countdownTimer = setInterval(() => {
    countdown = Math.max(0, countdown - 1);
    updateRing();
    if (countdown === 0) {
      fullRefresh();
      countdown = refreshInterval;
    }
  }, 1000);
}

function setRefreshInterval(val) {
  refreshInterval = parseInt(val);
  startCountdown();
}

function tickPrices() {
  tokenPrices = tokenPrices.map(t => {
    const newP = Math.max(t.base * 0.5, t.price * (1 + (Math.random() - 0.5) * 0.007));
    return { ...t, prevPrice: t.price, price: newP, hist: [...t.hist.slice(1), newP] };
  });
  renderPrices();
}

function setupNavHighlight() {
  const sections = ['overview', 'protocols', 'sensitivity', 'alerts', 'prices', 'paradox'];
  const items = document.querySelectorAll('.nav-item');
  window.addEventListener('scroll', () => {
    let current = sections[0];
    sections.forEach(id => {
      const el = document.getElementById(id);
      if (el && el.getBoundingClientRect().top < 180) current = id;
    });
    items.forEach(item => {
      const href = item.getAttribute('href');
      if (href && href.startsWith('#')) {
        item.classList.toggle('active', href === '#' + current);
      }
    });
  }, { passive: true });
}

document.addEventListener('DOMContentLoaded', async () => {
  setupNavHighlight();
  await fullRefresh();
  renderPrices();
  startCountdown();
  priceTimer = setInterval(tickPrices, 4000);
});
