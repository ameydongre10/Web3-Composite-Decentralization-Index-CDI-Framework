from abc import ABC, abstractmethod
from typing import Dict, Any, List


class BaseDataProvider(ABC):
    """
    Abstract interface for blockchain and governance data providers.
    """
    @abstractmethod
    async def fetch_telemetry(self, endpoint: str) -> Dict[str, Any]:
        """Fetch raw node telemetry (block number, gas price, latency)."""
        pass

    @abstractmethod
    async def fetch_holder_distribution(self, protocol_slug: str, contract_address: str = None) -> List[float]:
        """Fetch token balance distribution across holders."""
        pass

    @abstractmethod
    async def fetch_governance_distribution(self, protocol_slug: str) -> Dict[str, Any]:
        """Fetch governance proposal votes and voter weights."""
        pass
