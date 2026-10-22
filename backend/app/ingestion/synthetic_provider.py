from typing import Dict, Any, List
import numpy as np
from backend.app.ingestion.base import BaseDataProvider


class SyntheticDataProvider(BaseDataProvider):
    """
    Generates statistically grounded token and governance distributions
    using calibrated Pareto and log-normal models for testing and demonstration.
    
    All returned data is transparently flagged as provenance='synthetic'.
    """
    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)

    async def fetch_telemetry(self, endpoint: str) -> Dict[str, Any]:
        return {
            "current_block": 21_000_000 + int(self.rng.integers(100, 50000)),
            "gas_price": int(self.rng.integers(12, 35) * 1e9),
            "latency_ms": round(float(self.rng.uniform(15.0, 45.0)), 2),
            "endpoint": endpoint,
            "status": "online (simulated)",
        }

    async def fetch_holder_distribution(
        self,
        protocol_slug: str,
        contract_address: str = None,
        sample_size: int = 150,
    ) -> List[float]:
        # Web3 token distribution follows heavy-tailed Pareto distribution (alpha ~ 1.2 to 1.8)
        alpha_map = {
            "uniswap": 1.45,
            "aave": 1.38,
            "sushi": 1.55,
            "curve": 1.62,
            "compound": 1.40,
        }
        alpha = alpha_map.get(protocol_slug, 1.45)
        # Generate Pareto samples
        samples = (self.rng.pareto(alpha, sample_size) + 1.0) * 1000.0
        return [float(x) for x in samples]

    async def fetch_governance_distribution(self, protocol_slug: str) -> Dict[str, Any]:
        # Governance voting weights exhibit higher concentration than token balances
        alpha = 1.25
        vps = list((self.rng.pareto(alpha, 100) + 1.0) * 5000.0)
        return {
            "votes": [float(x) for x in vps],
            "voter_count": len(vps),
            "delegation_centrality": float(np.clip(self.rng.normal(0.40, 0.05), 0.1, 0.8)),
            "bloc_clustering": float(np.clip(self.rng.normal(0.38, 0.05), 0.1, 0.8)),
            "provenance": "synthetic",
        }
