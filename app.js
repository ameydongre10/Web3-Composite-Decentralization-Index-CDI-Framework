'use strict';

// ── State ──────────────────────────────────────────────────────────────────
const PROTOCOL_META = [
  { id:'uniswap', name:'Uniswap v3', tag:'DEX',    color:'#378ADD', dash:[]        },
  { id:'aave',    name:'Aave v3',    tag:'Lending', color:'#1D9E75', dash:[6,3]     },
  { id:'sushi',   name:'SushiSwap',  tag:'DEX',     color:'#EF9F27', dash:[3,3]     },
  { id:'curve',   name:'Curve',      tag:'AMM',     color:'#D85A30', dash:[8,4]     },
  { id:'compound',name:'Compound',   tag:'Lending', color:'#7F77DD', dash:[5,2]     },
];

const BASE_DATA = {
  uniswap:  { gini:0.22, hhi:2150, entropy:6.42, delegationCent:0.43, blocCluster:0.41, structural:0.62, development:0.58 },
  aave:     { gini:0.25, hhi:2300, entropy:6.20, delegationCent:0.48, blocCluster:0.44, structural:0.59, development:0.63 },
  sushi:    { gini:0.20, hhi:1950, entropy:6.55, delegationCent:0.37, blocCluster:0.35, structural:0.64, development:0.52 },
  curve:    { gini:0.18, hhi:1800, entropy:6.70, delegationCent:0.34, blocCluster:0.33, structural:0.66, development:0.50 },
  compound: { gini:0.24, hhi:2200, entropy:6.30, delegationCent:0.45, blocCluster:0.42, structural:0.57, development:0.56 },
};

const DIMENSIONS = [
  { key: 'economic', label: 'Economic Decentralization', color: '#378ADD' },
  { key: 'governance', label: 'Governance Decentralization', color: '#EF9F27' },
  { key: 'structural', label: 'Structural Network Decentralization', color: '#1D9E75' },
  { key: 'development', label: 'Development Decentralization', color: '#D85A30' },
];

const PIPELINE_STEPS = [
  'Data Ingestion',
  'Feature Engineering',
  'Graph Construction',
  'Metric Computation',
  'Weight Learning Engine',
  'Temporal Modeling',
  'Risk Prediction',
  'Dashboard / API',
];

const TOKEN_META = [
  { sym:'UNI',  name:'Uniswap',   base:7.82,  color:'#378ADD', bg:'#0d2440', fg:'#5aadff' },
  { sym:'AAVE', name:'Aave',      base:88.40, color:'#1D9E75', bg:'#0d2b22', fg:'#3dd6a3' },
  { sym:'SUSHI',name:'SushiSwap', base:1.12,  color:'#EF9F27', bg:'#2b200a', fg:'#f5b94d' },
  { sym:'CRV',  name:'Curve',     base:0.34,  color:'#D85A30', bg:'#2b150a', fg:'#f58a60' },
  { sym:'COMP', name:'Compound',  base:44.10, color:'#7F77DD', bg:'#1e1b3a', fg:'#aaa4f5' },
];

let protoData = PROTOCOL_META.map(p => ({
  ...p,
  ...BASE_DATA[p.id],
  scores: { economic: 0, governance: 0, structural: 0, development: 0 },
  cdi: 0,
}));

let dynamicWeights = { economic: 0.25, governance: 0.25, structural: 0.25, development: 0.25 };

let tokenPrices = TOKEN_META.map(t => ({
  ...t,
  price: t.base,
  prevPrice: t.base,
  hist: Array.from({length:24}, () => t.base * (1 + (Math.random()-.5)*.04)),
}));

let visible = Object.fromEntries(PROTOCOL_META.map(p => [p.id, true]));
let cdiChart = null;
let radarChart = null;
let centralityChart = null;
let cdiSeries = {};
let refreshInterval = 30;
let countdown = 30;
let countdownTimer = null;
let priceTimer = null;
let ganacheProvider = null;
let ganacheConnected = false;
let latestGanacheSample = null;
let latestGanacheMeta = null;
let graphXPollingTimer = null;

const GANACHE_RPC_URLS = [
  'http://127.0.0.1:7545',
  'http://127.0.0.1:8545',
];

// ── Helpers ─────────────────────────────────────────────────────────────────
function jitter(v, pct = 0.018) {
  return parseFloat((v + (Math.random() - 0.5) * v * pct * 2).toFixed(4));
}

function clamp(v, min = 0, max = 1) {
  return Math.max(min, Math.min(max, v));
}

function sigmoid(x) {
  return 1 / (1 + Math.exp(-x));
}

function mean(arr) {
  return arr.reduce((s, x) => s + x, 0) / arr.length;
}

function stdev(arr) {
  if (arr.length < 2) return 0;
  const m = mean(arr);
  return Math.sqrt(arr.reduce((s, x) => s + (x - m) ** 2, 0) / (arr.length - 1));
}

function genSeries(baseVal, n = 90) {
  let v = baseVal;
  return Array.from({length: n}, () => {
    v = Math.max(0.35, Math.min(0.55, v + (Math.random() - 0.5) * 0.007));
    return parseFloat(v.toFixed(4));
  });
}

function dateLabels(n = 90) {
  return Array.from({length: n}, (_, i) => {
    const d = new Date(2024, 0, 1);
    d.setDate(d.getDate() + i);
    return i % 14 === 0
      ? d.toLocaleDateString('en-US', {month:'short', day:'numeric'})
      : '';
  });
}

function riskLabel(cdi) {
  if (cdi < 0.42) return ['High', 'risk-high'];
  if (cdi < 0.52) return ['Mod', 'risk-mod'];
  return ['Low', 'risk-low'];
}

function fmt(n, dec = 3) { return parseFloat(n).toFixed(dec); }

function setGanacheStatus(connected, text) {
  ganacheConnected = connected;
  const el = document.getElementById('ganache-status');
  if (!el) return;
  el.textContent = text;
  el.classList.toggle('online', connected);
  el.classList.toggle('offline', !connected);
}

function setGraphXStatus(ok, text) {
  const el = document.getElementById('graphx-status');
  if (!el) return;
  el.textContent = text;
  el.classList.toggle('online', ok);
  el.classList.toggle('offline', !ok);
}

function setGraphXValueDisplay(value, timestamp, latencyMs) {
  const valueEl = document.getElementById('graphx-value');
  const tsEl = document.getElementById('graphx-timestamp');
  const latEl = document.getElementById('graphx-latency');
  if (valueEl) valueEl.textContent = value;
  if (tsEl) tsEl.textContent = timestamp || '-';
  if (latEl) latEl.textContent = latencyMs != null ? `${latencyMs} ms` : '-';
}

function extractGraphXValue(payload) {
  if (payload == null) return null;
  if (typeof payload === 'number') return payload;
  if (typeof payload === 'string' && payload.trim() !== '' && !Number.isNaN(Number(payload))) return Number(payload);

  const candidateKeys = ['value', 'graphxValue', 'score', 'metric', 'data'];
  for (const k of candidateKeys) {
    const v = payload[k];
    if (typeof v === 'number') return v;
    if (typeof v === 'string' && v.trim() !== '' && !Number.isNaN(Number(v))) return Number(v);
    if (v && typeof v === 'object' && typeof v.value === 'number') return v.value;
  }

  return null;
}

async function fetchGraphXValue() {
  const endpointEl = document.getElementById('graphx-endpoint');
  const keyEl = document.getElementById('graphx-api-key');
  if (!endpointEl) return;

  const endpoint = endpointEl.value.trim();
  const apiKey = keyEl ? keyEl.value.trim() : '';
  if (!endpoint) {
    setGraphXStatus(false, 'GraphX: Missing endpoint');
    return;
  }

  setGraphXStatus(false, 'GraphX: Fetching...');
  const started = performance.now();

  try {
    const headers = { 'Accept': 'application/json' };
    if (apiKey) headers.Authorization = `Bearer ${apiKey}`;

    const res = await fetch(endpoint, { method: 'GET', headers });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    const payload = await res.json();
    const value = extractGraphXValue(payload);
    if (value == null) throw new Error('No numeric value in GraphX response');

    const latency = Math.round(performance.now() - started);
    const ts = payload.timestamp || payload.updatedAt || new Date().toISOString();
    setGraphXValueDisplay(Number(value).toFixed(4), ts, latency);
    setGraphXStatus(true, 'GraphX: Connected');
  } catch (err) {
    setGraphXStatus(false, `GraphX: ${String(err.message || 'Fetch failed')}`);
    setGraphXValueDisplay('-', '-', null);
  }
}

function setMetaValue(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

function renderGanacheMeta(meta) {
  const m = meta || latestGanacheMeta;
  if (!m) {
    setMetaValue('meta-block', '-');
    setMetaValue('meta-gas-price', '-');
    setMetaValue('meta-gas-limit', '-');
    setMetaValue('meta-hardfork', '-');
    setMetaValue('meta-network-id', '-');
    setMetaValue('meta-rpc', '-');
    setMetaValue('meta-mining', '-');
    return;
  }

  setMetaValue('meta-block', String(m.currentBlock));
  setMetaValue('meta-gas-price', String(m.gasPrice));
  setMetaValue('meta-gas-limit', String(m.gasLimit));
  setMetaValue('meta-hardfork', m.hardfork || 'MERGE');
  setMetaValue('meta-network-id', String(m.networkId));
  setMetaValue('meta-rpc', m.rpcServer);
  setMetaValue('meta-mining', m.mining ? 'AUTOMINING' : 'STOPPED');
}

async function tryGanacheProvider(url) {
  const provider = new ethers.JsonRpcProvider(url, undefined, { staticNetwork: true });
  const net = await provider.getNetwork();
  if (!net || net.chainId <= 0n) throw new Error('No chain id');
  return provider;
}

async function sampleGanacheData() {
  if (!ganacheProvider) return null;

  const blockNumber = await ganacheProvider.getBlockNumber();
  const latestBlock = await ganacheProvider.getBlock(blockNumber, true);
  const txCount = latestBlock && latestBlock.transactions ? latestBlock.transactions.length : 0;

  const accounts = await ganacheProvider.listAccounts();
  const balances = await Promise.all(accounts.slice(0, 10).map(a => ganacheProvider.getBalance(a.address || a)));
  const balanceNums = balances.map(v => Number(ethers.formatEther(v)));
  const totalBalance = balanceNums.reduce((s, v) => s + v, 0) || 1;
  const topShare = balanceNums.sort((a, b) => b - a).slice(0, 3).reduce((s, v) => s + v, 0) / totalBalance;

  return {
    blockNumber,
    txCount,
    accountCount: accounts.length,
    topShare: clamp(topShare, 0, 1),
  };
}

async function fetchGanacheMeta(url) {
  if (!ganacheProvider) return null;

  const [
    blockHex,
    gasPriceHex,
    mining,
    networkId,
    latestBlock,
    clientVersion,
  ] = await Promise.all([
    ganacheProvider.send('eth_blockNumber', []),
    ganacheProvider.send('eth_gasPrice', []),
    ganacheProvider.send('eth_mining', []),
    ganacheProvider.send('net_version', []),
    ganacheProvider.send('eth_getBlockByNumber', ['latest', false]),
    ganacheProvider.send('web3_clientVersion', []),
  ]);

  const currentBlock = parseInt(blockHex, 16);
  const gasPrice = BigInt(gasPriceHex).toString();
  const gasLimit = latestBlock && latestBlock.gasLimit ? parseInt(latestBlock.gasLimit, 16).toString() : '-';
  const inferredHardfork = /merge|paris/i.test(String(clientVersion)) ? 'MERGE' : 'MERGE';

  return {
    currentBlock,
    gasPrice,
    gasLimit,
    hardfork: inferredHardfork,
    networkId,
    rpcServer: String(url).toUpperCase(),
    mining: Boolean(mining),
  };
}

function applyGanacheSample(sample) {
  if (!sample) return;
  latestGanacheSample = sample;

  // Map local chain concentration/activity into feature priors.
  const txSignal = clamp(sample.txCount / 40, 0, 1);
  const acctSignal = clamp(sample.accountCount / 20, 0, 1);
  const concentration = sample.topShare;

  protoData = protoData.map((p, i) => {
    const offset = (i - 2) * 0.007;
    return {
      ...p,
      gini: clamp(0.16 + 0.22 * concentration + 0.03 * (1 - acctSignal) + offset, 0.05, 0.9),
      hhi: Math.round(clamp(1600 + concentration * 2800 + (1 - txSignal) * 450 + i * 25, 1200, 5000)),
      entropy: clamp(5.8 + txSignal * 1.1 + acctSignal * 0.7 - concentration * 0.9 + offset, 3.2, 7.8),
      delegationCent: clamp(0.25 + concentration * 0.5 + 0.06 * i),
      blocCluster: clamp(0.24 + concentration * 0.52 + 0.03 * (4 - i)),
      structural: clamp(0.52 + txSignal * 0.24 - concentration * 0.18 - 0.01 * i),
      development: clamp(0.50 + acctSignal * 0.21 - concentration * 0.08 + 0.01 * i),
    };
  });
}

async function connectGanache() {
  setGanacheStatus(false, 'Ganache: Connecting...');
  renderGanacheMeta(null);

  for (const url of GANACHE_RPC_URLS) {
    try {
      ganacheProvider = await tryGanacheProvider(url);
      const sample = await sampleGanacheData();
      const meta = await fetchGanacheMeta(url);
      applyGanacheSample(sample);
      recomputeModelState();
      latestGanacheMeta = meta;
      renderGanacheMeta(meta);
      fullRefresh();
      setGanacheStatus(true, `Ganache: Connected (${url})`);
      return;
    } catch (err) {
      // Try next port.
    }
  }

  ganacheProvider = null;
  latestGanacheSample = null;
  latestGanacheMeta = null;
  setGanacheStatus(false, 'Ganache: Offline (start node at 7545/8545)');
  renderGanacheMeta(null);
}

function computeDimensionScores(p) {
  const wealthEntropy = clamp(p.entropy / 8);
  const giniBalance = clamp(1 - p.gini);
  const hhiBalance = clamp(1 - p.hhi / 10000);

  const economic = clamp(
    0.45 * giniBalance +
    0.30 * wealthEntropy +
    0.25 * hhiBalance
  );

  const governance = clamp(
    0.45 * hhiBalance +
    0.25 * wealthEntropy +
    0.30 * (1 - p.delegationCent)
  );

  const structural = clamp(
    0.55 * p.structural +
    0.25 * (1 - p.blocCluster) +
    0.20 * wealthEntropy
  );

  const development = clamp(
    0.70 * p.development +
    0.30 * (1 - p.gini)
  );

  return { economic, governance, structural, development };
}

function computeAdaptiveWeights(protocols) {
  const n = protocols.length;
  const k = 1 / Math.log(n);
  const eps = 1e-9;
  const diversities = {};

  DIMENSIONS.forEach(d => {
    const vals = protocols.map(p => clamp(p.scores[d.key], 0.0001, 0.9999));
    const total = vals.reduce((s, v) => s + v, 0);
    const probs = vals.map(v => v / total);
    const entropy = -k * probs.reduce((s, p) => s + p * Math.log(p + eps), 0);
    diversities[d.key] = Math.max(0.0001, 1 - entropy);
  });

  const sumD = Object.values(diversities).reduce((s, x) => s + x, 0);
  const out = {};
  DIMENSIONS.forEach(d => {
    out[d.key] = diversities[d.key] / sumD;
  });

  return out;
}

function recomputeModelState() {
  protoData = protoData.map(p => ({ ...p, scores: computeDimensionScores(p) }));
  dynamicWeights = computeAdaptiveWeights(protoData);
  protoData = protoData.map(p => {
    const cdi = DIMENSIONS.reduce((s, d) => s + dynamicWeights[d.key] * p.scores[d.key], 0);
    return { ...p, cdi: clamp(cdi, 0.30, 0.90) };
  });
}

// ── Init time series ─────────────────────────────────────────────────────────
recomputeModelState();
PROTOCOL_META.forEach(p => {
  const proto = protoData.find(x => x.id === p.id);
  cdiSeries[p.id] = genSeries(proto ? proto.cdi : 0.45);
});

// ── Charts ──────────────────────────────────────────────────────────────────
function buildCDIChart() {
  const ctx = document.getElementById('cdiChart');
  const datasets = PROTOCOL_META.map(p => ({
    label: p.name,
    data: cdiSeries[p.id],
    borderColor: p.color,
    backgroundColor: 'transparent',
    borderWidth: 1.5,
    borderDash: p.dash,
    pointRadius: 0,
    tension: 0.4,
    hidden: !visible[p.id],
  }));

  cdiChart = new Chart(ctx, {
    type: 'line',
    data: { labels: dateLabels(), datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 400 },
      plugins: {
        legend: { display: false },
        tooltip: {
          mode: 'index',
          intersect: false,
          backgroundColor: '#1a1d32',
          borderColor: 'rgba(255,255,255,0.12)',
          borderWidth: 1,
          titleColor: '#9095b0',
          bodyColor: '#e8eaf0',
          padding: 10,
          callbacks: {
            label: ctx => ` ${ctx.dataset.label}: ${ctx.parsed.y.toFixed(3)}`
          }
        }
      },
      scales: {
        x: {
          grid: { color: 'rgba(255,255,255,0.04)' },
          ticks: { color: '#5a5f7a', font: {size:10}, maxRotation: 0 }
        },
        y: {
          min: 0.32, max: 0.58,
          grid: { color: 'rgba(255,255,255,0.04)' },
          ticks: { color: '#5a5f7a', font: {size:10}, callback: v => v.toFixed(2) }
        }
      },
      interaction: { mode:'index', intersect:false }
    }
  });
}

function buildRadarChart() {
  const ctx = document.getElementById('radarChart');
  const labels = ['Economic', 'Governance', 'Structural', 'Development'];

  const datasets = protoData.map(p => ({
    label: p.name,
    data: [
      parseFloat(p.scores.economic.toFixed(3)),
      parseFloat(p.scores.governance.toFixed(3)),
      parseFloat(p.scores.structural.toFixed(3)),
      parseFloat(p.scores.development.toFixed(3)),
    ],
    borderColor: p.color,
    backgroundColor: p.color + '22',
    borderWidth: 1.5,
    pointRadius: 3,
    pointBackgroundColor: p.color,
  }));

  radarChart = new Chart(ctx, {
    type: 'radar',
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 400 },
      plugins: { legend: { display: false } },
      scales: {
        r: {
          min: 0, max: 1,
          grid: { color: 'rgba(255,255,255,0.07)' },
          angleLines: { color: 'rgba(255,255,255,0.07)' },
          pointLabels: { color: '#9095b0', font: {size: 11} },
          ticks: { display: false, stepSize: 0.25 }
        }
      }
    }
  });
}

// ── Protocol toggles ─────────────────────────────────────────────────────────
function buildProtoToggles() {
  const wrap = document.getElementById('proto-btns');
  const legend = document.getElementById('chart-legend');
  wrap.innerHTML = PROTOCOL_META.map(p => `
    <button
      class="proto-btn active"
      style="--pc:${p.color}"
      data-id="${p.id}"
      onclick="toggleProto('${p.id}', this)"
    >${p.name}</button>
  `).join('');

  legend.innerHTML = PROTOCOL_META.map(p => `
    <div class="legend-item">
      <div class="legend-dot" style="background:${p.color}"></div>
      <span>${p.name}</span>
    </div>
  `).join('');
}

function toggleProto(id, btn) {
  visible[id] = !visible[id];
  btn.classList.toggle('active', visible[id]);
  cdiChart.data.datasets.forEach(ds => {
    const meta = PROTOCOL_META.find(p => p.name === ds.label);
    if (meta && meta.id === id) ds.hidden = !visible[id];
  });
  cdiChart.update();
}

// ── Render protocol table ────────────────────────────────────────────────────
function renderProtoTable() {
  const sorted = [...protoData].sort((a, b) => b.cdi - a.cdi);
  document.getElementById('proto-rows').innerHTML = sorted.map((p, i) => {
    const [rl, rc] = riskLabel(p.cdi);
    const barW = Math.round(p.cdi * 100);
    return `
      <tr>
        <td><span class="rank-num">${i + 1}</span></td>
        <td>
          <div class="proto-name-cell">
            <div class="name">${p.name}</div>
            <div class="tag">${p.tag}</div>
          </div>
        </td>
        <td>
          <div class="cdi-cell">
            <div class="cdi-bar-bg">
              <div class="cdi-bar-fg" style="width:${barW}%;background:${p.color}"></div>
            </div>
            <span class="cdi-num">${fmt(p.cdi)}</span>
          </div>
        </td>
        <td><span class="gini-num">${fmt(p.gini)}</span></td>
        <td><span class="entropy-num">${fmt(p.entropy, 2)}</span></td>
        <td><span class="risk-pill ${rc}">${rl}</span></td>
      </tr>`;
  }).join('');
}

function renderDimensionScoreGrid() {
  const avgByDim = {};
  DIMENSIONS.forEach(d => {
    avgByDim[d.key] = protoData.reduce((s, p) => s + p.scores[d.key], 0) / protoData.length;
  });

  document.getElementById('dimension-score-grid').innerHTML = DIMENSIONS.map(d => {
    const val = avgByDim[d.key];
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

function renderWeightList() {
  document.getElementById('weight-list').innerHTML = DIMENSIONS.map(d => {
    const w = dynamicWeights[d.key] || 0;
    return `
      <div class="weight-row">
        <div class="weight-label">
          <span class="dim-dot" style="background:${d.color}"></span>
          <span>${d.label}</span>
        </div>
        <div class="weight-value">w(t) = ${fmt(w)}</div>
        <div class="weight-bar"><div class="weight-fill" style="width:${Math.round(w * 100)}%;background:${d.color}"></div></div>
      </div>
    `;
  }).join('');
}

function computeTemporalStats(series) {
  const last30 = series.slice(-30);
  const diffs = last30.slice(1).map((v, i) => v - last30[i]);
  const volatility = stdev(diffs);
  const changePoints = diffs.filter(d => Math.abs(d) > 0.012).length;

  const prev = series.slice(-20, -10);
  const curr = series.slice(-10);
  const breakMagnitude = Math.abs(mean(curr) - mean(prev));
  const structuralBreak = breakMagnitude > 0.015;

  return { volatility, changePoints, structuralBreak, breakMagnitude };
}

function renderTemporalSignals() {
  const rows = PROTOCOL_META.map(meta => {
    const s = cdiSeries[meta.id];
    const t = computeTemporalStats(s);
    return { ...meta, ...t };
  });

  document.getElementById('temporal-signals').innerHTML = rows.map(r => `
    <div class="signal-row">
      <div class="signal-name">${r.name}</div>
      <div class="signal-metrics">
        <span>Volatility ${fmt(r.volatility, 4)}</span>
        <span>Change-points ${r.changePoints}</span>
        <span class="${r.structuralBreak ? 'sig-break' : 'sig-stable'}">${r.structuralBreak ? 'Break detected' : 'Stable regime'}</span>
      </div>
    </div>
  `).join('');
}

function governanceConcentrationMetrics(p) {
  return {
    votingHHI: clamp(p.hhi / 5000),
    delegationCentrality: clamp(p.delegationCent),
    blocClustering: clamp(p.blocCluster),
  };
}

function heatColor(v) {
  const x = clamp(v);
  const alpha = 0.16 + x * 0.64;
  return `rgba(226,75,74,${alpha.toFixed(3)})`;
}

function renderGovernanceHeatmap() {
  const headers = ['Protocol', 'Voting HHI', 'Delegation Centrality', 'Bloc Clustering'];
  const rows = protoData.map(p => {
    const m = governanceConcentrationMetrics(p);
    return { p, vals: [m.votingHHI, m.delegationCentrality, m.blocClustering] };
  });

  const head = `<div class="heat-row heat-head">${headers.map(h => `<div class="heat-cell">${h}</div>`).join('')}</div>`;
  const body = rows.map(r => `
    <div class="heat-row">
      <div class="heat-cell heat-proto">${r.p.name}</div>
      ${r.vals.map(v => `<div class="heat-cell heat-value" style="background:${heatColor(v)}">${fmt(v, 3)}</div>`).join('')}
    </div>
  `).join('');

  document.getElementById('gov-heatmap').innerHTML = head + body;
}

function buildCentralityDistribution(p) {
  const concentration = clamp(0.45 * p.delegationCent + 0.35 * p.blocCluster + 0.20 * (p.hhi / 5000));
  const percentiles = [10,20,30,40,50,60,70,80,90,100];
  return percentiles.map(q => {
    const n = q / 100;
    const skew = 0.65 + concentration;
    const share = clamp((1 - Math.pow(1 - n, skew)) * (0.55 + concentration * 0.45));
    return parseFloat(share.toFixed(3));
  });
}

function buildCentralityChart() {
  const ctx = document.getElementById('centralityChart');
  const labels = ['P10','P20','P30','P40','P50','P60','P70','P80','P90','P100'];
  const datasets = protoData.map(p => ({
    label: p.name,
    data: buildCentralityDistribution(p),
    borderColor: p.color,
    backgroundColor: 'transparent',
    pointRadius: 1.8,
    borderWidth: 1.6,
    tension: 0.35,
  }));

  centralityChart = new Chart(ctx, {
    type: 'line',
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 400 },
      plugins: {
        legend: { display: false },
        tooltip: {
          mode: 'index',
          intersect: false,
          callbacks: { label: x => ` ${x.dataset.label}: ${x.parsed.y.toFixed(3)}` }
        }
      },
      interaction: { mode: 'index', intersect: false },
      scales: {
        x: {
          grid: { color: 'rgba(255,255,255,0.04)' },
          ticks: { color: '#5a5f7a', font: { size: 10 } },
          title: { display: true, text: 'Percentile Band', color: '#9095b0', font: { size: 10 } },
        },
        y: {
          min: 0,
          max: 1,
          grid: { color: 'rgba(255,255,255,0.04)' },
          ticks: { color: '#5a5f7a', font: { size: 10 } },
          title: { display: true, text: 'Centrality Share', color: '#9095b0', font: { size: 10 } },
        }
      }
    }
  });
}

function updateCentralityChart() {
  if (!centralityChart) return;
  centralityChart.data.datasets.forEach(ds => {
    const p = protoData.find(x => x.name === ds.label);
    if (p) ds.data = buildCentralityDistribution(p);
  });
  centralityChart.update('none');
}

function computeDriftAlerts() {
  return PROTOCOL_META.map(meta => {
    const series = cdiSeries[meta.id];
    const recent = series.slice(-30);
    const older = series.slice(-60, -30);
    const recentMean = mean(recent);
    const olderMean = mean(older);
    const drift = recentMean - olderMean;
    const temporal = computeTemporalStats(series);
    const sev = clamp(
      0.55 * (0.5 - recentMean) +
      0.30 * Math.max(0, -drift) * 10 +
      0.15 * (temporal.volatility * 50)
    );

    let label = 'Info';
    if (sev >= 0.70) label = 'Critical';
    else if (sev >= 0.50) label = 'Warning';
    else if (sev >= 0.35) label = 'Watch';

    return {
      ...meta,
      recentMean,
      drift,
      sev,
      label,
      changePoints: temporal.changePoints,
    };
  }).sort((a, b) => b.sev - a.sev);
}

function renderDriftAlerts() {
  const alerts = computeDriftAlerts();
  document.getElementById('drift-alerts').innerHTML = alerts.map(a => `
    <div class="drift-row">
      <div class="drift-top">
        <span class="drift-name">${a.name}</span>
        <span class="drift-pill drift-${a.label.toLowerCase()}">${a.label}</span>
      </div>
      <div class="drift-meta">
        <span>Current CDI mean ${fmt(a.recentMean)}</span>
        <span>30d drift ${a.drift >= 0 ? '+' : ''}${fmt(a.drift, 4)}</span>
        <span>Change-points ${a.changePoints}</span>
      </div>
      <div class="drift-bar"><div class="drift-fill" style="width:${Math.round(a.sev * 100)}%"></div></div>
    </div>
  `).join('');
}

function riskScores(p) {
  const cRisk = sigmoid(
    5.0 * (0.52 - p.cdi) +
    2.1 * (p.gini - 0.2) +
    1.2 * ((p.hhi - 1900) / 1000)
  );

  const gRisk = sigmoid(
    4.2 * (0.50 - p.scores.governance) +
    2.4 * p.delegationCent +
    1.7 * p.blocCluster
  );

  const cartel = sigmoid(
    3.7 * (0.52 - p.scores.structural) +
    1.8 * p.blocCluster +
    1.4 * (0.55 - p.scores.economic)
  );

  return {
    centralization: clamp(cRisk),
    governanceCapture: clamp(gRisk),
    cartelFormation: clamp(cartel),
  };
}

function renderRiskForecast() {
  const sorted = [...protoData].sort((a, b) => riskScores(b).centralization - riskScores(a).centralization);
  document.getElementById('risk-forecast').innerHTML = sorted.map(p => {
    const r = riskScores(p);
    const composite = clamp(0.40 * r.centralization + 0.35 * r.governanceCapture + 0.25 * r.cartelFormation);
    return `
      <div class="forecast-row">
        <div class="forecast-top">
          <span class="forecast-name">${p.name}</span>
          <span class="forecast-cdi">CDI ${fmt(p.cdi)}</span>
        </div>
        <div class="forecast-metric strong">
          <span>Risk score (0-1)</span>
          <span>${fmt(composite, 3)}</span>
        </div>
        <div class="forecast-bar"><div class="forecast-fill neutral" style="width:${Math.round(composite * 100)}%"></div></div>
        <div class="forecast-metric">
          <span>Centralization risk</span>
          <span>${Math.round(r.centralization * 100)}%</span>
        </div>
        <div class="forecast-bar"><div class="forecast-fill danger" style="width:${Math.round(r.centralization * 100)}%"></div></div>
        <div class="forecast-metric">
          <span>Governance capture</span>
          <span>${Math.round(r.governanceCapture * 100)}%</span>
        </div>
        <div class="forecast-bar"><div class="forecast-fill warning" style="width:${Math.round(r.governanceCapture * 100)}%"></div></div>
        <div class="forecast-metric">
          <span>Cartel formation</span>
          <span>${Math.round(r.cartelFormation * 100)}%</span>
        </div>
        <div class="forecast-bar"><div class="forecast-fill accent" style="width:${Math.round(r.cartelFormation * 100)}%"></div></div>
      </div>
    `;
  }).join('');
}

function renderPipelineFlow() {
  document.getElementById('pipeline-flow').innerHTML = PIPELINE_STEPS.map((step, i) => `
    <div class="pipe-step-wrap">
      <div class="pipe-step">
        <span class="pipe-index">${i + 1}</span>
        <span>${step}</span>
      </div>
      ${i < PIPELINE_STEPS.length - 1 ? '<div class="pipe-arrow">↓</div>' : ''}
    </div>
  `).join('');
}

// ── Render prices ───────────────────────────────────────────────────────────
function buildSparkPath(hist) {
  const mn = Math.min(...hist), mx = Math.max(...hist), rng = mx - mn || 0.001;
  return hist.map((v, i) => {
    const x = (i / (hist.length - 1)) * 86 + 1;
    const y = 28 - ((v - mn) / rng) * 24;
    return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)} ${y.toFixed(1)}`;
  }).join(' ');
}

function renderPrices() {
  document.getElementById('price-list').innerHTML = tokenPrices.map(t => {
    const chg = ((t.price - t.base) / t.base * 100).toFixed(2);
    const isUp = parseFloat(chg) >= 0;
    const spark = buildSparkPath(t.hist);
    const fmtPrice = t.price < 1
      ? t.price.toFixed(4)
      : t.price < 10
        ? t.price.toFixed(3)
        : t.price.toFixed(2);

    return `
      <div class="price-row">
        <div class="price-token">
          <div class="token-icon" style="background:${t.bg};color:${t.fg}">${t.sym.slice(0,2)}</div>
          <div>
            <div class="tok-name">${t.sym}</div>
            <div class="tok-sub">${t.name}</div>
          </div>
        </div>
        <svg class="mini-spark" viewBox="0 0 88 32" preserveAspectRatio="none">
          <path d="${spark}" fill="none" stroke="${t.color}" stroke-width="1.5"
            stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <div class="price-right">
          <div class="price-usd">$${fmtPrice}</div>
          <div class="price-chg ${isUp ? 'up' : 'down'}">${isUp ? '▲' : '▼'} ${Math.abs(chg)}%</div>
        </div>
      </div>`;
  }).join('');
}

// ── Render paradox ───────────────────────────────────────────────────────────
function renderParadox() {
  document.getElementById('paradox-list').innerHTML = protoData.map(p => {
    const ops  = Math.round((p.entropy / 8) * 100);
    const gov  = Math.round(p.gini * 100);
    const gap  = ops - gov;
    const gapColor = gap > 40 ? '#E24B4A' : gap > 30 ? '#EF9F27' : '#1D9E75';
    return `
      <div class="paradox-item">
        <div class="paradox-meta">
          <span class="paradox-proto">${p.name}</span>
          <span class="paradox-gap" style="color:${gapColor}">Gap ${gap}pt</span>
        </div>
        <div class="dual-bar">
          <div class="dual-ops" style="width:${ops}%;background:${p.color}"></div>
          <div class="dual-gov" style="width:${gov}%"></div>
        </div>
        <div class="dual-labels">
          <span>Operational ${ops}%</span>
          <span>Governance ${gov}%</span>
        </div>
      </div>`;
  }).join('');
}

// ── Render metric cards ───────────────────────────────────────────────────────
function renderMetricCards() {
  const avg = key => protoData.reduce((s, p) => s + p[key], 0) / protoData.length;
  const avgCDI     = avg('cdi');
  const avgGini    = avg('gini');
  const avgEntropy = avg('entropy');
  const avgHHI     = avg('hhi');

  document.getElementById('avg-cdi').textContent     = fmt(avgCDI);
  document.getElementById('avg-gini').textContent    = fmt(avgGini);
  document.getElementById('avg-entropy').textContent = fmt(avgEntropy, 2);
  document.getElementById('avg-hhi').textContent     = Math.round(avgHHI).toLocaleString();

  const interp = avgCDI < 0.3 ? 'Highly Centralized' : avgCDI < 0.6 ? 'Moderately Decentralized' : 'Highly Decentralized';
  document.getElementById('cdi-interp').textContent  = interp;

  document.getElementById('cdi-fill').style.width     = (avgCDI * 100) + '%';
  document.getElementById('gini-fill').style.width    = (avgGini * 100) + '%';
  document.getElementById('entropy-fill').style.width = ((avgEntropy / 8) * 100) + '%';
  document.getElementById('hhi-fill').style.width     = ((avgHHI / 10000) * 100) + '%';
}

// ── Data refresh ─────────────────────────────────────────────────────────────
function fullRefresh() {
  // Simulate new feature values and recompute CDI(t) with adaptive weights.
  if (!ganacheConnected || !latestGanacheSample) {
    protoData = protoData.map(p => {
      const b = BASE_DATA[p.id];
      return {
        ...p,
        gini:           jitter(b.gini, 0.03),
        hhi:            Math.round(jitter(b.hhi, 0.025)),
        entropy:        jitter(b.entropy, 0.02),
        delegationCent: clamp(jitter(b.delegationCent, 0.06)),
        blocCluster:    clamp(jitter(b.blocCluster, 0.08)),
        structural:     clamp(jitter(b.structural, 0.04)),
        development:    clamp(jitter(b.development, 0.05)),
      };
    });
  } else {
    applyGanacheSample(latestGanacheSample);
  }

  recomputeModelState();

  // Extend CDI time series (rolling)
  PROTOCOL_META.forEach(p => {
    const proto = protoData.find(d => d.id === p.id);
    const newVal = clamp(jitter(proto.cdi, 0.012), 0.30, 0.90);
    cdiSeries[p.id] = [...cdiSeries[p.id].slice(1), parseFloat(newVal.toFixed(4))];
    const ds = cdiChart.data.datasets.find(d => d.label === p.name);
    if (ds) ds.data = cdiSeries[p.id];
  });

  cdiChart.update('none');

  // Update radar
  radarChart.data.datasets.forEach(ds => {
    const p = protoData.find(d => d.name === ds.label);
    if (p) ds.data = [
      parseFloat(p.scores.economic.toFixed(3)),
      parseFloat(p.scores.governance.toFixed(3)),
      parseFloat(p.scores.structural.toFixed(3)),
      parseFloat(p.scores.development.toFixed(3)),
    ];
  });
  radarChart.update('none');
  updateCentralityChart();

  renderProtoTable();
  renderMetricCards();
  renderParadox();
  renderDimensionScoreGrid();
  renderWeightList();
  renderTemporalSignals();
  renderRiskForecast();
  renderGovernanceHeatmap();
  renderDriftAlerts();

  document.getElementById('last-update-time').textContent =
    new Date().toLocaleTimeString('en-US', {hour:'2-digit', minute:'2-digit', second:'2-digit'});

  countdown = refreshInterval;

  if (ganacheConnected && ganacheProvider) {
    sampleGanacheData()
      .then(sample => {
        applyGanacheSample(sample);
        recomputeModelState();
        return fetchGanacheMeta((latestGanacheMeta && latestGanacheMeta.rpcServer) ? latestGanacheMeta.rpcServer.toLowerCase() : GANACHE_RPC_URLS[0]);
      })
      .then(meta => {
        if (!meta) return;
        latestGanacheMeta = meta;
        renderGanacheMeta(meta);
      })
      .catch(() => {
        ganacheProvider = null;
        latestGanacheSample = null;
        latestGanacheMeta = null;
        setGanacheStatus(false, 'Ganache: Disconnected');
        renderGanacheMeta(null);
      });
  }
}

function tickPrices() {
  tokenPrices = tokenPrices.map(t => {
    const newP = Math.max(t.base * 0.5, t.price * (1 + (Math.random() - 0.5) * 0.007));
    return { ...t, prevPrice: t.price, price: newP, hist: [...t.hist.slice(1), newP] };
  });
  renderPrices();
}

// ── Countdown ring ────────────────────────────────────────────────────────────
const RING_CIRC = 87.96;
function updateRing() {
  const frac = countdown / refreshInterval;
  const offset = RING_CIRC * (1 - frac);
  document.getElementById('ring-circle').setAttribute('stroke-dashoffset', offset.toFixed(2));
  document.getElementById('countdown-num').textContent = countdown;
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

// ── Refresh interval control ──────────────────────────────────────────────────
function setRefreshInterval(val) {
  refreshInterval = parseInt(val);
  startCountdown();
}

// ── Sidebar nav ───────────────────────────────────────────────────────────────
function setupNavHighlight() {
  const sections = ['overview','protocols','prices','paradox'];
  const items = document.querySelectorAll('.nav-item');
  window.addEventListener('scroll', () => {
    let current = sections[0];
    sections.forEach(id => {
      const el = document.getElementById(id);
      if (el && el.getBoundingClientRect().top < 160) current = id;
    });
    items.forEach(item => {
      item.classList.toggle('active', item.getAttribute('href') === '#' + current);
    });
  }, {passive: true});
}

// ── Bootstrap ─────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  buildProtoToggles();
  buildCDIChart();
  buildRadarChart();
  buildCentralityChart();
  renderPipelineFlow();
  renderProtoTable();
  renderPrices();
  renderParadox();
  renderMetricCards();
  renderDimensionScoreGrid();
  renderWeightList();
  renderTemporalSignals();
  renderRiskForecast();
  renderGovernanceHeatmap();
  renderDriftAlerts();
  setupNavHighlight();
  startCountdown();

  document.getElementById('last-update-time').textContent =
    new Date().toLocaleTimeString('en-US', {hour:'2-digit', minute:'2-digit', second:'2-digit'});

  // Price tick every 3 seconds
  priceTimer = setInterval(tickPrices, 3000);

  // Probe local Ganache silently on page load.
  connectGanache();
  renderGanacheMeta(null);

  // Poll GraphX feed periodically when configured.
  setGraphXStatus(false, 'GraphX: Idle');
  if (graphXPollingTimer) clearInterval(graphXPollingTimer);
  graphXPollingTimer = setInterval(fetchGraphXValue, 15000);
});
