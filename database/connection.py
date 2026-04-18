from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Generator

from mysql.connector import pooling
from mysql.connector.cursor import MySQLCursor
from mysql.connector.pooling import MySQLConnectionPool, PooledMySQLConnection

from database.config import get_database_config


logger = logging.getLogger(__name__)


class DatabaseConfigurationError(RuntimeError):
    """Raised when the database settings are incomplete."""


_pool: MySQLConnectionPool | None = None


def _create_pool() -> MySQLConnectionPool:
    database_config = get_database_config()
    if database_config.is_configured:
        return pooling.MySQLConnectionPool(
            pool_name=database_config.pool_name,
            pool_reset_session=True,
            pool_size=database_config.pool_size,
            **database_config.connection_kwargs,
        )

    logger.debug("Database pool creation skipped because configuration is incomplete.")
    raise DatabaseConfigurationError(
        "Configure MYSQL_DATABASE and MYSQL_USER before opening a database connection."
    )


def get_pool() -> MySQLConnectionPool:
    global _pool

    if _pool is not None:
        return _pool

    _pool = _create_pool()
    return _pool


@contextmanager
def get_connection() -> Generator[PooledMySQLConnection, None, None]:
    connection = get_pool().get_connection()
    try:
        yield connection
    finally:
        connection.close()


@contextmanager
def get_cursor(
    connection: PooledMySQLConnection,
    *,
    buffered: bool = True,
    dictionary: bool = False,
) -> Generator[MySQLCursor, None, None]:
    cursor = connection.cursor(
        buffered=buffered,
        dictionary=dictionary,
    )
    try:
        yield cursor
    finally:
        cursor.close()