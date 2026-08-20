"""Tests du moteur d'insights IA."""

import pytest

from cloudtrim.domain.ai_insights import generate_insight


def test_orphan_insight():
    """Génère un insight pour une ressource orpheline."""
    context = {
        "total_cost": 93.11,
        "daily_cost": 3.10,
        "days": 30,
    }
    insight = generate_insight("vol-0deadbeef0000", "orphan", context)

    assert insight.resource_id == "vol-0deadbeef0000"
    assert insight.insight_type == "orphan"
    assert "orpheline" in insight.title.lower()
    assert "93.11" in insight.summary
    assert len(insight.actions) > 0
    assert insight.confidence == "high"


def test_untagged_insight():
    """Génère un insight pour une ressource non taguée."""
    context = {
        "total_cost": 150.0,
        "recovery_rate": 0.4,
    }
    insight = generate_insight("resource-0001", "untagged", context)

    assert insight.insight_type == "untagged"
    assert "non taguée" in insight.title.lower()
    assert "40%" in insight.summary
    assert insight.confidence == "medium"


def test_anomaly_insight():
    """Génère un insight pour une anomalie."""
    context = {
        "cost": 57.50,
        "median": 2.30,
        "z_score": 5.2,
        "day": "2026-01-25",
        "severity": "critical",
    }
    insight = generate_insight("resource-0015", "anomaly", context)

    assert insight.insight_type == "anomaly"
    assert "CRITIQUE" in insight.title
    assert "5.2" in insight.summary
    assert "CloudTrail" in "\n".join(insight.actions)
    assert insight.confidence == "high"


def test_unknown_type_raises_error():
    """Erreur si le type d'insight est inconnu."""
    with pytest.raises(ValueError):
        generate_insight("resource-0001", "unknown", {})