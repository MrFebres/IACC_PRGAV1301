from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime
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
    ShipmentSchemaCompatibilityError,
    ShipmentSummary,
)


logger = logging.getLogger(__name__)


class MySQLShipmentRepository(ShipmentRepository):
    ESTIMATED_DELIVERY_DATE_COLUMN_NAME: str = "estimated_delivery_date"
    ESTIMATED_DELIVERY_DATE_COMPATIBILITY_QUERY: str = (
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_schema = DATABASE() AND table_name = %s AND column_name = %s "
        "LIMIT 1"
    )
    ESTIMATED_DELIVERY_DATE_REMEDIATION_SQL: str = (
        "ALTER TABLE shipments ADD COLUMN estimated_delivery_date "
        "DATE NULL DEFAULT NULL AFTER destination_city"
    )
    SHIPMENTS_TABLE_NAME: str = "shipments"

    def __init__(self) -> None:
        self._estimated_delivery_date_schema_verified: bool = False

    def create_shipment(self, payload: ShipmentMutation) -> ShipmentRecord:
        query: str = (
            "INSERT INTO shipments "
            "(destination_city, estimated_delivery_date, origin_city, status, tracking_number) "
            "VALUES (%s, %s, %s, %s, %s)"
        )

        try:
            with get_connection() as connection:
                self._ensure_estimated_delivery_date_schema(connection)
                with get_cursor(connection) as cursor:
                    cursor.execute(
                        query,
                        (
                            payload.destination_city,
                            payload.estimated_delivery_date,
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
            "SELECT created_at, destination_city, estimated_delivery_date, id, origin_city, "
            "status, tracking_number, updated_at "
            "FROM shipments ORDER BY created_at DESC, id DESC"
        )

        try:
            with get_connection() as connection:
                self._ensure_estimated_delivery_date_schema(connection)
                with get_cursor(connection, dictionary=True) as cursor:
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
            "UPDATE shipments SET destination_city = %s, estimated_delivery_date = %s, "
            "origin_city = %s, status = %s, tracking_number = %s WHERE id = %s"
        )

        try:
            with get_connection() as connection:
                self._ensure_estimated_delivery_date_schema(connection)
                with get_cursor(connection) as cursor:
                    cursor.execute(
                        query,
                        (
                            payload.destination_city,
                            payload.estimated_delivery_date,
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

    def delete_shipment(self, shipment_id: int) -> None:
        query: str = "DELETE FROM shipments WHERE id = %s"

        try:
            with get_connection() as connection:
                with get_cursor(connection) as cursor:
                    cursor.execute(query, (shipment_id,))
                    if cursor.rowcount == 0:
                        raise ShipmentNotFoundError(
                            f"No shipment exists with id {shipment_id}."
                        )
                connection.commit()
        except Error as exc:
            self._raise_known_error(exc)
            logger.exception("Unexpected database error deleting shipment %s", shipment_id)
            raise

    def _fetch_shipment_by_id(
        self,
        connection: PooledMySQLConnection,
        shipment_id: int,
    ) -> ShipmentRecord:
        query: str = (
            "SELECT created_at, destination_city, estimated_delivery_date, id, origin_city, "
            "status, tracking_number, updated_at "
            "FROM shipments WHERE id = %s"
        )

        self._ensure_estimated_delivery_date_schema(connection)
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
            estimated_delivery_date=cast(date | None, row["estimated_delivery_date"]),
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

    def _ensure_estimated_delivery_date_schema(
        self,
        connection: PooledMySQLConnection,
    ) -> None:
        if self._estimated_delivery_date_schema_verified:
            return

        if self._has_estimated_delivery_date_column(connection):
            self._estimated_delivery_date_schema_verified = True
            return

        logger.warning(
            "Legacy shipments schema detected. Attempting to add %s.",
            self.ESTIMATED_DELIVERY_DATE_COLUMN_NAME,
        )
        try:
            with get_cursor(connection) as cursor:
                cursor.execute(self.ESTIMATED_DELIVERY_DATE_REMEDIATION_SQL)
        except Error as exc:
            if exc.errno == errorcode.ER_DUP_FIELDNAME:
                if self._has_estimated_delivery_date_column(connection):
                    self._estimated_delivery_date_schema_verified = True
                    return

            logger.warning(
                "Shipment schema compatibility repair failed: %s",
                exc,
            )
            raise ShipmentSchemaCompatibilityError(
                detail=(
                    "No fue posible agregar automaticamente la columna "
                    "estimated_delivery_date a shipments."
                ),
                remediation_sql=self.ESTIMATED_DELIVERY_DATE_REMEDIATION_SQL,
            ) from exc

        connection.commit()
        self._estimated_delivery_date_schema_verified = True

    def _has_estimated_delivery_date_column(
        self,
        connection: PooledMySQLConnection,
    ) -> bool:
        with get_cursor(connection, dictionary=True) as cursor:
            cursor.execute(
                self.ESTIMATED_DELIVERY_DATE_COMPATIBILITY_QUERY,
                (
                    self.SHIPMENTS_TABLE_NAME,
                    self.ESTIMATED_DELIVERY_DATE_COLUMN_NAME,
                ),
            )
            return cursor.fetchone() is not None

    @staticmethod
    def _raise_known_error(exc: Error) -> None:
        if exc.errno == errorcode.ER_DUP_ENTRY:
            raise DuplicateTrackingNumberError(
                "The tracking number is already registered."
            ) from exc