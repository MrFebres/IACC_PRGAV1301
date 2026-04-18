from __future__ import annotations

from datetime import date, datetime

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


class FakeShipmentActions:
    def __init__(self) -> None:
        self.update_enabled: bool = False

    def set_update_enabled(self, enabled: bool) -> None:
        self.update_enabled = enabled


class FakeShipmentTable:
    def __init__(self) -> None:
        self.rows: tuple[tuple[int, tuple[str, ...]], ...] = ()
        self.selected_shipment_id: int | None = None
        self.selection_cleared: bool = False

    def clear_selection(self) -> None:
        self.selection_cleared = True
        self.selected_shipment_id = None

    def get_selected_shipment_id(self) -> int | None:
        return self.selected_shipment_id

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
        summarize_error: Exception | None = None,
        summarize_result: tuple[ShipmentSummary, ...] = (),
        update_error: Exception | None = None,
        update_result: ShipmentRecord | None = None,
    ) -> None:
        self.create_calls: list[ShipmentMutation] = []
        self.create_error = create_error
        self.create_result = create_result
        self.list_calls: int = 0
        self.list_error = list_error
        self.list_result = list_result
        self.summarize_calls: int = 0
        self.summarize_error = summarize_error
        self.summarize_result = summarize_result
        self.update_calls: list[tuple[int, ShipmentMutation]] = []
        self.update_error = update_error
        self.update_result = update_result

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
        self.summarize_calls += 1
        if self.summarize_error is not None:
            raise self.summarize_error
        return self.summarize_result

    def update_shipment(self, shipment_id: int, payload: ShipmentMutation) -> ShipmentRecord:
        self.update_calls.append((shipment_id, payload))
        if self.update_error is not None:
            raise self.update_error
        if self.update_result is None:
            raise AssertionError("update_result must be provided for successful updates")
        return self.update_result


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
        estimated_delivery_date=date(2026, 5, 1),
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
    view.estimated_delivery_date_var = FakeVar()
    view.origin_city_var = FakeVar()
    view.status_feedback_var = FakeVar(
        "Completa el formulario y usa Recargar lista para consultar MySQL."
    )
    view.status_var = FakeVar(ShipmentManagementView.STATUS_CHOICES[0][1])
    view.tracking_number_var = FakeVar()
    view._selected_shipment_id = None
    view._shipments_by_id = {}
    view.shipment_actions = FakeShipmentActions()
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
    assert view.shipment_table.rows[0][1][2] == "2026-05-01"
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
            estimated_delivery_date=None,
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


def test_table_selection_loads_form_and_enables_update(
    suppress_messageboxes: list[tuple[str, str]],
) -> None:
    selected_record = build_record(shipment_id=7, tracking_number="TRK-777")
    repository = FakeShipmentRepository(list_result=(selected_record,))
    view = build_view(repository)

    view._reload_shipments(show_dialog_on_error=False)
    view.shipment_table.selected_shipment_id = 7

    view._on_table_select()

    assert view._selected_shipment_id == 7
    assert view.destination_city_var.get() == "Valparaiso"
    assert view.estimated_delivery_date_var.get() == "2026-05-01"
    assert view.origin_city_var.get() == "Santiago"
    assert view.shipment_form.status_value == "Pendiente"
    assert view.tracking_number_var.get() == "TRK-777"
    assert view.shipment_actions.update_enabled is True
    assert suppress_messageboxes == []


def test_on_create_blocks_invalid_estimated_delivery_date(
    suppress_messageboxes: list[tuple[str, str]],
) -> None:
    repository = FakeShipmentRepository()
    view = build_view(repository)

    view.destination_city_var.set("Valparaiso")
    view.estimated_delivery_date_var.set("abc")
    view.origin_city_var.set("Santiago")
    view.tracking_number_var.set("TRK-010")

    view._on_create()

    assert repository.create_calls == []
    assert view.status_feedback_var.get() == (
        "Fecha de entrega prevista debe usar el formato YYYY-MM-DD."
    )
    assert suppress_messageboxes[-1] == (
        "warning",
        "Fecha de entrega prevista debe usar el formato YYYY-MM-DD.",
    )


def test_on_generate_report_shows_grouped_status_summary(
    suppress_messageboxes: list[tuple[str, str]],
) -> None:
    repository = FakeShipmentRepository(
        summarize_result=(
            ShipmentSummary(shipment_count=2, status="pendiente"),
            ShipmentSummary(shipment_count=1, status="estado_desconocido"),
        )
    )
    view = build_view(repository)

    view._on_generate_report()

    assert repository.summarize_calls == 1
    assert view.status_feedback_var.get() == "Se genero el reporte de estados de envios."
    assert suppress_messageboxes[-1] == (
        "info",
        "Resumen de envios por estado:\n- Pendiente: 2\n- Estado Desconocido: 1",
    )


def test_on_generate_report_warns_when_summary_is_empty(
    suppress_messageboxes: list[tuple[str, str]],
) -> None:
    repository = FakeShipmentRepository(summarize_result=())
    view = build_view(repository)

    view._on_generate_report()

    assert repository.summarize_calls == 1
    assert view.status_feedback_var.get() == (
        "No hay datos para generar el reporte de estados. Crea envios o recarga la lista."
    )
    assert suppress_messageboxes[-1] == (
        "warning",
        "No hay envios registrados para resumir por estado.",
    )


def test_on_generate_report_surfaces_database_failures(
    suppress_messageboxes: list[tuple[str, str]],
) -> None:
    repository = FakeShipmentRepository(
        summarize_error=OperationalError(msg="MySQL unavailable", errno=2003),
    )
    view = build_view(repository)

    view._on_generate_report()

    assert repository.summarize_calls == 1
    assert view.status_feedback_var.get() == (
        "No fue posible completar la operacion en MySQL. Verifica la conexion y vuelve a intentar."
    )
    assert suppress_messageboxes[-1] == (
        "error",
        "No fue posible conectar con MySQL o completar la operacion solicitada.",
    )


def test_on_generate_report_surfaces_missing_configuration_guidance(
    suppress_messageboxes: list[tuple[str, str]],
) -> None:
    repository = FakeShipmentRepository(
        summarize_error=DatabaseConfigurationError("missing settings"),
    )
    view = build_view(repository)

    view._on_generate_report()

    assert repository.summarize_calls == 1
    assert view.status_feedback_var.get() == (
        "Falta configuracion de MySQL. Revisa MYSQL_DATABASE y MYSQL_USER en .env."
    )
    assert suppress_messageboxes[-1] == (
        "error",
        "Configura MYSQL_DATABASE y MYSQL_USER en tu archivo .env antes de usar la gestion de envios.",
    )


def test_on_update_requires_selection_before_saving(
    suppress_messageboxes: list[tuple[str, str]],
) -> None:
    repository = FakeShipmentRepository()
    view = build_view(repository)

    view._on_update()

    assert repository.update_calls == []
    assert view.status_feedback_var.get() == (
        "Selecciona un envio de la lista antes de actualizar."
    )
    assert suppress_messageboxes[-1] == (
        "warning",
        "Selecciona un envio de la lista antes de actualizar.",
    )


def test_on_update_persists_refreshes_table_and_resets_form(
    suppress_messageboxes: list[tuple[str, str]],
) -> None:
    existing_record = build_record(shipment_id=5, tracking_number="TRK-005")
    updated_record = ShipmentRecord(
        created_at=existing_record.created_at,
        destination_city="Puerto Montt",
        estimated_delivery_date=date(2026, 5, 3),
        id=5,
        origin_city="Osorno",
        status="en_transito",
        tracking_number="TRK-999",
        updated_at=existing_record.updated_at,
    )
    repository = FakeShipmentRepository(
        list_result=(updated_record,),
        update_result=updated_record,
    )
    view = build_view(repository)

    view._reload_shipments(show_dialog_on_error=False)
    view.shipment_table.selected_shipment_id = 5
    view._shipments_by_id = {5: existing_record}
    view._on_table_select()
    view.destination_city_var.set("Puerto Montt")
    view.estimated_delivery_date_var.set("2026-05-03")
    view.origin_city_var.set("Osorno")
    view.status_var.set("En transito")
    view.tracking_number_var.set("TRK-999")

    view._on_update()

    assert repository.update_calls == [
        (
            5,
            ShipmentMutation(
                destination_city="Puerto Montt",
                estimated_delivery_date=date(2026, 5, 3),
                origin_city="Osorno",
                status="en_transito",
                tracking_number="TRK-999",
            ),
        )
    ]
    assert repository.list_calls == 2
    assert view._selected_shipment_id is None
    assert view.destination_city_var.get() == ""
    assert view.estimated_delivery_date_var.get() == ""
    assert view.origin_city_var.get() == ""
    assert view.tracking_number_var.get() == ""
    assert view.shipment_form.status_value == "Pendiente"
    assert view.shipment_actions.update_enabled is False
    assert view.shipment_table.selection_cleared is True
    assert view.status_feedback_var.get() == "Se actualizo el envio TRK-999 correctamente."
    assert suppress_messageboxes[-1] == (
        "info",
        "El envio fue actualizado y la lista se recargo correctamente.",
    )


def test_on_update_shows_controlled_duplicate_error(
    suppress_messageboxes: list[tuple[str, str]],
) -> None:
    existing_record = build_record(shipment_id=3, tracking_number="TRK-003")
    repository = FakeShipmentRepository(
        list_result=(existing_record,),
        update_error=DuplicateTrackingNumberError("duplicate tracking number"),
    )
    view = build_view(repository)

    view._reload_shipments(show_dialog_on_error=False)
    view.shipment_table.selected_shipment_id = 3
    view._on_table_select()
    view.destination_city_var.set("Valparaiso")
    view.origin_city_var.set("Santiago")
    view.tracking_number_var.set("TRK-001")

    view._on_update()

    assert repository.update_calls == [
        (
            3,
            ShipmentMutation(
                destination_city="Valparaiso",
                estimated_delivery_date=date(2026, 5, 1),
                origin_city="Santiago",
                status="pendiente",
                tracking_number="TRK-001",
            ),
        )
    ]
    assert view.status_feedback_var.get() == (
        "El numero de seguimiento ya existe. Corrige el valor e intenta otra vez."
    )
    assert suppress_messageboxes[-1] == (
        "warning",
        "Ya existe un envio con ese numero de seguimiento.",
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