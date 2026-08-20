"""Moteur d'insights IA : génère des explications en langage naturel.

Fonctionne en mode hybride :
- Mode "template" (par défaut) : règles métier dynamiques, 100% fiable, gratuit
- Mode "LLM" (optionnel) : si une clé API est configurée, enrichit l'explication
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class Insight:
    """Un insight généré pour une ressource ou une anomalie."""

    resource_id: str
    insight_type: str  # "orphan", "untagged", "anomaly"
    title: str
    summary: str
    details: list[str]
    actions: list[str]
    confidence: str  # "high", "medium", "low"


def generate_insight(
    resource_id: str,
    insight_type: str,
    context: dict,
) -> Insight:
    """Génère un insight pour une ressource ou une anomalie.

    Args:
        resource_id: Identifiant de la ressource.
        insight_type: Type d'insight ("orphan", "untagged", "anomaly").
        context: Données contextuelles (coûts, Z-score, etc.).

    Returns:
        Un Insight avec explications et actions recommandées.
    """
    # Mode LLM (optionnel, si clé API configurée)
    if os.getenv("OPENAI_API_KEY") or os.getenv("GROQ_API_KEY"):
        return _generate_llm_insight(resource_id, insight_type, context)

    # Mode template (par défaut)
    return _generate_template_insight(resource_id, insight_type, context)


def _generate_template_insight(
    resource_id: str,
    insight_type: str,
    context: dict,
) -> Insight:
    """Génère un insight basé sur des templates métier."""

    if insight_type == "orphan":
        return _orphan_insight(resource_id, context)
    elif insight_type == "untagged":
        return _untagged_insight(resource_id, context)
    elif insight_type == "anomaly":
        return _anomaly_insight(resource_id, context)
    else:
        raise ValueError(f"Type d'insight inconnu : {insight_type}")


def _orphan_insight(resource_id: str, context: dict) -> Insight:
    """Insight pour une ressource orpheline."""
    total_cost = context.get("total_cost", 0)
    daily_cost = context.get("daily_cost", 0)
    days = context.get("days", 30)
    annual_projection = daily_cost * 365

    title = f"💡 Ressource orpheline détectée : {resource_id}"

    summary = (
        f"Cette ressource ne sert à rien et coûte {total_cost:.2f} $ "
        f"depuis {days} jours. C'est du gaspillage à 100%."
    )

    details = [
        f"📊 Coût cumulé : {total_cost:.2f} $ sur {days} jours",
        f"📊 Coût journalier moyen : {daily_cost:.2f} $",
        f"📊 Projection annuelle si non corrigé : ≈ {annual_projection:,.0f} $",
        "",
        "🔍 Diagnostic :",
        "Cette ressource n'est attachée à aucune instance active. Il s'agit",
        "probablement d'un volume EBS conservé après termination d'instance,",
        "ou d'une ressource de test oubliée.",
    ]

    actions = [
        "1. Vérifier qu'aucun snapshot récent n'en dépend",
        f"2. Supprimer via : aws ec2 delete-volume --volume-id {resource_id}",
        "3. Mettre en place une règle AWS Config pour alerter automatiquement",
    ]

    return Insight(
        resource_id=resource_id,
        insight_type="orphan",
        title=title,
        summary=summary,
        details=details,
        actions=actions,
        confidence="high",
    )


def _untagged_insight(resource_id: str, context: dict) -> Insight:
    """Insight pour une ressource non taguée."""
    total_cost = context.get("total_cost", 0)
    recovery_rate = context.get("recovery_rate", 0.4)
    recoverable = total_cost * recovery_rate

    title = f"💡 Dépense non taguée : {resource_id}"

    summary = (
        f"Cette ressource coûte {total_cost:.2f} $ mais n'a aucun tag. "
        f"On estime que {recovery_rate*100:.0f}% sont récupérables ({recoverable:.2f} $)."
    )

    details = [
        f"📊 Coût total : {total_cost:.2f} $",
        f"📊 Taux de récupération estimé : {recovery_rate*100:.0f}%",
        f"📊 Économie potentielle : {recoverable:.2f} $",
        "",
        "🔍 Diagnostic :",
        "Une ressource non taguée ne peut pas être attribuée à une équipe.",
        "Elle peut être légitime (juste mal configurée) ou du gaspillage pur.",
        "L'analyse statistique suggère qu'une partie est récupérable.",
    ]

    actions = [
        "1. Identifier l'équipe propriétaire via CloudTrail (qui l'a créée ?)",
        "2. Ajouter les tags requis (Team, Environment, Project)",
        "3. Si inutile, supprimer la ressource",
        "4. Mettre en place une policy de tagging obligatoire",
    ]

    return Insight(
        resource_id=resource_id,
        insight_type="untagged",
        title=title,
        summary=summary,
        details=details,
        actions=actions,
        confidence="medium",
    )


def _anomaly_insight(resource_id: str, context: dict) -> Insight:
    """Insight pour une anomalie de coût."""
    cost = context.get("cost", 0)
    median = context.get("median", 0)
    z_score = context.get("z_score", 0)
    day = context.get("day", "date inconnue")
    severity = context.get("severity", "moderate")

    severity_label = "CRITIQUE" if severity == "critical" else "MODÉRÉE"

    title = f"⚠️ Anomalie de coût {severity_label} : {resource_id}"

    summary = (
        f"Le {day}, cette ressource a coûté {cost:.2f} $ (médiane : {median:.2f} $). "
        f"Z-score : {z_score:.2f}. C'est statistiquement exceptionnel."
    )

    details = [
        f"📊 Coût du jour : {cost:.2f} $",
        f"📊 Médiane habituelle : {median:.2f} $",
        f"📊 Z-score : {z_score:.2f} (seuil : 3.0)",
        "",
        "🔍 Diagnostic :",
        "Un Z-score élevé indique un écart statistique majeur par rapport",
        "au comportement normal. Causes possibles :",
        "• Script de test qui a tourné en boucle",
        "• Déploiement raté (ex: 100 instances au lieu de 10)",
        "• Fuite de données ou attaque DDoS",
        "• Tâche de batch anormalement longue",
    ]

    actions = [
        "1. Vérifier les logs CloudTrail pour cette date",
        "2. Identifier les processus actifs sur cette ressource",
        "3. Si légitime, documenter la cause (ex: migration, test de charge)",
        "4. Si anomalie, corriger la cause racine et mettre en place des alertes",
    ]

    return Insight(
        resource_id=resource_id,
        insight_type="anomaly",
        title=title,
        summary=summary,
        details=details,
        actions=actions,
        confidence="high" if severity == "critical" else "medium",
    )


def _generate_llm_insight(
    resource_id: str,
    insight_type: str,
    context: dict,
) -> Insight:
    """Génère un insight via un LLM (optionnel).

    TODO: Implémenter l'appel API (OpenAI, Groq, etc.)
    Pour l'instant, on fallback sur le template.
    """
    # Placeholder pour l'intégration LLM future
    return _generate_template_insight(resource_id, insight_type, context)