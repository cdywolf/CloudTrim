"""Modèle de domaine d'une ligne de coût (CUR).

Une ligne de coût représente une unité d'usage AWS sur une période donnée, pour
un montant précis. C'est la matière première de toute l'analyse FinOps. Ce module
est PUR : aucune dépendance à DuckDB, au réseau ou au disque.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

# Les clés de tags qu'on suit (colonnes fixes, comme dans un vrai CUR).
TAG_KEYS: tuple[str, ...] = ("Team", "Environment", "Project")


class CostLineItem(BaseModel):
    """Une ligne de facturation détaillée, au sens du Cost and Usage Report."""

    usage_start_date: datetime = Field(description="Début de la période d'usage.")
    usage_end_date: datetime = Field(description="Fin de la période d'usage.")
    usage_account_id: str = Field(description="Compte AWS (12 chiffres).")
    product_code: str = Field(description="Code produit AWS, ex. AmazonEC2.")
    product_name: str = Field(description="Nom lisible du service.")
    usage_type: str = Field(description="Type d'usage facturé, ex. BoxUsage:t3.medium.")
    operation: str = Field(description="Opération, ex. RunInstances.")
    region: str = Field(description="Région AWS, ex. us-east-1.")
    resource_id: str = Field(description="Identifiant de la ressource concernée.")
    usage_amount: float = Field(ge=0, description="Quantité consommée.")
    unblended_cost: float = Field(ge=0, description="Coût non mélangé (ce qui est payé).")
    tags: dict[str, str] = Field(
        default_factory=dict,
        description="Étiquettes clé-valeur. Vide = dépense non taguée (à repérer).",
    )

    @property
    def is_untagged(self) -> bool:
        """Vrai si la ligne ne porte aucun des tags suivis (dépense non attribuable)."""
        return not any(self.tags.get(k) for k in TAG_KEYS)


# Correspondance vers les en-têtes de colonnes d'un vrai CUR (pour l'export CSV).
CUR_COLUMNS: dict[str, str] = {
    "usage_start_date": "lineItem/UsageStartDate",
    "usage_end_date": "lineItem/UsageEndDate",
    "usage_account_id": "lineItem/UsageAccountId",
    "product_code": "lineItem/ProductCode",
    "product_name": "product/ProductName",
    "usage_type": "lineItem/UsageType",
    "operation": "lineItem/Operation",
    "region": "product/region",
    "resource_id": "lineItem/ResourceId",
    "usage_amount": "lineItem/UsageAmount",
    "unblended_cost": "lineItem/UnblendedCost",
}
