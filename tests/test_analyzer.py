"""Tests du moteur d'analyse FinOps."""

import pytest

from cloudtrim.domain.analyzer import (
    analyze_orphan_resources,
    analyze_untagged_resources,
    estimate_savings,
)


def test_estimate_savings_with_stable_costs():
    """Coûts stables → intervalle étroit."""
    daily_costs = [10.0] * 30
    estimate = estimate_savings(daily_costs, confidence=0.95)

    assert estimate.sample_size == 30
    assert estimate.mean_daily_cost == 10.0
    # Intervalle très étroit car pas de variabilité
    assert estimate.lower_bound == pytest.approx(10.0, abs=0.01)
    assert estimate.upper_bound == pytest.approx(10.0, abs=0.01)


def test_estimate_savings_with_variable_costs():
    """Coûts variables → intervalle plus large."""
    daily_costs = [10.0, 12.0, 8.0, 11.0, 9.0] * 6  # 30 jours, variabilité
    estimate = estimate_savings(daily_costs, confidence=0.95)

    assert estimate.sample_size == 30
    assert estimate.mean_daily_cost == pytest.approx(10.0, abs=0.5)
    # Intervalle plus large à cause de la variabilité
    assert estimate.lower_bound < 10.0
    assert estimate.upper_bound > 10.0


def test_estimate_savings_raises_on_empty():
    """Erreur si la liste est vide."""
    with pytest.raises(ValueError):
        estimate_savings([])


def test_analyze_untagged_resources_applies_recovery_rate():
    """Le taux de récupération est appliqué aux bornes."""
    daily_costs_by_resource = {
        "resource-0001": [10.0] * 30,
        "resource-0002": [20.0] * 30,
    }
    findings = analyze_untagged_resources(daily_costs_by_resource, recovery_rate=0.4)

    assert len(findings) == 2
    for finding in findings:
        assert finding.waste_type == "untagged"
        assert finding.details["recovery_rate"] == 0.4
        low, high = finding.details["adjusted_savings_range"]
        # Les bornes ajustées doivent être inférieures aux bornes brutes
        assert low < finding.estimate.confidence_interval_total[0]
        assert high < finding.estimate.confidence_interval_total[1]


def test_analyze_orphan_resources_full_recovery():
    """Les ressources orphelines sont 100% récupérables."""
    daily_costs_by_resource = {
        "vol-0deadbeef0000": [3.10] * 30,
    }
    findings = analyze_orphan_resources(daily_costs_by_resource)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.waste_type == "orphan"
    assert finding.details["recovery_rate"] == 1.0
    # L'économie totale est bien le coût total
    low, high = finding.estimate.confidence_interval_total
    assert low == pytest.approx(3.10 * 30, abs=1.0)
    assert high == pytest.approx(3.10 * 30, abs=1.0)