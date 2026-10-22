from typing import List, Dict, Any
import numpy as np


def compute_temporal_drift(
    series: List[float],
    window_recent: int = 14,
    window_baseline: int = 30,
) -> Dict[str, Any]:
    """
    Computes temporal decentralization drift and structural regime shifts.
    
    Returns:
        - recent_mean: Average CDI over recent window
        - baseline_mean: Average CDI over historical baseline window
        - drift: difference (recent - baseline). Negative value indicates centralization drift!
        - volatility: standard deviation of period-to-period differences
        - change_points_count: number of significant step changes
        - structural_break: boolean indicating statistically significant drift (> 2.0 std err)
        - severity_label: "Stable", "Watch", "Warning", "Critical"
    """
    arr = np.asarray(series, dtype=np.float64)
    n = len(arr)
    if n < 4:
        return {
            "recent_mean": float(arr[-1]) if n > 0 else 0.5,
            "baseline_mean": float(arr[0]) if n > 0 else 0.5,
            "drift": 0.0,
            "volatility": 0.0,
            "change_points_count": 0,
            "structural_break": False,
            "severity_label": "Stable",
        }

    # Slice windows
    w_rec = min(window_recent, n // 2)
    w_base = min(window_baseline, n - w_rec)

    recent = arr[-w_rec:]
    baseline = arr[-(w_rec + w_base):-w_rec] if w_base > 0 else arr[:w_rec]

    recent_mean = float(np.mean(recent))
    baseline_mean = float(np.mean(baseline))
    drift = recent_mean - baseline_mean

    # Daily diffs
    diffs = np.diff(arr)
    volatility = float(np.std(diffs)) if len(diffs) > 1 else 0.0

    # CUSUM change points
    threshold = max(0.015, 2.0 * volatility)
    significant_steps = int(np.sum(np.abs(diffs) > threshold))

    # Standard error of difference in means
    se = np.sqrt((np.var(recent) / len(recent)) + (np.var(baseline) / len(baseline)) + 1e-8)
    z_score = abs(drift) / se if se > 0 else 0.0
    structural_break = bool(z_score > 2.0 and abs(drift) > 0.02)

    # Severity evaluation
    severity = "Stable"
    if drift < -0.05 or (structural_break and drift < 0):
        severity = "Critical"
    elif drift < -0.025 or structural_break:
        severity = "Warning"
    elif drift < -0.01 or volatility > 0.02:
        severity = "Watch"

    return {
        "recent_mean": round(recent_mean, 4),
        "baseline_mean": round(baseline_mean, 4),
        "drift": round(drift, 4),
        "volatility": round(volatility, 4),
        "change_points_count": significant_steps,
        "structural_break": structural_break,
        "severity_label": severity,
    }


def detect_change_points_cusum(series: List[float], threshold: float = 3.0) -> List[int]:
    """
    Two-sided Cumulative Sum (CUSUM) change-point detector.
    Returns indices where statistically significant shifts occur.
    """
    arr = np.asarray(series, dtype=np.float64)
    if len(arr) < 5:
        return []

    mean_val = np.mean(arr)
    std_val = np.std(arr)
    if std_val < 1e-8:
        return []

    standardized = (arr - mean_val) / std_val
    pos_sum = 0.0
    neg_sum = 0.0
    change_points = []

    for i in range(1, len(arr)):
        pos_sum = max(0.0, pos_sum + standardized[i] - 0.5)
        neg_sum = max(0.0, neg_sum - standardized[i] - 0.5)

        if pos_sum > threshold or neg_sum > threshold:
            change_points.append(i)
            pos_sum = 0.0
            neg_sum = 0.0

    return change_points
