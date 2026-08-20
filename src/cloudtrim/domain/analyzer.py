"""Moteur d'analyse FinOps : détection de gaspillage et estimation des économies.

Ce module contient la logique pure de détection (règles de gaspillage) et le
calcul statistique des intervalles de confiance. Il est indépendant de DuckDB
et de toute infrastructure.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass


@dataclass
class CostEstimate:
    """Estimation d'économie avec intervalle de confiance."""

    lower_bound: float
    upper_bound: float
    confidence_level: float  # ex: 0.95 pour 95%
    sample_size: int
    mean_daily_cost: float

    @property
    def estimated_total_savings(self) -> float:
        """Estimation ponctuelle (moyenne × nombre de jours)."""
        return self.mean_daily_cost * self.sample_size

    @property
    def confidence_interval_total(self) -> tuple[float, float]:
        """Intervalle de confiance sur le total (bornes × nombre de jours)."""
        return (self.lower_bound * self.sample_size, self.upper_bound * self.sample_size)


def _t_critical(n: int, confidence: float = 0.95) -> float:
    """Valeur critique t de Student pour un intervalle de confiance donné.

    Pour n >= 30, on utilise l'approximation normale (t ≈ 1.96).
    Pour n < 30, on utilise une table de valeurs critiques (df = n - 1).
    """
    if n >= 30:
        return 1.96  # approximation normale pour grands échantillons

    # Table de valeurs critiques t pour 95% de confiance (queue à deux côtés)
    # df = n - 1 degrés de liberté
    t_table = {
        1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571,
        6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228,
        11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145, 15: 2.131,
        16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093, 20: 2.086,
        21: 2.080, 22: 2.074, 23: 2.069, 24: 2.064, 25: 2.060,
        26: 2.056, 27: 2.052, 28: 2.048, 29: 2.045,
    }
    df = n - 1
    return t_table.get(df, 1.96)


def estimate_savings(daily_costs: list[float], confidence: float = 0.95) -> CostEstimate:
    """Calcule l'intervalle de confiance pour l'économie potentielle.

    Args:
        daily_costs: Liste des coûts journaliers (un par jour).
        confidence: Niveau de confiance (défaut 0.95 pour 95%).

    Returns:
        Un CostEstimate avec les bornes de l'intervalle de confiance.
    """
    if not daily_costs:
        raise ValueError("daily_costs ne peut pas être vide")

    n = len(daily_costs)
    mean = statistics.mean(daily_costs)

    if n == 1:
        # Pas de variabilité mesurable avec un seul point
        return CostEstimate(
            lower_bound=mean,
            upper_bound=mean,
            confidence_level=confidence,
            sample_size=1,
            mean_daily_cost=mean,
        )

    stdev = statistics.stdev(daily_costs)
    t_val = _t_critical(n, confidence)
    margin_of_error = t_val * (stdev / math.sqrt(n))

    return CostEstimate(
        lower_bound=max(0, mean - margin_of_error),
        upper_bound=mean + margin_of_error,
        confidence_level=confidence,
        sample_size=n,
        mean_daily_cost=mean,
    )


@dataclass
class WasteFinding:
    """Un constat de gaspillage avec estimation d'économie."""

    resource_id: str
    waste_type: str  # "untagged" ou "orphan"
    estimate: CostEstimate
    details: dict


def analyze_untagged_resources(
    daily_costs_by_resource: dict[str, list[float]],
    recovery_rate: float = 0.4,
) -> list[WasteFinding]:
    """Analyse les ressources non taguées et estime les économies.

    Args:
        daily_costs_by_resource: Dict {resource_id: [coût_jour_1, coût_jour_2, ...]}
        recovery_rate: Taux de récupération estimé (défaut 40%).

    Returns:
        Liste de WasteFinding pour chaque ressource non taguée.
    """
    findings = []
    for resource_id, daily_costs in daily_costs_by_resource.items():
        if not daily_costs:
            continue

        estimate = estimate_savings(daily_costs)
        # Applique le taux de récupération aux bornes
        adjusted_lower = estimate.lower_bound * recovery_rate * estimate.sample_size
        adjusted_upper = estimate.upper_bound * recovery_rate * estimate.sample_size

        findings.append(
            WasteFinding(
                resource_id=resource_id,
                waste_type="untagged",
                estimate=estimate,
                details={
                    "recovery_rate": recovery_rate,
                    "adjusted_savings_range": (adjusted_lower, adjusted_upper),
                },
            )
        )

    return findings


def analyze_orphan_resources(
    daily_costs_by_resource: dict[str, list[float]],
) -> list[WasteFinding]:
    """Analyse les ressources orphelines et estime les économies (100% récupérable).

    Args:
        daily_costs_by_resource: Dict {resource_id: [coût_jour_1, coût_jour_2, ...]}

    Returns:
        Liste de WasteFinding pour chaque ressource orpheline.
    """
    findings = []
    for resource_id, daily_costs in daily_costs_by_resource.items():
        if not daily_costs:
            continue

        estimate = estimate_savings(daily_costs)
        findings.append(
            WasteFinding(
                resource_id=resource_id,
                waste_type="orphan",
                estimate=estimate,
                details={"recovery_rate": 1.0},
            )
        )

    return findings



 


@dataclass
class Anomaly:
    """Une anomalie de coût détectée."""

    resource_id: str
    day: str  # format ISO (YYYY-MM-DD)
    cost: float
    median_cost: float
    z_score: float
    severity: str  # "moderate" ou "critical"


def detect_cost_anomalies(
    daily_costs_by_resource: dict[str, list[tuple[str, float]]],
    threshold: float = 3.0,
) -> list[Anomaly]:
    """Détecte les anomalies de coût en utilisant le Z-score basé sur la médiane.

    Args:
        daily_costs_by_resource: Dict {resource_id: [(day, cost), ...]}
        threshold: Seuil de Z-score pour considérer un jour comme anormal (défaut 3.0).

    Returns:
        Liste d'anomalies détectées, triées par Z-score décroissant.
    """
    anomalies = []

    for resource_id, daily_costs in daily_costs_by_resource.items():
        if len(daily_costs) < 3:
            # Pas assez de données pour détecter des anomalies fiables
            continue

        costs = [cost for _, cost in daily_costs]
        median = statistics.median(costs)

        # Calcul du MAD (Median Absolute Deviation) pour plus de robustesse
        deviations = [abs(c - median) for c in costs]
        mad = statistics.median(deviations)

        # Si MAD = 0 (tous les coûts identiques), on utilise un écart minimal
        if mad == 0:
            mad = 0.01

        for day, cost in daily_costs:
            # Z-score modifié basé sur la médiane et le MAD
            z_score = (cost - median) / mad

            if z_score > threshold:
                severity = "critical" if z_score > 5.0 else "moderate"
                anomalies.append(
                    Anomaly(
                        resource_id=resource_id,
                        day=day,
                        cost=cost,
                        median_cost=median,
                        z_score=z_score,
                        severity=severity,
                    )
                )

    # Trie par Z-score décroissant (les plus critiques en premier)
    anomalies.sort(key=lambda a: a.z_score, reverse=True)
    return anomalies