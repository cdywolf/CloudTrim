"""Tests de la détection d'anomalies de coût."""

import pytest

from cloudtrim.domain.analyzer import detect_cost_anomalies


def test_detects_obvious_anomaly():
    """Détecte un pic évident (×25)."""
    # 29 jours à 2.30 $, 1 jour à 57.50 $
    daily_costs = {
        "resource-0015": [(f"2026-01-{i+1:02d}", 2.30) for i in range(29)]
        + [("2026-01-30", 57.50)]
    }

    anomalies = detect_cost_anomalies(daily_costs, threshold=3.0)

    assert len(anomalies) == 1
    anomaly = anomalies[0]
    assert anomaly.resource_id == "resource-0015"
    assert anomaly.day == "2026-01-30"
    assert anomaly.cost == 57.50
    assert anomaly.median_cost == pytest.approx(2.30, abs=0.01)
    assert anomaly.z_score > 5.0  # critique
    assert anomaly.severity == "critical"


def test_no_anomaly_with_stable_costs():
    """Pas d'anomalie si les coûts sont stables."""
    daily_costs = {
        "resource-0001": [(f"2026-01-{i+1:02d}", 10.0) for i in range(30)]
    }

    anomalies = detect_cost_anomalies(daily_costs, threshold=3.0)

    assert len(anomalies) == 0


def test_detects_moderate_anomaly():
    """Détecte une anomalie modérée (Z-score entre 3 et 5)."""
    # Données avec variabilité naturelle :
    # 14 jours à 8.0 $, 15 jours à 12.0 $ -> Médiane = 12.0, MAD = 2.0
    # 1 jour à 20.0 $ -> Déviation = 8.0. Z-score = 8.0 / 2.0 = 4.0 (Modéré)
    daily_costs = {
        "resource-0002": [(f"2026-01-{i+1:02d}", 8.0) for i in range(14)]
        + [(f"2026-01-{i+15:02d}", 12.0) for i in range(15)]
        + [("2026-01-30", 20.0)]
    }

    anomalies = detect_cost_anomalies(daily_costs, threshold=3.0)

    assert len(anomalies) == 1
    anomaly = anomalies[0]
    assert anomaly.resource_id == "resource-0002"
    assert anomaly.day == "2026-01-30"
    assert anomaly.cost == 20.0
    assert anomaly.median_cost == pytest.approx(12.0, abs=0.01)
    assert anomaly.z_score == pytest.approx(4.0, abs=0.1)  # Z-score de 4.0
    assert anomaly.severity == "moderate"  # Entre 3 et 5


def test_ignores_resources_with_too_few_days():
    """Ignore les ressources avec moins de 3 jours de données."""
    daily_costs = {
        "resource-0003": [("2026-01-01", 10.0), ("2026-01-02", 100.0)]
    }

    anomalies = detect_cost_anomalies(daily_costs, threshold=3.0)

    assert len(anomalies) == 0


def test_sorts_by_z_score_descending():
    """Trie les anomalies par Z-score décroissant."""
    daily_costs = {
        "resource-0004": [(f"2026-01-{i+1:02d}", 10.0) for i in range(29)]
        + [("2026-01-30", 20.0)],  # Z-score modéré
        "resource-0005": [(f"2026-01-{i+1:02d}", 5.0) for i in range(29)]
        + [("2026-01-30", 50.0)],  # Z-score élevé
    }

    anomalies = detect_cost_anomalies(daily_costs, threshold=3.0)

    assert len(anomalies) == 2
    # La ressource-0005 doit être en premier (Z-score plus élevé)
    assert anomalies[0].resource_id == "resource-0005"
    assert anomalies[1].resource_id == "resource-0004"