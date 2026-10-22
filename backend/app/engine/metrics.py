import math
from typing import Sequence, Tuple
import numpy as np


def compute_gini(holdings: Sequence[float]) -> float:
    """
    Computes the Gini coefficient of wealth/token distribution.
    
    Formula:
        G = (2 * sum(i * x_i) / (n * sum(x_i))) - (n + 1) / n
    where x is sorted in ascending order, i is 1-indexed.

    Properties:
        - G in [0, 1]
        - G = 0: Perfect equality (uniform distribution)
        - G = 1: Absolute concentration (single whale owns everything)
        - Inverted for decentralization: F_gini = 1.0 - G
    """
    arr = np.asarray(holdings, dtype=np.float64)
    arr = arr[arr > 0]  # Filter non-positive/zero dust
    n = len(arr)
    if n <= 1:
        return 1.0  # Monopolistic concentration if 0 or 1 holder

    total = np.sum(arr)
    if total == 0:
        return 1.0

    sorted_arr = np.sort(arr)
    indices = np.arange(1, n + 1, dtype=np.float64)
    weighted_sum = np.sum(indices * sorted_arr)
    gini = (2.0 * weighted_sum) / (n * total) - (n + 1.0) / n
    return float(np.clip(gini, 0.0, 1.0))


def compute_hhi(values: Sequence[float]) -> Tuple[float, float]:
    """
    Computes the Herfindahl-Hirschman Index (HHI).

    Returns:
        (hhi_points, hhi_normalized)
        - hhi_points: Traditional scale from 0 to 10,000 (sum of percentage squared)
        - hhi_normalized: Scale from 0.0 (perfect distribution) to 1.0 (monopoly)
          Formula: (HHI - 1/n) / (1 - 1/n) for n > 1
    """
    arr = np.asarray(values, dtype=np.float64)
    arr = arr[arr > 0]
    n = len(arr)
    if n == 0:
        return 10000.0, 1.0
    if n == 1:
        return 10000.0, 1.0

    total = np.sum(arr)
    if total <= 0:
        return 10000.0, 1.0

    fractions = arr / total
    hhi_fractional = np.sum(fractions ** 2)  # [1/n, 1.0]
    hhi_points = hhi_fractional * 10000.0

    # Minimum possible HHI for n entities is 1/n
    min_hhi = 1.0 / n
    if min_hhi >= 1.0:
        hhi_norm = 1.0
    else:
        hhi_norm = (hhi_fractional - min_hhi) / (1.0 - min_hhi)

    return float(np.clip(hhi_points, 0.0, 10000.0)), float(np.clip(hhi_norm, 0.0, 1.0))


def compute_shannon_entropy(values: Sequence[float]) -> Tuple[float, float]:
    """
    Computes Shannon Entropy and Normalized Shannon Entropy.

    Formula:
        H = - sum(p_i * ln(p_i))
        H_norm = H / ln(n)

    Properties:
        - H_norm in [0, 1]
        - H_norm = 1.0: Perfect uniform dispersion (highest decentralization)
        - H_norm = 0.0: Extreme concentration (single entity holds all weight)
    """
    arr = np.asarray(values, dtype=np.float64)
    arr = arr[arr > 0]
    n = len(arr)
    if n <= 1:
        return 0.0, 0.0

    total = np.sum(arr)
    if total <= 0:
        return 0.0, 0.0

    probs = arr / total
    # Use natural log
    entropy = -np.sum(probs * np.log(probs + 1e-15))
    max_entropy = np.log(n)
    normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0.0

    return float(max(0.0, entropy)), float(np.clip(normalized_entropy, 0.0, 1.0))


def compute_nakamoto_coefficient(holdings: Sequence[float], threshold_ratio: float = 0.50) -> int:
    """
    Computes the Nakamoto Coefficient:
    Minimum number of entities needed to reach or exceed `threshold_ratio` of total holdings (default 50%).
    """
    arr = np.asarray(holdings, dtype=np.float64)
    arr = arr[arr > 0]
    if len(arr) == 0:
        return 1

    total = np.sum(arr)
    if total <= 0:
        return 1

    sorted_desc = np.sort(arr)[::-1]
    cumulative = np.cumsum(sorted_desc)
    target = threshold_ratio * total

    # To strictly exceed target (e.g. > 50% control)
    count = int(np.searchsorted(cumulative, target, side="right")) + 1
    return min(len(arr), max(1, count))


def compute_palma_ratio(holdings: Sequence[float]) -> float:
    """
    Computes the Palma Ratio:
    Share of top 10% holdings divided by share of bottom 40% holdings.
    """
    arr = np.asarray(holdings, dtype=np.float64)
    arr = arr[arr > 0]
    n = len(arr)
    if n < 10:
        return 1.0

    sorted_arr = np.sort(arr)
    total = np.sum(sorted_arr)
    if total <= 0:
        return 1.0

    top_10_idx = int(math.ceil(n * 0.90))
    bottom_40_idx = int(math.floor(n * 0.40))

    top_10_share = np.sum(sorted_arr[top_10_idx:]) / total
    bottom_40_share = np.sum(sorted_arr[:bottom_40_idx]) / total

    if bottom_40_share <= 0:
        return 100.0  # High concentration ceiling
    return float(top_10_share / bottom_40_share)


def compute_top_k_share(holdings: Sequence[float], k: int = 10) -> float:
    """
    Computes the share of holdings owned by the top K holders.
    """
    arr = np.asarray(holdings, dtype=np.float64)
    arr = arr[arr > 0]
    if len(arr) == 0:
        return 1.0

    total = np.sum(arr)
    if total <= 0:
        return 1.0

    sorted_desc = np.sort(arr)[::-1]
    top_k_sum = np.sum(sorted_desc[:k])
    return float(np.clip(top_k_sum / total, 0.0, 1.0))
