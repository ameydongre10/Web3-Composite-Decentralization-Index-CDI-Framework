import math
from typing import Dict, List
import numpy as np

DEFAULT_DIMENSIONS = ["economic", "governance", "structural", "development"]


def normalize_custom_weights(weights: Dict[str, float]) -> Dict[str, float]:
    """
    Validates and normalizes weights so that sum(w_i) == 1.0 and w_i >= 0.
    """
    cleaned = {}
    for d in DEFAULT_DIMENSIONS:
        val = max(0.0, float(weights.get(d, 0.25)))
        cleaned[d] = val

    total = sum(cleaned.values())
    if total <= 0:
        return {d: 0.25 for d in DEFAULT_DIMENSIONS}

    return {d: float(val / total) for d, val in cleaned.items()}


def compute_entropy_weights(dimension_matrix: Dict[str, List[float]]) -> Dict[str, float]:
    """
    Computes objective weights using the Entropy Weight Method (EWM).
    
    Formula:
        m: number of protocol observations
        p_ij = x_ij / sum_i(x_ij)
        e_j = - 1/ln(m) * sum_i(p_ij * ln(p_ij))
        d_j = 1 - e_j (degree of divergence / information diversity)
        w_j = d_j / sum(d_k)
    """
    dims = [d for d in DEFAULT_DIMENSIONS if d in dimension_matrix]
    if not dims:
        return {d: 0.25 for d in DEFAULT_DIMENSIONS}

    # Verify lengths
    m = len(dimension_matrix[dims[0]])
    if m <= 1:
        return {d: 1.0 / len(dims) for d in dims}

    k_factor = 1.0 / math.log(m)
    diversities = {}

    for d in dims:
        raw_vals = np.asarray(dimension_matrix[d], dtype=np.float64)
        clipped_vals = np.clip(raw_vals, 0.001, 0.999)
        col_sum = np.sum(clipped_vals)

        if col_sum <= 0:
            diversities[d] = 0.001
            continue

        p = clipped_vals / col_sum
        entropy = -k_factor * np.sum(p * np.log(p + 1e-12))
        diversity = max(0.0001, 1.0 - float(entropy))
        diversities[d] = diversity

    sum_div = sum(diversities.values())
    if sum_div <= 0:
        return {d: 1.0 / len(dims) for d in dims}

    return {d: float(div / sum_div) for d, div in diversities.items()}
