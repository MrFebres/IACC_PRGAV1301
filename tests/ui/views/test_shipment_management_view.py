from __future__ import annotations

from datetime import datetime

import pytest
from mysql.connector.errors import OperationalError

from database.connection import DatabaseConfigurationError
from repositories.shipment_repository import (
    DuplicateTrackingNumberError,
    ShipmentMutation,
    ShipmentRecord,
    ShipmentSummary,
)
from ui.views.shipment_management_view import ShipmentManagementView


class FakeVar:
    def __init__(self, value: str = "") -> None:
        self.value = value

    def get(self) -> str:
        return self.value

    def set(self, value: str) -> None:
        self.value = value


class FakeShipmentForm:
    def __init__(self) -> None:
        self.status_options: tuple[str, ...] = ()
        self.status_value: str = ""

    def configure_status_options(self, status_options: tuple[str, ...]) -> None:
        self.status_options = status_options

    def set_status_value(
        self,
        status_label: str,
        *,
        extend_options: bool = False,
    ) -> None:
        if extend_options and status_label not in self.status_options:
            self.status_options = (*self.status_options, status_label)
        self.status_value = status_label


class FakeShipmentTable:
    def __init__(self) -> None:
        self.rows: tuple[tuple[int, tuple[str, ...]], ...] = ()
        self.selection_cleared: bool = False

    def clear_selection(self) -> None:
        self.selection_cleared = True

    def load_rows(self, rows: tuple[tuple[int, tuple[str, ...]], ...]) -> None:
        self.rows = rows


class FakeShipmentRepository:
    def __init__(
        self,
        *,
        create_error: Exception | None = None,
        create_result: ShipmentRecord | None = None,
        list_error: Exception | None = None,
        list_result: tuple[ShipmentRecord, ...] = (),
    ) -> None:
        self.create_calls: list[ShipmentMutation] = []
        self.create_error = create_error
        self.create_result = create_result
        self.list_calls: int = 0
        self.list_error = list_error
        self.list_result = list_result

    def create_shipment(self, payload: ShipmentMutation) -> ShipmentRecord:
        self.create_calls.append(payload)
        if self.create_error is not None:
            raise self.create_error
        if self.create_result is None:
            raise AssertionError("create_result must be provided for successful creates")
        return self.create_result

    def list_shipments(self) -> tuple[ShipmentRecord, ...]:
        self.list_calls += 1
        if self.list_error is not None:
            raise self.list_error
        return self.list_result

    def summarize_shipments(self) -> tuple[ShipmentSummary, ...]:
        raise AssertionError("Summary is out of scope for this slice")

    def update_shipment(self, shipment_id: int, payload: ShipmentMutation) -> ShipmentRecord:
        raise AssertionError(f"Update is out of scope for this slice: {shipment_id} {payload}")


@pytest.fixture
def suppress_messageboxes(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
    calls: list[tuple[str, str]] = []

    def record(kind: str):
        def _inner(*, message: str, **_kwargs: object) -> None:
            calls.append((kind, message))

        return _inner

    monkeypatch.setattr(
        "ui.views.shipment_management_view.messagebox.showerror",
        record("error"),
    )
    monkeypatch.setattr(
        "ui.views.shipment_management_view.messagebox.showinfo",
        record("info"),
    )
    monkeypatch.setattr(
        "ui.views.shipment_management_view.messagebox.showwarning",
        record("warning"),
    )
    return calls


def build_record(*, shipment_id: int = 1, tracking_number: str = "TRK-001") -> ShipmentRecord:
    timestamp = datetime(2026, 4, 18, 11, 0)
    return ShipmentRecord(
        created_at=timestamp,
        destination_city="Valparaiso",
        id=shipment_id,
        origin_city="Santiago",
        status="pendiente",
        tracking_number=tracking_number,
        updated_at=timestamp,
    )


def build_view(repository: FakeShipmentRepository) -> ShipmentManagementView:
    view = ShipmentManagementView.__new__(ShipmentManagementView)
    view.repository = repository
    view.destination_city_var = FakeVar()
    view.origin_city_var = FakeVar()
    view.status_feedback_var = FakeVar(
        "Completa el formulario y usa Recargar lista para consultar MySQL."
    )
    view.status_var = FakeVar(ShipmentManagementView.STATUS_CHOICES[0][1])
    view.tracking_number_var = FakeVar()
    view.shipment_form = FakeShipmentForm()
    view.shipment_table = FakeShipmentTable()
    return view


def test_initial_load_populates_table_on_first_render(
    suppress_messageboxes: list[tuple[str, str]],
) -> None:
    repository = FakeShipmentRepository(list_result=(build_record(),))
    view = build_view(repository)

    view._load_initial_shipments()

    assert repository.list_calls == 1
    assert len(view.shipment_table.rows) == 1
    assert suppress_messageboxes == []


def test_on_create_blocks_blank_required_fields(
    suppress_messageboxes: list[tuple[str, str]],
) -> None:
    repository = FakeShipmentRepository()
    view = build_view(repository)

    view.origin_city_var.set("Santiago")
    view._on_create()

    assert repository.create_calls == []
    assert "Completa los campos obligatorios" in view.status_feedback_var.get()
    assert view.origin_city_var.get() == "Santiago"
    assert suppress_messageboxes[0][0] == "warning"


def test_on_create_blocks_values_that_exceed_schema_limits(
    suppress_messageboxes: list[tuple[str, str]],
) -> None:
    repository = FakeShipmentRepository()
    view = build_view(repository)

    view.destination_city_var.set("D" * 121)
    view.origin_city_var.set("Santiago")
    view.tracking_number_var.set("TRK-001")
    view._on_create()

    assert repository.create_calls == []
    assert view.status_feedback_var.get() == "Ciudad de destino no puede superar 120 caracteres."
    assert suppress_messageboxes[0] == (
        "warning",
        "Ciudad de destino no puede superar 120 caracteres.",
    )


def test_on_create_persists_and_refreshes_table(
    suppress_messageboxes: list[tuple[str, str]],
) -> None:
    created_record = build_record(tracking_number="TRK-777")
    repository = FakeShipmentRepository(
        create_result=created_record,
        list_result=(created_record,),
    )
    view = build_view(repository)

    view.destination_city_var.set("Valparaiso")
    view.origin_city_var.set("Santiago")
    view.tracking_number_var.set("TRK-777")
    view._on_create()

    assert repository.create_calls == [
        ShipmentMutation(
            destination_city="Valparaiso",
            origin_city="Santiago",
            status="pendiente",
            tracking_number="TRK-777",
        )
    ]
    assert repository.list_calls == 1
    assert view.status_feedback_var.get() == "Se registro el envio TRK-777 correctamente."
    assert view.tracking_number_var.get() == ""
    assert len(view.shipment_table.rows) == 1
    assert suppress_messageboxes[-1] == (
        "info",
        "El envio fue registrado y la lista se actualizo correctamente.",
    )


def test_on_create_shows_controlled_duplicate_error(
    suppress_messageboxes: list[tuple[str, str]],
) -> None:
    repository = FakeShipmentRepository(
        create_error=DuplicateTrackingNumberError("duplicate tracking number"),
    )
    view = build_view(repository)

    view.destination_city_var.set("Valparaiso")
    view.origin_city_var.set("Santiago")
    view.tracking_number_var.set("TRK-001")
    view._on_create()

    assert view.status_feedback_var.get() == (
        "El numero de seguimiento ya existe. Corrige el valor e intenta otra vez."
    )
    assert view.tracking_number_var.get() == "TRK-001"
    assert suppress_messageboxes[-1] == (
        "warning",
        "Ya existe un envio con ese numero de seguimiento.",
    )


def test_on_reload_surfaces_database_failures_without_crashing(
    suppress_messageboxes: list[tuple[str, str]],
) -> None:
    repository = FakeShipmentRepository(
        list_error=OperationalError(msg="MySQL unavailable", errno=2003),
    )
    view = build_view(repository)

    view._on_reload()

    assert repository.list_calls == 1
    assert view.status_feedback_var.get() == (
        "No fue posible completar la operacion en MySQL. Verifica la conexion y vuelve a intentar."
    )
    assert suppress_messageboxes[-1] == (
        "error",
        "No fue posible conectar con MySQL o completar la operacion solicitada.",
    )


def test_on_reload_surfaces_missing_configuration_guidance(
    suppress_messageboxes: list[tuple[str, str]],
) -> None:
    repository = FakeShipmentRepository(
        list_error=DatabaseConfigurationError("missing settings"),
    )
    view = build_view(repository)

    view._on_reload()

    assert view.status_feedback_var.get() == (
        "Falta configuracion de MySQL. Revisa MYSQL_DATABASE y MYSQL_USER en .env."
    )
    assert suppress_messageboxes[-1] == (
        "error",
        "Configura MYSQL_DATABASE y MYSQL_USER en tu archivo .env antes de usar la gestion de envios.",
    )