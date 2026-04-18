from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime

import pytest
from mysql.connector import errorcode
from mysql.connector.errors import IntegrityError, OperationalError

from database.connection import DatabaseConfigurationError
import repositories.mysql_shipment_repository as shipment_module
from repositories.mysql_shipment_repository import MySQLShipmentRepository
from repositories.shipment_repository import (
    DuplicateTrackingNumberError,
    ShipmentMutation,
    ShipmentNotFoundError,
    ShipmentSummary,
)


class FakeCursor:
    def __init__(
        self,
        *,
        execute_error: Exception | None = None,
        fetchall_result: list[dict[str, object]] | None = None,
        fetchone_result: dict[str, object] | None = None,
        lastrowid: int = 0,
    ) -> None:
        self.execute_calls: list[tuple[str, tuple[object, ...] | None]] = []
        self.execute_error = execute_error
        self.fetchall_result = fetchall_result or []
        self.fetchone_result = fetchone_result
        self.lastrowid = lastrowid

    def close(self) -> None:
        return None

    def execute(self, query: str, params: tuple[object, ...] | None = None) -> None:
        self.execute_calls.append((query, params))
        if self.execute_error is not None:
            raise self.execute_error

    def fetchall(self) -> list[dict[str, object]]:
        return self.fetchall_result

    def fetchone(self) -> dict[str, object] | None:
        return self.fetchone_result


class FakeConnection:
    def __init__(self) -> None:
        self.commit_calls: int = 0

    def close(self) -> None:
        return None

    def commit(self) -> None:
        self.commit_calls += 1


def patch_database(
    monkeypatch: pytest.MonkeyPatch,
    *,
    cursors: list[FakeCursor],
) -> FakeConnection:
    connection = FakeConnection()
    cursor_iter = iter(cursors)

    @contextmanager
    def fake_get_connection() -> FakeConnection:
        yield connection

    @contextmanager
    def fake_get_cursor(_connection: FakeConnection, **_kwargs: object) -> FakeCursor:
        yield next(cursor_iter)

    monkeypatch.setattr(shipment_module, "get_connection", fake_get_connection)
    monkeypatch.setattr(shipment_module, "get_cursor", fake_get_cursor)
    return connection


def test_create_shipment_inserts_and_fetches_created_row(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = ShipmentMutation(
        destination_city="Valparaiso",
        estimated_delivery_date=date(2026, 5, 1),
        origin_city="Santiago",
        status="pendiente",
        tracking_number="TRK-001",
    )
    created_at = datetime(2026, 4, 18, 9, 30)
    insert_cursor = FakeCursor(lastrowid=7)
    select_cursor = FakeCursor(
        fetchone_result={
            "created_at": created_at,
            "destination_city": "Valparaiso",
            "estimated_delivery_date": date(2026, 5, 1),
            "id": 7,
            "origin_city": "Santiago",
            "status": "pendiente",
            "tracking_number": "TRK-001",
            "updated_at": created_at,
        }
    )

    connection = patch_database(monkeypatch, cursors=[insert_cursor, select_cursor])

    repository = MySQLShipmentRepository()
    shipment = repository.create_shipment(payload)

    assert shipment.id == 7
    assert shipment.estimated_delivery_date == date(2026, 5, 1)
    assert shipment.tracking_number == "TRK-001"
    assert connection.commit_calls == 1
    assert insert_cursor.execute_calls == [
        (
            "INSERT INTO shipments "
            "(destination_city, estimated_delivery_date, origin_city, status, tracking_number) "
            "VALUES (%s, %s, %s, %s, %s)",
            ("Valparaiso", date(2026, 5, 1), "Santiago", "pendiente", "TRK-001"),
        )
    ]
    assert select_cursor.execute_calls == [
        (
            "SELECT created_at, destination_city, estimated_delivery_date, id, origin_city, "
            "status, tracking_number, updated_at "
            "FROM shipments WHERE id = %s",
            (7,),
        )
    ]


def test_list_shipments_returns_records_in_query_order(monkeypatch: pytest.MonkeyPatch) -> None:
    cursor = FakeCursor(
        fetchall_result=[
            {
                "created_at": datetime(2026, 4, 18, 10, 0),
                "destination_city": "Concepcion",
                "estimated_delivery_date": date(2026, 4, 23),
                "id": 2,
                "origin_city": "Temuco",
                "status": "en_transito",
                "tracking_number": "TRK-002",
                "updated_at": datetime(2026, 4, 18, 10, 5),
            },
            {
                "created_at": datetime(2026, 4, 17, 18, 0),
                "destination_city": "Arica",
                "estimated_delivery_date": None,
                "id": 1,
                "origin_city": "Iquique",
                "status": "pendiente",
                "tracking_number": "TRK-001",
                "updated_at": datetime(2026, 4, 17, 18, 15),
            },
        ]
    )

    patch_database(monkeypatch, cursors=[cursor])

    repository = MySQLShipmentRepository()
    shipments = repository.list_shipments()

    assert tuple(shipment.id for shipment in shipments) == (2, 1)
    assert shipments[0].estimated_delivery_date == date(2026, 4, 23)
    assert shipments[1].estimated_delivery_date is None
    assert "ORDER BY created_at DESC, id DESC" in cursor.execute_calls[0][0]


def test_summarize_shipments_returns_grouped_counts(monkeypatch: pytest.MonkeyPatch) -> None:
    cursor = FakeCursor(
        fetchall_result=[
            {
                "shipment_count": 1,
                "status": "en_transito",
            },
            {
                "shipment_count": 3,
                "status": "pendiente",
            },
        ]
    )

    patch_database(monkeypatch, cursors=[cursor])

    repository = MySQLShipmentRepository()
    summary = repository.summarize_shipments()

    assert summary == (
        ShipmentSummary(shipment_count=1, status="en_transito"),
        ShipmentSummary(shipment_count=3, status="pendiente"),
    )
    assert cursor.execute_calls == [
        (
            "SELECT COUNT(*) AS shipment_count, status FROM shipments "
            "GROUP BY status ORDER BY status ASC",
            None,
        )
    ]


def test_create_shipment_maps_duplicate_tracking_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    duplicate_error = IntegrityError(
        msg="Duplicate entry 'TRK-001' for key 'idx_shipments_tracking_number'",
        errno=errorcode.ER_DUP_ENTRY,
    )
    insert_cursor = FakeCursor(execute_error=duplicate_error)
    patch_database(monkeypatch, cursors=[insert_cursor])

    repository = MySQLShipmentRepository()
    payload = ShipmentMutation(
        destination_city="Valparaiso",
        estimated_delivery_date=None,
        origin_city="Santiago",
        status="pendiente",
        tracking_number="TRK-001",
    )

    with pytest.raises(DuplicateTrackingNumberError):
        repository.create_shipment(payload)


def test_update_shipment_updates_and_fetches_row(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = ShipmentMutation(
        destination_city="Puerto Montt",
        estimated_delivery_date=date(2026, 5, 3),
        origin_city="Osorno",
        status="en_transito",
        tracking_number="TRK-999",
    )
    updated_at = datetime(2026, 4, 18, 12, 45)
    update_cursor = FakeCursor()
    select_cursor = FakeCursor(
        fetchone_result={
            "created_at": datetime(2026, 4, 18, 9, 30),
            "destination_city": "Puerto Montt",
            "estimated_delivery_date": date(2026, 5, 3),
            "id": 7,
            "origin_city": "Osorno",
            "status": "en_transito",
            "tracking_number": "TRK-999",
            "updated_at": updated_at,
        }
    )

    connection = patch_database(monkeypatch, cursors=[update_cursor, select_cursor])

    repository = MySQLShipmentRepository()
    shipment = repository.update_shipment(7, payload)

    assert shipment.id == 7
    assert shipment.destination_city == "Puerto Montt"
    assert shipment.estimated_delivery_date == date(2026, 5, 3)
    assert shipment.updated_at == updated_at
    assert connection.commit_calls == 1
    assert update_cursor.execute_calls == [
        (
            "UPDATE shipments SET destination_city = %s, estimated_delivery_date = %s, "
            "origin_city = %s, status = %s, tracking_number = %s WHERE id = %s",
            ("Puerto Montt", date(2026, 5, 3), "Osorno", "en_transito", "TRK-999", 7),
        )
    ]
    assert select_cursor.execute_calls == [
        (
            "SELECT created_at, destination_city, estimated_delivery_date, id, origin_city, "
            "status, tracking_number, updated_at "
            "FROM shipments WHERE id = %s",
            (7,),
        )
    ]


def test_update_shipment_maps_duplicate_tracking_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    duplicate_error = IntegrityError(
        msg="Duplicate entry 'TRK-001' for key 'idx_shipments_tracking_number'",
        errno=errorcode.ER_DUP_ENTRY,
    )
    update_cursor = FakeCursor(execute_error=duplicate_error)
    patch_database(monkeypatch, cursors=[update_cursor])

    repository = MySQLShipmentRepository()
    payload = ShipmentMutation(
        destination_city="Valparaiso",
        estimated_delivery_date=None,
        origin_city="Santiago",
        status="pendiente",
        tracking_number="TRK-001",
    )

    with pytest.raises(DuplicateTrackingNumberError):
        repository.update_shipment(4, payload)


def test_update_shipment_raises_not_found_when_row_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = ShipmentMutation(
        destination_city="Valparaiso",
        estimated_delivery_date=None,
        origin_city="Santiago",
        status="pendiente",
        tracking_number="TRK-404",
    )
    update_cursor = FakeCursor()
    select_cursor = FakeCursor(fetchone_result=None)

    patch_database(monkeypatch, cursors=[update_cursor, select_cursor])

    repository = MySQLShipmentRepository()

    with pytest.raises(ShipmentNotFoundError):
        repository.update_shipment(404, payload)


def test_list_shipments_propagates_missing_database_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    @contextmanager
    def fake_get_connection() -> FakeConnection:
        raise DatabaseConfigurationError("missing settings")
        yield FakeConnection()

    monkeypatch.setattr(shipment_module, "get_connection", fake_get_connection)

    repository = MySQLShipmentRepository()

    with pytest.raises(DatabaseConfigurationError):
        repository.list_shipments()


def test_list_shipments_reraises_mysql_connector_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    connector_error = OperationalError(msg="MySQL is unavailable", errno=2003)

    @contextmanager
    def fake_get_connection() -> FakeConnection:
        yield FakeConnection()

    @contextmanager
    def fake_get_cursor(_connection: FakeConnection, **_kwargs: object) -> FakeCursor:
        raise connector_error
        yield FakeCursor()

    monkeypatch.setattr(shipment_module, "get_connection", fake_get_connection)
    monkeypatch.setattr(shipment_module, "get_cursor", fake_get_cursor)

    repository = MySQLShipmentRepository()

    with pytest.raises(OperationalError):
        repository.list_shipments()