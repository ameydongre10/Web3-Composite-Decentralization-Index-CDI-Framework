# Composite Decentralization Index (CDI) Framework for Web3 Systems

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)

[cite_start]This repository contains the data, Python scripts, and analysis pipelines for computing the **Composite Decentralization Index (CDI)**, a multi-dimensional metric designed to quantify decentralization in Web3 systems[cite: 7, 8, 233, 234]. 

[cite_start]The research was conducted by Amey Dogre, Anand Rawat, Ashish Kumar Singh, Anshul Atre, and Anand Sen at the Pranveer Singh Institute of Technology, Kanpur, India[cite: 3, 4].

## 📖 Overview

[cite_start]While the theoretical benefits of decentralization are widely promoted, empirical measurement remains underdeveloped[cite: 122]. [cite_start]This project proposes the CDI to benchmark decentralization across major Decentralized Finance (DeFi) protocols by unifying three distinct structural properties[cite: 81]:
* [cite_start]**Economic Control:** Token ownership inequality[cite: 87, 114].
* [cite_start]**Political Control:** Governance voting power concentration[cite: 87, 114].
* [cite_start]**Operational Usage:** Transaction distribution and participation diversity[cite: 86, 87, 114].

[cite_start]A key finding of this research is the **Decentralization Paradox**, which highlights a structural imbalance where transactional participation is widespread, but governance power and token ownership remain highly concentrated[cite: 10, 116, 117].

## 🧮 Methodology

[cite_start]The CDI is defined as a weighted linear aggregation of three normalized indicators[cite: 89, 126]:

1.  [cite_start]**Gini Coefficient ($G$):** Measures inequality in token ownership[cite: 127]. [cite_start]Lower values indicate a more equitable distribution[cite: 127].
2.  [cite_start]**Herfindahl-Hirschman Index ($HHI$):** Measures the concentration of governance influence[cite: 128]. [cite_start]Lower values correspond to greater decentralization[cite: 129].
3.  [cite_start]**Shannon Entropy ($E$):** Measures the dispersion of transaction activity[cite: 130]. [cite_start]Higher entropy implies more decentralized economic participation[cite: 131].

[cite_start]Each metric is normalized to the interval [0, 1][cite: 132]. [cite_start]The formula for CDI is[cite: 133]:

$$CDI=(w_{1}\cdot N(G))+(w_{2}\cdot N(HHI))+(w_{3}\cdot N(E))$$

[cite_start]To avoid subjective bias, this study assigns equal weights ($w_{1}=w_{2}=w_{3}=\frac{1}{3}$)[cite: 103, 136]. 

### Interpretation Scale
* [cite_start]**0.0 - 0.3:** Highly centralized [cite: 112]
* [cite_start]**0.3 - 0.6:** Moderately decentralized [cite: 112]
* [cite_start]**0.6 - 1.0:** Highly decentralized [cite: 112]

## 📊 Data Collection

[cite_start]The evaluation is based on publicly available on-chain data spanning a 90-day observation window in Q1 2024[cite: 140, 194]. [cite_start]Data was collected using Dune Analytics queries and Etherscan APIs[cite: 234]. 

[cite_start]The analyzed DeFi protocols include[cite: 193]:
* [cite_start]Uniswap v3 [cite: 193]
* [cite_start]Aave v3 [cite: 193]
* [cite_start]SushiSwap [cite: 193]
* [cite_start]Curve Finance [cite: 193]
* [cite_start]Compound [cite: 193]

[cite_start]The dataset encompasses token balances for the top 10,000 externally owned addresses, voting power distributions for recent proposals, and transaction-level activity[cite: 142, 143, 144].

## 🚀 Results Summary

[cite_start]Results indicate consistent CDI scores ranging from 0.41 to 0.44 across the analyzed protocols, suggesting moderate decentralization[cite: 202]. 

* [cite_start]**Uniswap v3:** 0.43 [cite: 201]
* [cite_start]**Aave v3:** 0.44 [cite: 201]
* [cite_start]**SushiSwap:** 0.42 [cite: 201]
* [cite_start]**Curve Finance:** 0.41 [cite: 201]
* [cite_start]**Compound:** 0.43 [cite: 201]

[cite_start]Sensitivity analysis confirms that the CDI is robust, with scores varying within ±0.03 and protocol rankings remaining unchanged even when applying alternative weighting schemes (e.g., governance-heavy or usage-heavy weights)[cite: 222, 223].

## 🛠️ Reproducibility

[cite_start]To ensure reproducibility, all data processing and computation scripts are provided in Python[cite: 233]. [cite_start]The preprocessing pipeline features[cite: 234, 235]:
* [cite_start]Address filtering (excluding smart contracts) [cite: 236]
* [cite_start]Normalization of metric values [cite: 237]
* [cite_start]Aggregation of governance voting records [cite: 238]

*(Instructions for running the python scripts or Jupyter notebooks would go here)*
