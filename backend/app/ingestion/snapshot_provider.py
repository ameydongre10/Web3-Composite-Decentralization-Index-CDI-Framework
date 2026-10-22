from typing import Dict, Any, List
import httpx
from backend.app.config import settings
from backend.app.ingestion.base import BaseDataProvider


class SnapshotGraphQLProvider(BaseDataProvider):
    """
    Integrates with Snapshot.org GraphQL API to extract actual DAO proposal votes.
    """
    def __init__(self, endpoint: str = settings.SNAPSHOT_GRAPHQL_URL, timeout_seconds: float = 10.0):
        self.endpoint = endpoint
        self.timeout = timeout_seconds

    async def fetch_telemetry(self, endpoint: str) -> Dict[str, Any]:
        return {"status": "online", "endpoint": self.endpoint}

    async def fetch_holder_distribution(self, protocol_slug: str, contract_address: str = None) -> List[float]:
        return []

    async def fetch_governance_distribution(self, space_id: str) -> Dict[str, Any]:
        query = """
        query GetRecentVotes($space: String!) {
            votes(
                first: 100,
                where: { space: $space },
                orderBy: "created",
                orderDirection: desc
            ) {
                id
                voter
                vp
                choice
            }
        }
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    self.endpoint,
                    json={"query": query, "variables": {"space": f"{space_id}.eth"}},
                )
                if resp.status_code == 200:
                    data = resp.json().get("data", {}).get("votes", [])
                    vps = [float(v["vp"]) for v in data if float(v.get("vp", 0)) > 0]
                    return {
                        "votes": vps,
                        "voter_count": len(vps),
                        "provenance": "snapshot_graphql",
                    }
        except Exception:
            pass

        # Fallback if network or space is unavailable
        return {"votes": [], "voter_count": 0, "provenance": "unavailable"}
