"""Tests du générateur CUR.

On vérifie la mécanique (comptage, reproductibilité) et surtout que les problèmes
injectés (vérité terrain) sont bien présents : dépenses non taguées, pic de coût,
ressource orpheline. C'est ce qui nous permettra plus tard de valider le moteur.
"""

from collections import defaultdict

import pytest

from cloudtrim.domain.cur import CostLineItem
from cloudtrim.domain.generator import generate_cur


def test_line_item_count_matches_days_and_resources():
    # num_resources ressources + 1 ressource orpheline injectée, sur `days` jours.
    items = generate_cur(days=10, num_resources=15, seed=1)
    assert len(items) == 10 * (15 + 1)
    assert all(isinstance(i, CostLineItem) for i in items)


def test_reproducible_with_same_seed():
    a = generate_cur(days=7, num_resources=12, seed=7)
    b = generate_cur(days=7, num_resources=12, seed=7)
    assert [i.unblended_cost for i in a] == [i.unblended_cost for i in b]


def test_injects_untagged_spend():
    items = generate_cur(days=5, num_resources=20, seed=3)
    untagged = [i for i in items if i.is_untagged]
    # Il DOIT exister des lignes non taguées (problème injecté n°1).
    assert len(untagged) > 0


def test_injects_orphan_resource():
    items = generate_cur(days=5, num_resources=10, seed=3, inject_orphan=True)
    orphans = [i for i in items if i.resource_id.startswith("vol-")]
    assert len(orphans) == 5  # présente chaque jour
    assert all(o.is_untagged for o in orphans)  # et non taguée


def test_injects_cost_anomaly():
    items = generate_cur(days=30, num_resources=15, seed=5, inject_anomaly=True)
    daily_total = defaultdict(float)
    for i in items:
        daily_total[i.usage_start_date.date()] += i.unblended_cost
    totals = sorted(daily_total.values())
    median = totals[len(totals) // 2]
    # Le pic injecté doit créer un jour nettement au-dessus de la médiane.
    assert max(totals) > 2 * median


def test_no_anomaly_when_disabled():
    items = generate_cur(days=30, num_resources=15, seed=5, inject_anomaly=False)
    daily_total = defaultdict(float)
    for i in items:
        daily_total[i.usage_start_date.date()] += i.unblended_cost
    totals = sorted(daily_total.values())
    median = totals[len(totals) // 2]
    # Sans anomalie, les totaux journaliers restent proches les uns des autres.
    assert max(totals) < 1.5 * median


@pytest.mark.parametrize("bad", [(0, 5), (5, 0), (-1, 5)])
def test_rejects_invalid_sizes(bad):
    days, resources = bad
    with pytest.raises(ValueError):
        generate_cur(days=days, num_resources=resources)
