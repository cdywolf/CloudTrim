"""Application FastAPI : API REST + dashboard web."""

from __future__ import annotations

from pathlib import Path
from cloudtrim.domain.ai_insights import generate_insight
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from cloudtrim.api.dependencies import get_repository
from cloudtrim.api.schemas import (
    AnomaliesResponse,
    AnomalyResponse,
    CostBreakdown,
    DailyCost,
    OrphanWasteResponse,
    SummaryResponse,
    UntaggedWasteResponse,
    WasteEstimate,
)
from cloudtrim.domain.analyzer import (
    analyze_orphan_resources,
    analyze_untagged_resources,
    detect_cost_anomalies,
)

# Répertoires pour les templates et fichiers statiques
BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

# Création de l'application FastAPI
app = FastAPI(
    title="CloudTrim API",
    description="Moteur d'optimisation de coûts cloud (FinOps) sur données AWS CUR",
    version="0.1.0",
)

# Montage des fichiers statiques
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Templates Jinja2
templates = Jinja2Templates(directory=TEMPLATES_DIR)


# === Endpoints API ===


@app.get("/health")
def health_check():
    """Vérifie que l'API tourne."""
    return {"status": "healthy"}


@app.get("/api/costs/by-product", response_model=list[CostBreakdown])
def cost_by_product():
    """Décomposition des coûts par service AWS."""
    repo = get_repository()
    return repo.cost_by_product()


@app.get("/api/costs/by-region", response_model=list[CostBreakdown])
def cost_by_region():
    """Décomposition des coûts par région."""
    repo = get_repository()
    return repo.cost_by_region()


@app.get("/api/costs/by-team", response_model=list[CostBreakdown])
def cost_by_team():
    """Décomposition des coûts par équipe."""
    repo = get_repository()
    return repo.cost_by_team()


@app.get("/api/costs/daily", response_model=list[DailyCost])
def daily_cost():
    """Évolution journalière des coûts."""
    repo = get_repository()
    return repo.daily_cost()


@app.get("/api/waste/untagged", response_model=UntaggedWasteResponse)
def waste_untagged():
    """Dépenses non taguées avec estimation d'économies."""
    repo = get_repository()
    untagged_costs = repo.get_untagged_resources_daily_costs()
    findings = analyze_untagged_resources(untagged_costs, recovery_rate=0.4)

    resources = []
    for finding in findings:
        low, high = finding.details["adjusted_savings_range"]
        resources.append(
            WasteEstimate(
                resource_id=finding.resource_id,
                lower_bound=low,
                upper_bound=high,
                mean_daily_cost=finding.estimate.mean_daily_cost,
                sample_size=finding.estimate.sample_size,
                confidence_level=finding.estimate.confidence_level,
            )
        )

    total_lower = sum(r.lower_bound for r in resources)
    total_upper = sum(r.upper_bound for r in resources)

    return UntaggedWasteResponse(
        total_resources=len(resources),
        total_lower_bound=total_lower,
        total_upper_bound=total_upper,
        resources=resources,
    )


@app.get("/api/waste/orphans", response_model=OrphanWasteResponse)
def waste_orphans():
    """Ressources orphelines avec estimation d'économies."""
    repo = get_repository()
    orphan_costs = repo.get_orphan_resources_daily_costs()
    findings = analyze_orphan_resources(orphan_costs)

    resources = []
    for finding in findings:
        low, high = finding.estimate.confidence_interval_total
        resources.append(
            WasteEstimate(
                resource_id=finding.resource_id,
                lower_bound=low,
                upper_bound=high,
                mean_daily_cost=finding.estimate.mean_daily_cost,
                sample_size=finding.estimate.sample_size,
                confidence_level=finding.estimate.confidence_level,
            )
        )

    total_lower = sum(r.lower_bound for r in resources)
    total_upper = sum(r.upper_bound for r in resources)

    return OrphanWasteResponse(
        total_resources=len(resources),
        total_lower_bound=total_lower,
        total_upper_bound=total_upper,
        resources=resources,
    )


@app.get("/api/ai/insight")
def get_insight(resource_id: str, type: str):
    """Génère un insight en langage naturel pour une ressource ou anomalie.

    Args:
        resource_id: Identifiant de la ressource.
        type: Type d'insight ("orphan", "untagged", "anomaly").
    """
    repo = get_repository()

    # Récupère le contexte selon le type
    if type == "orphan":
        orphan_costs = repo.get_orphan_resources_daily_costs()
        if resource_id not in orphan_costs:
            return {"error": "Ressource orpheline non trouvée"}
        daily_costs = orphan_costs[resource_id]
        context = {
            "total_cost": sum(daily_costs),
            "daily_cost": sum(daily_costs) / len(daily_costs),
            "days": len(daily_costs),
        }
    elif type == "untagged":
        untagged_costs = repo.get_untagged_resources_daily_costs()
        if resource_id not in untagged_costs:
            return {"error": "Ressource non taguée non trouvée"}
        daily_costs = untagged_costs[resource_id]
        context = {
            "total_cost": sum(daily_costs),
            "recovery_rate": 0.4,
        }
    elif type == "anomaly":
        # Pour les anomalies, on cherche dans toutes les ressources
        all_costs = repo.get_all_resources_daily_costs()
        if resource_id not in all_costs:
            return {"error": "Ressource non trouvée"}
        daily_costs = all_costs[resource_id]
        # Trouve le jour avec le coût max (l'anomalie)
        max_day_idx = max(range(len(daily_costs)), key=lambda i: daily_costs[i][1])
        anomaly_day, anomaly_cost = daily_costs[max_day_idx]
        costs_only = [c for _, c in daily_costs]
        from statistics import median
        median_cost = median(costs_only)
        from cloudtrim.domain.analyzer import detect_cost_anomalies
        anomalies = detect_cost_anomalies({resource_id: daily_costs})
        if not anomalies:
            return {"error": "Aucune anomalie détectée pour cette ressource"}
        anomaly = anomalies[0]
        context = {
            "cost": anomaly.cost,
            "median": anomaly.median_cost,
            "z_score": anomaly.z_score,
            "day": anomaly.day,
            "severity": anomaly.severity,
        }
    else:
        return {"error": f"Type d'insight inconnu : {type}"}

    insight = generate_insight(resource_id, type, context)
    return {
        "resource_id": insight.resource_id,
        "insight_type": insight.insight_type,
        "title": insight.title,
        "summary": insight.summary,
        "details": insight.details,
        "actions": insight.actions,
        "confidence": insight.confidence,
    }


@app.get("/api/anomalies", response_model=AnomaliesResponse)
def anomalies():
    """Anomalies de coût détectées."""
    repo = get_repository()
    all_costs = repo.get_all_resources_daily_costs()
    anomaly_list = detect_cost_anomalies(all_costs, threshold=3.0)

    anomalies_response = [
        AnomalyResponse(
            resource_id=a.resource_id,
            day=a.day,
            cost=a.cost,
            median_cost=a.median_cost,
            z_score=a.z_score,
            severity=a.severity,
        )
        for a in anomaly_list
    ]

    critical_count = sum(1 for a in anomalies_response if a.severity == "critical")
    moderate_count = sum(1 for a in anomalies_response if a.severity == "moderate")

    return AnomaliesResponse(
        total_anomalies=len(anomalies_response),
        critical_count=critical_count,
        moderate_count=moderate_count,
        anomalies=anomalies_response,
    )


@app.get("/api/summary", response_model=SummaryResponse)
def summary():
    """Résumé global."""
    repo = get_repository()

    # Coût total
    daily_costs = repo.daily_cost()
    total_cost = sum(d["daily_cost"] for d in daily_costs)

    # Dépenses non taguées
    untagged_costs = repo.get_untagged_resources_daily_costs()
    untagged_findings = analyze_untagged_resources(untagged_costs, recovery_rate=0.4)
    untagged_lower = sum(f.details["adjusted_savings_range"][0] for f in untagged_findings)
    untagged_upper = sum(f.details["adjusted_savings_range"][1] for f in untagged_findings)

    # Ressources orphelines
    orphan_costs = repo.get_orphan_resources_daily_costs()
    orphan_findings = analyze_orphan_resources(orphan_costs)
    orphan_lower = sum(f.estimate.confidence_interval_total[0] for f in orphan_findings)
    orphan_upper = sum(f.estimate.confidence_interval_total[1] for f in orphan_findings)

    # Anomalies
    all_costs = repo.get_all_resources_daily_costs()
    anomaly_list = detect_cost_anomalies(all_costs, threshold=3.0)

    return SummaryResponse(
        total_cost=total_cost,
        untagged_savings_lower=untagged_lower,
        untagged_savings_upper=untagged_upper,
        orphan_savings_lower=orphan_lower,
        orphan_savings_upper=orphan_upper,
        anomalies_count=len(anomaly_list),
    )


# === Routes du dashboard ===


@app.get("/", response_class=HTMLResponse)
def dashboard_home(request: Request):
    """Page d'accueil du dashboard."""
    return templates.TemplateResponse(
        request=request,
        name="index.html"
    )