from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
import logging
from typing import cast

from mysql.connector import Error, errorcode
from mysql.connector.pooling import PooledMySQLConnection

from database.connection import get_connection, get_cursor
from repositories.shipment_repository import (
    DuplicateTrackingNumberError,
    ShipmentMutation,
    ShipmentNotFoundError,
    ShipmentRecord,
    ShipmentRepository,
    ShipmentSummary,
)


logger = logging.getLogger(__name__)


class MySQLShipmentRepository(ShipmentRepository):
    def create_shipment(self, payload: ShipmentMutation) -> ShipmentRecord:
        query: str = (
            "INSERT INTO shipments (destination_city, origin_city, status, tracking_number) "
            "VALUES (%s, %s, %s, %s)"
        )

        try:
            with get_connection() as connection:
                with get_cursor(connection) as cursor:
                    cursor.execute(
                        query,
                        (
                            payload.destination_city,
                            payload.origin_city,
                            payload.status,
                            payload.tracking_number,
                        ),
                    )
                    shipment_id: int = int(cursor.lastrowid)
                connection.commit()
                return self._fetch_shipment_by_id(connection, shipment_id)
        except Error as exc:
            self._raise_known_error(exc)
            logger.exception("Unexpected database error creating shipment")
            raise

    def list_shipments(self) -> tuple[ShipmentRecord, ...]:
        query: str = (
            "SELECT created_at, destination_city, id, origin_city, status, tracking_number, updated_at "
            "FROM shipments ORDER BY created_at DESC, id DESC"
        )

        try:
            with get_connection() as connection, get_cursor(connection, dictionary=True) as cursor:
                cursor.execute(query)
                rows = cursor.fetchall()
                return tuple(self._map_shipment_record(row) for row in rows)
        except Error:
            logger.exception("Unexpected database error listing shipments")
            raise

    def summarize_shipments(self) -> tuple[ShipmentSummary, ...]:
        query: str = (
            "SELECT COUNT(*) AS shipment_count, status FROM shipments "
            "GROUP BY status ORDER BY status ASC"
        )

        with get_connection() as connection, get_cursor(connection, dictionary=True) as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
            return tuple(self._map_shipment_summary(row) for row in rows)

    def update_shipment(self, shipment_id: int, payload: ShipmentMutation) -> ShipmentRecord:
        query: str = (
            "UPDATE shipments SET destination_city = %s, origin_city = %s, status = %s, "
            "tracking_number = %s WHERE id = %s"
        )

        try:
            with get_connection() as connection:
                with get_cursor(connection) as cursor:
                    cursor.execute(
                        query,
                        (
                            payload.destination_city,
                            payload.origin_city,
                            payload.status,
                            payload.tracking_number,
                            shipment_id,
                        ),
                    )
                connection.commit()
                return self._fetch_shipment_by_id(connection, shipment_id)
        except Error as exc:
            self._raise_known_error(exc)
            logger.exception("Unexpected database error updating shipment %s", shipment_id)
            raise

    def _fetch_shipment_by_id(
        self,
        connection: PooledMySQLConnection,
        shipment_id: int,
    ) -> ShipmentRecord:
        query: str = (
            "SELECT created_at, destination_city, id, origin_city, status, tracking_number, updated_at "
            "FROM shipments WHERE id = %s"
        )

        with get_cursor(connection, dictionary=True) as cursor:
            cursor.execute(query, (shipment_id,))
            row = cursor.fetchone()

        if row is None:
            raise ShipmentNotFoundError(f"No shipment exists with id {shipment_id}.")

        return self._map_shipment_record(row)

    @staticmethod
    def _map_shipment_record(row: Mapping[str, object]) -> ShipmentRecord:
        return ShipmentRecord(
            created_at=cast(datetime | None, row["created_at"]),
            destination_city=cast(str, row["destination_city"]),
            id=int(row["id"]),
            origin_city=cast(str, row["origin_city"]),
            status=cast(str, row["status"]),
            tracking_number=cast(str, row["tracking_number"]),
            updated_at=cast(datetime | None, row["updated_at"]),
        )

    @staticmethod
    def _map_shipment_summary(row: Mapping[str, object]) -> ShipmentSummary:
        return ShipmentSummary(
            shipment_count=int(row["shipment_count"]),
            status=cast(str, row["status"]),
        )

    @staticmethod
    def _raise_known_error(exc: Error) -> None:
        if exc.errno == errorcode.ER_DUP_ENTRY:
            raise DuplicateTrackingNumberError(
                "The tracking number is already registered."
            ) from exc