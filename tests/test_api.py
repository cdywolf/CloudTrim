"""Tests de l'API FastAPI."""

import pytest
from fastapi.testclient import TestClient

from cloudtrim.adapters.csv_writer import write_cur_csv
from cloudtrim.adapters.duckdb_repository import DuckDBRepository
from cloudtrim.api.app import app
from cloudtrim.api.dependencies import set_db_path
from cloudtrim.domain.generator import generate_cur


@pytest.fixture
def test_db(tmp_path):
    """Crée une base de test avec des données."""
    items = generate_cur(days=10, num_resources=5, seed=1)
    csv_path = tmp_path / "test_cur.csv"
    write_cur_csv(items, csv_path)
    
    db_path = tmp_path / "test.duckdb"
    repo = DuckDBRepository(db_path=db_path)
    repo.load_cur_csv(csv_path)
    repo.close()
    
    set_db_path(db_path)
    return db_path


@pytest.fixture
def client(test_db):
    """Client de test FastAPI."""
    return TestClient(app)


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_cost_by_product(client):
    response = client.get("/api/costs/by-product")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "label" in data[0]
    assert "total_cost" in data[0]


def test_summary(client):
    response = client.get("/api/summary")
    assert response.status_code == 200
    data = response.json()
    assert "total_cost" in data
    assert "untagged_savings_lower" in data
    assert "anomalies_count" in data


def test_anomalies(client):
    response = client.get("/api/anomalies")
    assert response.status_code == 200
    data = response.json()
    assert "total_anomalies" in data
    assert "anomalies" in data


def test_dashboard_home(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "CloudTrim" in response.text