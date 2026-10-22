import numpy as np


def compute_economic_dimension(
    gini: float,
    hhi_normalized: float,
    entropy_normalized: float,
    nakamoto_ratio: float = 0.1,
    palma_ratio: float = 2.0,
) -> float:
    """
    Computes Economic Decentralization Dimension Score F_eco in [0, 1].
    
    Components:
        - (1 - Gini): Inverted concentration (0=whale monopoly, 1=equal distribution)
        - (1 - HHI_norm): Inverted market concentration
        - Entropy_norm: Distribution diversity
        - Nakamoto ratio: Fraction of network required for majority control
    """
    gini_balance = 1.0 - np.clip(gini, 0.0, 1.0)
    hhi_balance = 1.0 - np.clip(hhi_normalized, 0.0, 1.0)
    entropy_balance = np.clip(entropy_normalized, 0.0, 1.0)
    nakamoto_norm = np.clip(nakamoto_ratio * 2.0, 0.0, 1.0)
    palma_balance = 1.0 / (1.0 + np.log1p(max(0.0, palma_ratio)))

    score = (
        0.35 * gini_balance +
        0.25 * hhi_balance +
        0.25 * entropy_balance +
        0.10 * nakamoto_norm +
        0.05 * palma_balance
    )
    return float(np.clip(score, 0.0, 1.0))


def compute_governance_dimension(
    hhi_normalized: float,
    entropy_normalized: float,
    delegation_centrality: float,
    bloc_clustering: float,
) -> float:
    """
    Computes Governance Decentralization Dimension Score F_gov in [0, 1].

    Components:
        - (1 - HHI_norm): Inverted voting power concentration
        - Entropy_norm: Voter turnout and ballot diversity
        - (1 - Delegation Centrality): Absence of voting proxy monopolies
        - (1 - Bloc Clustering): Absence of collusive voting cartels
    """
    voting_balance = 1.0 - np.clip(hhi_normalized, 0.0, 1.0)
    entropy_balance = np.clip(entropy_normalized, 0.0, 1.0)
    delegation_balance = 1.0 - np.clip(delegation_centrality, 0.0, 1.0)
    cartel_balance = 1.0 - np.clip(bloc_clustering, 0.0, 1.0)

    score = (
        0.35 * voting_balance +
        0.25 * entropy_balance +
        0.20 * delegation_balance +
        0.20 * cartel_balance
    )
    return float(np.clip(score, 0.0, 1.0))


def compute_structural_dimension(
    structural_base: float,
    bloc_clustering: float,
    entropy_normalized: float,
) -> float:
    """
    Computes Structural Network Decentralization Dimension Score F_struct in [0, 1].

    Components:
        - structural_base: Validator/node topology score
        - (1 - bloc_clustering): Inverted network clustering
        - entropy_normalized: Transaction and validator activity diversity
    """
    struct = np.clip(structural_base, 0.0, 1.0)
    anti_cluster = 1.0 - np.clip(bloc_clustering, 0.0, 1.0)
    entropy = np.clip(entropy_normalized, 0.0, 1.0)

    score = (
        0.50 * struct +
        0.30 * anti_cluster +
        0.20 * entropy
    )
    return float(np.clip(score, 0.0, 1.0))


def compute_development_dimension(
    development_base: float,
    gini: float,
    bus_factor: int = 5,
) -> float:
    """
    Computes Development Decentralization Dimension Score F_dev in [0, 1].

    Components:
        - development_base: Contributor activity and commit distribution
        - (1 - Gini): Commit equality across contributors
        - bus_factor: Number of key developers (normalized up to 10)
    """
    dev = np.clip(development_base, 0.0, 1.0)
    gini_balance = 1.0 - np.clip(gini, 0.0, 1.0)
    bus_norm = np.clip(bus_factor / 10.0, 0.1, 1.0)

    score = (
        0.55 * dev +
        0.25 * gini_balance +
        0.20 * bus_norm
    )
    return float(np.clip(score, 0.0, 1.0))
