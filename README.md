# 🌐 Dynamic Decentralization Intelligence System (DDIS) for Web3

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Web3](https://img.shields.io/badge/Web3-Decentralized-blueviolet)](https://web3.foundation/)
[![Status: Prototype](https://img.shields.io/badge/Status-Research--Prototype-success)](https://github.com/)

> **From static scorecards to predictive intelligence.** DDIS is an industry-oriented analytics framework that measures Web3 decentralization over time, detects "centralization drift," and forecasts governance risks before they manifest.

---

## 🚀 Executive Summary
Current decentralization metrics are often static, one-dimensional, and retrospective. **DDIS** shifts the paradigm by computing a **Dynamic Composite Decentralization Index (CDI)**. By integrating network topology, governance behavior, and economic concentration into a rolling-window forecasting model, the system provides a proactive early-warning system for protocol health.

---

## 🧠 Core Architecture
The system operates across a 7-layer intelligence stack, moving from raw on-chain data to explainable risk probabilities.

### The Dynamic Index Formula
The core engine calculates decentralization as a function of time:

$$CDI(t) = \sum_{i=1}^{k} w_i(t) \cdot F_i(t)$$

* **$F_i(t)$**: Dimension score (Economic, Governance, Structural, Dev).
* **$w_i(t)$**: Adaptive weights calculated via entropy-based sensing.
* **$t$**: Rolling time window for temporal drift detection.

---

## ✨ Key Features
* **Four-Dimensional Scoring:** Tracks Economic, Governance, Structural (Network), and Development (Bus Factor) metrics.
* **Temporal Intelligence:** Uses change-point detection to identify when a protocol begins to "drift" toward centralization.
* **Predictive Risk Layer:** Generates a **0 to 1** probability score for governance capture and cartel formation.
* **Adaptive Weighting:** Uses an entropy engine to adjust the importance of metrics based on current network volatility.
* **Live Dashboard:** Real-time visualization with local-chain connectivity (Ganache) and external value feeds.

---

## 🛠 Tech Stack
| Layer | Technologies |
| :--- | :--- |
| **Frontend** | HTML5, CSS3, ES6+ JavaScript, **Chart.js** |
| **Blockchain** | Ethers.js v6, Ganache (Local Node) |
| **Data Logic** | Custom Entropy Engine, Rolling-window Analysis |
| **Integration** | Neural GraphX Endpoint Pattern, JSON Fetch Adapters |

---

## 📊 Functional Outputs
The system provides a suite of diagnostic tools for decision-makers:
* 📈 **CDI(t) Trajectory:** Visualizing the health of decentralization over months or years.
* 🔥 **Governance Heatmaps:** Identifying clusters of voting power and delegation monopolies.
* 🕸 **Network Centrality:** Mapping node distribution and topology.
* 🚨 **Drift Alerts:** Automated notifications when structural breaks occur in the decentralization trend.

---

## 🗺 Roadmap & Future Scope
- [ ] **Phase 1:** Core CDI Engine & Local Chain Integration (Current)
- [ ] **Phase 2:** Contract-level event ingestion (Proposals/Votes/Treasury)
- [ ] **Phase 3:** Supervised weight learning using historical exploit datasets
- [ ] **Phase 4:** Graph Neural Networks (GNN) for advanced structural forecasting
- [ ] **Phase 5:** Cross-chain support (L2s, Solana, Polkadot)

---

## 👥 Stakeholders
* **Protocol Foundations:** Monitor long-term ecosystem health.
* **Investors:** Conduct deep due diligence on structural resilience.
* **Regulators:** Access evidence-based decentralization assessments.
* **Security Teams:** Detect concentration patterns that precede exploits.

---

## 📝 Abstract
The **Dynamic Decentralization Intelligence System** transforms decentralization analysis from static scoring into continuous, predictive risk intelligence. By quantifying decentralization across four critical dimensions and applying probabilistic modeling, the system surfaces actionable insights. It bridges the gap between academic rigor and operational monitoring, providing the "radar" necessary for the next generation of resilient Web3 protocols.

---

### 🛠 Installation (Prototype)
```bash
# Clone the repository
git clone [https://github.com/your-username/project-name.git](https://github.com/your-username/project-name.git)

# Install dependencies
npm install

# Start a local Ganache instance for telemetry
ganache-cli

# Open the dashboard
open index.html
