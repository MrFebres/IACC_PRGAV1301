from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT: Path = Path(__file__).resolve().parent


def load_environment(*, env_file: Path | None = None) -> None:
    dotenv_path: Path = env_file or PROJECT_ROOT / ".env"
    load_dotenv(dotenv_path=dotenv_path, override=False)


def _get_int(name: str, default: int) -> int:
    raw_value: str | None = os.getenv(name)
    if raw_value is None or raw_value == "":
        return default
    try:
        return int(raw_value)
    except ValueError as exc:
        raise ValueError(f"The environment variable '{name}' must be an integer.") from exc


def _get_bool(name: str, default: bool) -> bool:
    raw_value: str | None = os.getenv(name)
    if raw_value is None or raw_value == "":
        return default

    normalized_value: str = raw_value.strip().lower()
    if normalized_value in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized_value in {"0", "false", "no", "n", "off"}:
        return False
    raise ValueError(f"The environment variable '{name}' must be a boolean value.")


@dataclass(frozen=True)
class AppConfig:
    height: int
    title: str
    width: int

    @property
    def window_geometry(self) -> str:
        return f"{self.width}x{self.height}"


@dataclass(frozen=True)
class DatabaseSettings:
    charset: str
    collation: str
    database: str
    host: str
    password: str
    pool_name: str
    pool_size: int
    port: int
    raise_on_warnings: bool
    user: str


@dataclass(frozen=True)
class Settings:
    app: AppConfig
    database: DatabaseSettings


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    load_environment()

    return Settings(
        app=AppConfig(
            height=_get_int("APP_HEIGHT", 480),
            title=os.getenv("APP_TITLE", "Sistema de Logistica"),
            width=_get_int("APP_WIDTH", 800),
        ),
        database=DatabaseSettings(
            charset=os.getenv("MYSQL_CHARSET", "utf8mb4"),
            collation=os.getenv("MYSQL_COLLATION", "utf8mb4_unicode_ci"),
            database=os.getenv("MYSQL_DATABASE", ""),
            host=os.getenv("MYSQL_HOST", "127.0.0.1"),
            password=os.getenv("MYSQL_PASSWORD", ""),
            pool_name=os.getenv("MYSQL_POOL_NAME", "logistics_pool"),
            pool_size=_get_int("MYSQL_POOL_SIZE", 5),
            port=_get_int("MYSQL_PORT", 3306),
            raise_on_warnings=_get_bool("MYSQL_RAISE_ON_WARNINGS", True),
            user=os.getenv("MYSQL_USER", ""),
        ),
    )