"""Adaptateur DuckDB : ingestion du CUR et agrégations SQL de base.

DuckDB est une base analytique qui vit dans un fichier. On l'utilise pour
charger le CSV CUR et exécuter des requêtes SQL d'agrégation (décomposition
des coûts par service, région, tag, jour).
"""

from __future__ import annotations

from pathlib import Path

import duckdb


class DuckDBRepository:
    """Accès aux données CUR via DuckDB."""

    def __init__(self, db_path: str | Path = "data/cloudtrim.duckdb"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = duckdb.connect(str(self.db_path))

    def load_cur_csv(self, csv_path: str | Path) -> int:
        """Charge un CSV CUR dans la table `cur`. Renvoie le nombre de lignes."""
        csv_path = Path(csv_path)
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV introuvable : {csv_path}")

        # Supprime l'ancienne table si elle existe
        self.conn.execute("DROP TABLE IF EXISTS cur")

        # Crée la table à partir du CSV (DuckDB lit directement le CSV)
        self.conn.execute(f"CREATE TABLE cur AS SELECT * FROM '{csv_path}'")

        # Compte les lignes chargées
        result = self.conn.execute("SELECT COUNT(*) FROM cur").fetchone()
        return result[0] if result else 0

    def cost_by_product(self) -> list[dict]:
        query = """
            SELECT "product/ProductName" AS label,
                   SUM("lineItem/UnblendedCost") AS total_cost
            FROM cur
            GROUP BY label
            ORDER BY total_cost DESC
        """
        rows = self.conn.execute(query).fetchall()
        return [{"label": r[0], "total_cost": r[1]} for r in rows]

    def cost_by_region(self) -> list[dict]:
        query = """
            SELECT "product/region" AS label,
                   SUM("lineItem/UnblendedCost") AS total_cost
            FROM cur
            GROUP BY label
            ORDER BY total_cost DESC
        """
        rows = self.conn.execute(query).fetchall()
        return [{"label": r[0], "total_cost": r[1]} for r in rows]

    def cost_by_team(self) -> list[dict]:
        query = """
            SELECT COALESCE("resourceTags/user:Team", 'UNTAGGED') AS label,
                   SUM("lineItem/UnblendedCost") AS total_cost
            FROM cur
            GROUP BY label
            ORDER BY total_cost DESC
        """
        rows = self.conn.execute(query).fetchall()
        return [{"label": r[0], "total_cost": r[1]} for r in rows]

    def daily_cost(self) -> list[dict]:
        """Évolution journalière des coûts."""
        query = """
            SELECT DATE("lineItem/UsageStartDate") AS day,
                   SUM("lineItem/UnblendedCost") AS daily_cost
            FROM cur
            GROUP BY day
            ORDER BY day
        """
        rows = self.conn.execute(query).fetchall()
        return [{"day": str(r[0]), "daily_cost": r[1]} for r in rows]

    def close(self):
        """Ferme la connexion DuckDB."""
        self.conn.close()

    def get_untagged_resources_daily_costs(self) -> dict[str, list[float]]:
        """Renvoie les coûts journaliers des ressources non taguées.

        Returns:
            Dict {resource_id: [coût_jour_1, coût_jour_2, ...]}
        """
        query = """
            SELECT "lineItem/ResourceId" AS resource_id,
                   DATE("lineItem/UsageStartDate") AS day,
                   SUM("lineItem/UnblendedCost") AS daily_cost
            FROM cur
            WHERE "resourceTags/user:Team" IS NULL
              AND "resourceTags/user:Environment" IS NULL
              AND "resourceTags/user:Project" IS NULL
            GROUP BY resource_id, day
            ORDER BY resource_id, day
        """
        rows = self.conn.execute(query).fetchall()

        result: dict[str, list[float]] = {}
        for resource_id, day, daily_cost in rows:
            if resource_id not in result:
                result[resource_id] = []
            result[resource_id].append(daily_cost)

        return result

    def get_orphan_resources_daily_costs(self) -> dict[str, list[float]]:
        """Renvoie les coûts journaliers des ressources orphelines (volumes EBS).

        Returns:
            Dict {resource_id: [coût_jour_1, coût_jour_2, ...]}
        """
        query = """
            SELECT "lineItem/ResourceId" AS resource_id,
                   DATE("lineItem/UsageStartDate") AS day,
                   SUM("lineItem/UnblendedCost") AS daily_cost
            FROM cur
            WHERE "lineItem/UsageType" LIKE '%VolumeUsage%'
            GROUP BY resource_id, day
            ORDER BY resource_id, day
        """
        rows = self.conn.execute(query).fetchall()

        result: dict[str, list[float]] = {}
        for resource_id, day, daily_cost in rows:
            if resource_id not in result:
                result[resource_id] = []
            result[resource_id].append(daily_cost)

        return result

    def get_all_resources_daily_costs(self) -> dict[str, list[tuple[str, float]]]:
        """Renvoie les coûts journaliers de toutes les ressources.

        Returns:
            Dict {resource_id: [(day, cost), ...]}
        """
        query = """
            SELECT "lineItem/ResourceId" AS resource_id,
                   DATE("lineItem/UsageStartDate") AS day,
                   SUM("lineItem/UnblendedCost") AS daily_cost
            FROM cur
            GROUP BY resource_id, day
            ORDER BY resource_id, day
        """
        rows = self.conn.execute(query).fetchall()

        result: dict[str, list[tuple[str, float]]] = {}
        for resource_id, day, daily_cost in rows:
            if resource_id not in result:
                result[resource_id] = []
            result[resource_id].append((str(day), daily_cost))

        return result