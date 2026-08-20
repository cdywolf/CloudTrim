"""Dépendances FastAPI : injection du repository DuckDB."""

from __future__ import annotations

from pathlib import Path

from cloudtrim.adapters.duckdb_repository import DuckDBRepository

# Chemin par défaut du fichier DuckDB
DEFAULT_DB_PATH = Path("data/cloudtrim.duckdb")

# Instance globale du repository (partagée entre les requêtes)
_repository: DuckDBRepository | None = None


def get_repository() -> DuckDBRepository:
    """Retourne l'instance du repository DuckDB."""
    global _repository
    if _repository is None:
        _repository = DuckDBRepository(db_path=DEFAULT_DB_PATH)
    return _repository


def set_db_path(path: str | Path) -> None:
    """Configure le chemin du fichier DuckDB (appelé au démarrage)."""
    global _repository, DEFAULT_DB_PATH
    DEFAULT_DB_PATH = Path(path)
    _repository = None  # Réinitialise pour forcer la recréation