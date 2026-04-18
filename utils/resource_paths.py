from __future__ import annotations

from pathlib import Path


PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent


def get_project_root() -> Path:
    return PROJECT_ROOT


def get_sql_path(filename: str) -> Path:
    return get_project_root() / "sql" / filename