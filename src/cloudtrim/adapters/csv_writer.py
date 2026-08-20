"""Adaptateur d'écriture : sérialise des lignes de coût en CSV au format CUR.

Séparé du domaine (qui reste pur) car c'est de l'entrée/sortie fichier. Le CSV
produit utilise les vrais en-têtes de colonnes d'un CUR, plus une colonne par tag
suivi (comme AWS le fait : une colonne fixe par clé de tag, vide si absente).
"""

from __future__ import annotations

import csv
from pathlib import Path

from cloudtrim.domain.cur import CUR_COLUMNS, TAG_KEYS, CostLineItem


def _tag_column(key: str) -> str:
    return f"resourceTags/user:{key}"


def cur_fieldnames() -> list[str]:
    """L'ordre des colonnes du CSV CUR (colonnes de base puis colonnes de tags)."""
    return list(CUR_COLUMNS.values()) + [_tag_column(k) for k in TAG_KEYS]


def _row(item: CostLineItem) -> dict[str, str]:
    row = {
        CUR_COLUMNS["usage_start_date"]: item.usage_start_date.isoformat(),
        CUR_COLUMNS["usage_end_date"]: item.usage_end_date.isoformat(),
        CUR_COLUMNS["usage_account_id"]: item.usage_account_id,
        CUR_COLUMNS["product_code"]: item.product_code,
        CUR_COLUMNS["product_name"]: item.product_name,
        CUR_COLUMNS["usage_type"]: item.usage_type,
        CUR_COLUMNS["operation"]: item.operation,
        CUR_COLUMNS["region"]: item.region,
        CUR_COLUMNS["resource_id"]: item.resource_id,
        CUR_COLUMNS["usage_amount"]: f"{item.usage_amount}",
        CUR_COLUMNS["unblended_cost"]: f"{item.unblended_cost}",
    }
    for key in TAG_KEYS:
        row[_tag_column(key)] = item.tags.get(key, "")
    return row


def write_cur_csv(items: list[CostLineItem], path: str | Path) -> Path:
    """Écrit les lignes de coût dans un fichier CSV au format CUR. Renvoie le chemin."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=cur_fieldnames())
        writer.writeheader()
        for item in items:
            writer.writerow(_row(item))
    return path
