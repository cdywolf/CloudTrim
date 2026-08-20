"""Tests de l'adaptateur DuckDB.

On vérifie que l'ingestion fonctionne et que les agrégations SQL renvoient
des résultats cohérents avec les données générées.
"""

import pytest

from cloudtrim.adapters.csv_writer import write_cur_csv
from cloudtrim.adapters.duckdb_repository import DuckDBRepository
from cloudtrim.domain.generator import generate_cur


@pytest.fixture
def sample_csv(tmp_path):
    """Génère un petit CUR synthétique et le sauvegarde en CSV."""
    items = generate_cur(days=10, num_resources=5, seed=1)
    csv_path = tmp_path / "test_cur.csv"
    write_cur_csv(items, csv_path)
    return csv_path


@pytest.fixture
def repo(tmp_path):
    """Crée un dépôt DuckDB temporaire."""
    db_path = tmp_path / "test.duckdb"
    repo = DuckDBRepository(db_path=db_path)
    yield repo
    repo.close()


def test_load_cur_csv_loads_all_lines(sample_csv, repo):
    """L'ingestion charge bien toutes les lignes du CSV."""
    count = repo.load_cur_csv(sample_csv)
    # 10 jours × (5 ressources + 1 orphelin) = 60 lignes
    assert count == 60


def test_load_cur_csv_fails_on_missing_file(repo):
    """L'ingestion échoue si le CSV n'existe pas."""
    with pytest.raises(FileNotFoundError):
        repo.load_cur_csv("inexistent.csv")


def test_cost_by_product_returns_results(sample_csv, repo):
    """La décomposition par service renvoie des résultats."""
    repo.load_cur_csv(sample_csv)
    results = repo.cost_by_product()
    assert len(results) > 0
    assert all("label" in r and "total_cost" in r for r in results)
    assert all(r["total_cost"] > 0 for r in results)


def test_cost_by_region_returns_results(sample_csv, repo):
    """La décomposition par région renvoie des résultats."""
    repo.load_cur_csv(sample_csv)
    results = repo.cost_by_region()
    assert len(results) > 0
    assert all("label" in r and "total_cost" in r for r in results)


def test_cost_by_team_includes_untagged(sample_csv, repo):
    """La décomposition par équipe inclut les dépenses non taguées."""
    repo.load_cur_csv(sample_csv)
    results = repo.cost_by_team()
    teams = [r["label"] for r in results]
    # Il doit y avoir au moins une équipe UNTAGGED (problème injecté)
    assert "UNTAGGED" in teams


def test_daily_cost_returns_one_row_per_day(sample_csv, repo):
    """L'évolution journalière renvoie une ligne par jour."""
    repo.load_cur_csv(sample_csv)
    results = repo.daily_cost()
    # 10 jours de données
    assert len(results) == 10
    assert all("day" in r and "daily_cost" in r for r in results)