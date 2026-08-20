"""Schémas Pydantic pour les réponses de l'API."""

from __future__ import annotations

from pydantic import BaseModel


class CostBreakdown(BaseModel):
    """Décomposition des coûts (par service, région, équipe, etc.)."""

    label: str
    total_cost: float


class DailyCost(BaseModel):
    """Coût journalier."""

    day: str
    daily_cost: float


class WasteEstimate(BaseModel):
    """Estimation d'économie pour une ressource gaspillée."""

    resource_id: str
    lower_bound: float
    upper_bound: float
    mean_daily_cost: float
    sample_size: int
    confidence_level: float


class UntaggedWasteResponse(BaseModel):
    """Réponse pour les dépenses non taguées."""

    total_resources: int
    total_lower_bound: float
    total_upper_bound: float
    resources: list[WasteEstimate]


class OrphanWasteResponse(BaseModel):
    """Réponse pour les ressources orphelines."""

    total_resources: int
    total_lower_bound: float
    total_upper_bound: float
    resources: list[WasteEstimate]


class AnomalyResponse(BaseModel):
    """Une anomalie de coût détectée."""

    resource_id: str
    day: str
    cost: float
    median_cost: float
    z_score: float
    severity: str


class AnomaliesResponse(BaseModel):
    """Réponse pour les anomalies."""

    total_anomalies: int
    critical_count: int
    moderate_count: int
    anomalies: list[AnomalyResponse]


class SummaryResponse(BaseModel):
    """Résumé global."""

    total_cost: float
    untagged_savings_lower: float
    untagged_savings_upper: float
    orphan_savings_lower: float
    orphan_savings_upper: float
    anomalies_count: int