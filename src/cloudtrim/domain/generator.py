"""Générateur de données CUR synthétiques (pur, reproductible).

Produit un jeu de lignes de coût réaliste, et surtout y INJECTE volontairement
des problèmes (dépenses non taguées, pic de coût anormal, ressource orpheline).
Comme on sait ce qu'on a caché dans les données, on pourra vérifier plus tard
que le moteur d'analyse les retrouve : ces problèmes sont notre vérité terrain.

La génération est reproductible : à graine constante, mêmes données.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from cloudtrim.domain.cur import CostLineItem

# Catalogue de services : (product_code, product_name, usage_type, operation, coût/jour de base)
_SERVICES: list[tuple[str, str, str, str, float]] = [
    ("AmazonEC2", "Amazon Elastic Compute Cloud", "BoxUsage:t3.medium", "RunInstances", 1.15),
    ("AmazonEC2", "Amazon Elastic Compute Cloud", "BoxUsage:m5.large", "RunInstances", 2.30),
    ("AmazonRDS", "Amazon Relational Database Service", "InstanceUsage:db.t3.medium", "CreateDBInstance", 1.80),
    ("AmazonS3", "Amazon Simple Storage Service", "TimedStorage-ByteHrs", "StandardStorage", 0.42),
    ("AWSLambda", "AWS Lambda", "Lambda-GB-Second", "Invoke", 0.15),
    ("AmazonCloudWatch", "Amazon CloudWatch", "TimedStorage-ByteHrs", "MetricStorage", 0.08),
]

_REGIONS = ["us-east-1", "eu-west-1", "eu-central-1"]
_ACCOUNTS = ["111122223333", "444455556666"]
_TEAMS = ["data", "platform", "web", "ml"]
_ENVIRONMENTS = ["prod", "staging", "dev"]
_PROJECTS = ["atlas", "orion", "nova"]


class _Resource:
    """Une ressource fictive stable dans le temps (mêmes attributs chaque jour)."""

    def __init__(self, rid, code, name, usage_type, operation, region, account, base_cost, tags):
        self.rid = rid
        self.code = code
        self.name = name
        self.usage_type = usage_type
        self.operation = operation
        self.region = region
        self.account = account
        self.base_cost = base_cost
        self.tags = tags


def _build_resources(rng: random.Random, count: int, untagged_ratio: float) -> list[_Resource]:
    resources: list[_Resource] = []
    for i in range(count):
        code, name, usage_type, operation, base = rng.choice(_SERVICES)
        # Une fraction des ressources est laissée SANS tag (problème injecté n°1).
        if rng.random() < untagged_ratio:
            tags: dict[str, str] = {}
        else:
            tags = {
                "Team": rng.choice(_TEAMS),
                "Environment": rng.choice(_ENVIRONMENTS),
                "Project": rng.choice(_PROJECTS),
            }
        resources.append(
            _Resource(
                rid=f"resource-{i:04d}",
                code=code,
                name=name,
                usage_type=usage_type,
                operation=operation,
                region=rng.choice(_REGIONS),
                account=rng.choice(_ACCOUNTS),
                base_cost=base * rng.uniform(0.6, 1.6),
                tags=tags,
            )
        )
    return resources


def generate_cur(
    days: int = 30,
    num_resources: int = 20,
    seed: int | None = 42,
    untagged_ratio: float = 0.2,
    inject_anomaly: bool = True,
    inject_orphan: bool = True,
) -> list[CostLineItem]:
    """Génère un jeu de lignes de coût synthétiques avec problèmes injectés.

    Args:
        days: Nombre de jours couverts.
        num_resources: Nombre de ressources distinctes.
        seed: Graine pour la reproductibilité.
        untagged_ratio: Proportion de ressources sans tag (problème injecté).
        inject_anomaly: Ajoute un pic de coût anormal un jour donné.
        inject_orphan: Ajoute une ressource orpheline (volume EBS non attaché).

    Returns:
        La liste des lignes de coût, une par ressource et par jour.
    """
    if days < 1 or num_resources < 1:
        raise ValueError("days et num_resources doivent être >= 1.")

    rng = random.Random(seed)
    resources = _build_resources(rng, num_resources, untagged_ratio)

    # Problème injecté n°2 : le pic vise la ressource la plus coûteuse, pour
    # produire une anomalie franchement visible (et non noyée dans le bruit).
    anomaly_resource = max(resources, key=lambda r: r.base_cost) if inject_anomaly else None

    # Problème injecté n°3 : une ressource orpheline (volume EBS non attaché,
    # sans tag, qui coûte tous les jours pour rien).
    if inject_orphan:
        resources.append(
            _Resource(
                rid="vol-0deadbeef0000",
                code="AmazonEC2",
                name="Amazon Elastic Compute Cloud",
                usage_type="EBS:VolumeUsage.gp3",
                operation="CreateVolume",
                region="us-east-1",
                account="111122223333",
                base_cost=3.10,
                tags={},
            )
        )

    anomaly_day = rng.randrange(days) if inject_anomaly else -1

    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    items: list[CostLineItem] = []
    for day in range(days):
        day_start = start + timedelta(days=day)
        day_end = day_start + timedelta(days=1)
        for res in resources:
            cost = res.base_cost * rng.uniform(0.85, 1.15)
            if res is anomaly_resource and day == anomaly_day:
                cost *= 25  # le pic anormal
            items.append(
                CostLineItem(
                    usage_start_date=day_start,
                    usage_end_date=day_end,
                    usage_account_id=res.account,
                    product_code=res.code,
                    product_name=res.name,
                    usage_type=res.usage_type,
                    operation=res.operation,
                    region=res.region,
                    resource_id=res.rid,
                    usage_amount=round(rng.uniform(1, 100), 2),
                    unblended_cost=round(cost, 4),
                    tags=res.tags,
                )
            )
    return items
