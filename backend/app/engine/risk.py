import numpy as np


def sigmoid(x: float) -> float:
    return float(1.0 / (1.0 + np.exp(-np.clip(x, -30.0, 30.0))))


def compute_risk_indicators(
    cdi: float,
    economic: float,
    governance: float,
    structural: float,
    gini: float,
    hhi_points: float,
    delegation_centrality: float,
    bloc_clustering: float,
) -> dict:
    """
    Computes grounded probabilistic risk indicators in [0.0, 1.0].
    
    1. Centralization Risk: Overall likelihood that the protocol operates under centralized control.
    2. Governance Capture: Likelihood that voting quorum can be seized by top delegates or whales.
    3. Cartel Formation: Likelihood of collusive voting blocs coordinating off-chain.
    4. Composite Risk: Weighted integration of the above risks.
    """
    # 1. Centralization Risk
    # Higher Gini and HHI, combined with lower overall CDI score
    c_logits = (
        4.0 * (0.50 - cdi) +
        2.5 * (gini - 0.35) +
        1.5 * ((hhi_points - 2000.0) / 1000.0)
    )
    centralization_risk = float(np.clip(sigmoid(c_logits), 0.01, 0.99))

    # 2. Governance Capture Risk
    # Low governance score, high delegation centrality, high bloc clustering
    g_logits = (
        3.5 * (0.50 - governance) +
        3.0 * (delegation_centrality - 0.30) +
        2.0 * (bloc_clustering - 0.30)
    )
    governance_capture = float(np.clip(sigmoid(g_logits), 0.01, 0.99))

    # 3. Cartel Formation Risk
    # Low structural score, high bloc clustering, low economic distribution
    cartel_logits = (
        3.0 * (0.50 - structural) +
        2.5 * (bloc_clustering - 0.25) +
        1.5 * (0.50 - economic)
    )
    cartel_formation = float(np.clip(sigmoid(cartel_logits), 0.01, 0.99))

    # Composite Risk
    composite = float(
        0.40 * centralization_risk +
        0.35 * governance_capture +
        0.25 * cartel_formation
    )

    return {
        "centralization_risk": round(centralization_risk, 4),
        "governance_capture_risk": round(governance_capture, 4),
        "cartel_formation_risk": round(cartel_formation, 4),
        "composite_risk": round(composite, 4),
    }
