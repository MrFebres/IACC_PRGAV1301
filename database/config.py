from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from settings import get_settings


@dataclass(frozen=True)
class DBConfig:
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

    @property
    def connection_kwargs(self) -> dict[str, object]:
        return {
            "charset": self.charset,
            "collation": self.collation,
            "database": self.database,
            "host": self.host,
            "password": self.password,
            "port": self.port,
            "raise_on_warnings": self.raise_on_warnings,
            "user": self.user,
        }

    @property
    def is_configured(self) -> bool:
        return bool(self.database and self.user)


@lru_cache(maxsize=1)
def get_database_config() -> DBConfig:
    database_settings = get_settings().database
    return DBConfig(
        charset=database_settings.charset,
        collation=database_settings.collation,
        database=database_settings.database,
        host=database_settings.host,
        password=database_settings.password,
        pool_name=database_settings.pool_name,
        pool_size=database_settings.pool_size,
        port=database_settings.port,
        raise_on_warnings=database_settings.raise_on_warnings,
        user=database_settings.user,
    )