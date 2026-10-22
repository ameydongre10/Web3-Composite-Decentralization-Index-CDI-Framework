import pytest
import numpy as np
from backend.app.engine.metrics import (
    compute_gini,
    compute_hhi,
    compute_shannon_entropy,
    compute_nakamoto_coefficient,
    compute_palma_ratio,
    compute_top_k_share,
)
from backend.app.engine.dimensions import (
    compute_economic_dimension,
    compute_governance_dimension,
    compute_structural_dimension,
    compute_development_dimension,
)
from backend.app.engine.weighting import (
    compute_entropy_weights,
    normalize_custom_weights,
)
from backend.app.engine.temporal import (
    compute_temporal_drift,
    detect_change_points_cusum,
)
from backend.app.engine.risk import compute_risk_indicators


class TestMathMetrics:
    def test_gini_uniform_equality(self):
        # Equal distribution should produce Gini close to 0
        holdings = [100.0] * 50
        gini = compute_gini(holdings)
        assert 0.0 <= gini <= 0.05

    def test_gini_extreme_monopoly(self):
        # One whale owns 99.999% of supply
        holdings = [0.001] * 99 + [1_000_000.0]
        gini = compute_gini(holdings)
        assert gini > 0.95

    def test_gini_edge_cases(self):
        assert compute_gini([]) == 1.0
        assert compute_gini([100.0]) == 1.0
        assert compute_gini([0, 0, 0]) == 1.0

    def test_hhi_uniform_distribution(self):
        # 100 equal entities: each has 1% share. Raw points = 100 * 1^2 = 100.
        holdings = [10.0] * 100
        points, norm = compute_hhi(holdings)
        assert pytest.approx(points, rel=1e-2) == 100.0
        assert pytest.approx(norm, abs=1e-4) == 0.0  # Perfect dispersion has norm=0

    def test_hhi_monopoly(self):
        holdings = [1_000_000.0]
        points, norm = compute_hhi(holdings)
        assert points == 10000.0
        assert norm == 1.0

    def test_shannon_entropy_uniform(self):
        # Uniform distribution maximizes normalized entropy to 1.0
        holdings = [50.0] * 32
        raw_h, norm_h = compute_shannon_entropy(holdings)
        assert raw_h > 0
        assert pytest.approx(norm_h, abs=1e-4) == 1.0

    def test_shannon_entropy_concentrated(self):
        holdings = [1.0] * 10 + [10_000_000.0]
        raw_h, norm_h = compute_shannon_entropy(holdings)
        assert norm_h < 0.10

    def test_nakamoto_coefficient(self):
        # 10 holders with [50, 20, 10, 5, 5, 2, 2, 2, 2, 2]
        holdings = [50, 20, 10, 5, 5, 2, 2, 2, 2, 2]
        # Total = 100. Top 1 (50) does not exceed 50%. Top 2 (50+20=70) exceeds 50%.
        nakamoto = compute_nakamoto_coefficient(holdings, threshold_ratio=0.50)
        assert nakamoto == 2

    def test_palma_ratio(self):
        holdings = list(range(1, 101))  # 1 to 100
        palma = compute_palma_ratio(holdings)
        assert palma > 0

    def test_top_k_share(self):
        holdings = [100.0] * 10
        share = compute_top_k_share(holdings, k=3)
        assert pytest.approx(share, abs=1e-3) == 0.30


class TestDimensionsAndWeighting:
    def test_economic_dimension_bounds(self):
        score = compute_economic_dimension(gini=0.2, hhi_normalized=0.1, entropy_normalized=0.8)
        assert 0.0 <= score <= 1.0
        # Highly decentralized setup should score high
        assert score > 0.70

    def test_governance_dimension_bounds(self):
        score = compute_governance_dimension(
            hhi_normalized=0.8,
            entropy_normalized=0.2,
            delegation_centrality=0.7,
            bloc_clustering=0.6,
        )
        assert 0.0 <= score <= 1.0
        # Highly centralized governance should score low
        assert score < 0.35

    def test_normalize_custom_weights(self):
        w = normalize_custom_weights({"economic": 2, "governance": 2, "structural": 2, "development": 2})
        assert pytest.approx(sum(w.values()), abs=1e-5) == 1.0
        assert pytest.approx(w["economic"], abs=1e-5) == 0.25

    def test_entropy_weights_calculation(self):
        matrix = {
            "economic": [0.3, 0.4, 0.8, 0.2],
            "governance": [0.5, 0.5, 0.5, 0.5],
            "structural": [0.6, 0.7, 0.3, 0.4],
            "development": [0.4, 0.4, 0.4, 0.4],
        }
        weights = compute_entropy_weights(matrix)
        assert pytest.approx(sum(weights.values()), abs=1e-4) == 1.0
        for v in weights.values():
            assert v >= 0.0


class TestTemporalAndRisk:
    def test_temporal_drift_detection(self):
        # Stable series
        stable = [0.55 + 0.001 * (i % 3) for i in range(60)]
        res_stable = compute_temporal_drift(stable)
        assert res_stable["severity_label"] == "Stable"
        assert not res_stable["structural_break"]

        # Dropping series (centralization drift)
        decaying = [0.60] * 30 + [0.40] * 30
        res_decay = compute_temporal_drift(decaying)
        assert res_decay["drift"] < 0
        assert res_decay["severity_label"] in ["Warning", "Critical"]

    def test_cusum_detector(self):
        series = [0.5] * 20 + [0.8] * 20
        cp = detect_change_points_cusum(series, threshold=2.0)
        assert len(cp) > 0

    def test_risk_indicators(self):
        risk = compute_risk_indicators(
            cdi=0.35,
            economic=0.3,
            governance=0.25,
            structural=0.3,
            gini=0.7,
            hhi_points=3500,
            delegation_centrality=0.6,
            bloc_clustering=0.55,
        )
        assert 0.0 <= risk["centralization_risk"] <= 1.0
        assert 0.0 <= risk["governance_capture_risk"] <= 1.0
        assert 0.0 <= risk["cartel_formation_risk"] <= 1.0
        assert risk["centralization_risk"] > 0.50
