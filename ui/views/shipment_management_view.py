from __future__ import annotations

from datetime import date, datetime
import logging
import tkinter as tk
from tkinter import messagebox, ttk

from mysql.connector import Error

from database.connection import DatabaseConfigurationError
from repositories import (
    DuplicateTrackingNumberError,
    MySQLShipmentRepository,
    ShipmentMutation,
    ShipmentNotFoundError,
    ShipmentRecord,
    ShipmentRepository,
    ShipmentSchemaCompatibilityError,
    ShipmentSummary,
)
from ui.widgets import ShipmentActions, ShipmentForm, ShipmentTable


logger = logging.getLogger(__name__)


class ShipmentManagementView(ttk.Frame):
    MAX_CITY_LENGTH: int = 120
    MAX_STATUS_LENGTH: int = 20
    MAX_TRACKING_NUMBER_LENGTH: int = 32
    STATUS_CHOICES: tuple[tuple[str, str], ...] = (
        ("pendiente", "Pendiente"),
        ("en_transito", "En tránsito"),
        ("entregado", "Entregado"),
    )

    def __init__(
        self,
        parent: ttk.Frame,
        *,
        autoload: bool = True,
        repository: ShipmentRepository | None = None,
    ) -> None:
        super().__init__(parent)
        self._selected_shipment_id: int | None = None
        self._shipments_by_id: dict[int, ShipmentRecord] = {}
        self.repository: ShipmentRepository = repository or MySQLShipmentRepository()

        self.destination_city_var: tk.StringVar = tk.StringVar(master=self)
        self.estimated_delivery_date_var: tk.StringVar = tk.StringVar(master=self)
        self.origin_city_var: tk.StringVar = tk.StringVar(master=self)
        self.status_feedback_var: tk.StringVar = tk.StringVar(
            master=self,
            value="Completa el formulario y usa Recargar lista para consultar MySQL.",
        )
        self.status_var: tk.StringVar = tk.StringVar(
            master=self,
            value=self.STATUS_CHOICES[0][1],
        )
        self.tracking_number_var: tk.StringVar = tk.StringVar(master=self)

        self._create_widgets()
        if autoload:
            self.after(0, self._load_initial_shipments)

    def _build_payload(self) -> ShipmentMutation | None:
        destination_city: str = self.destination_city_var.get().strip()
        estimated_delivery_date_input: str = self.estimated_delivery_date_var.get().strip()
        origin_city: str = self.origin_city_var.get().strip()
        status_label: str = self.status_var.get().strip()
        tracking_number: str = self.tracking_number_var.get().strip()

        missing_fields: list[str] = []
        if not tracking_number:
            missing_fields.append("Numero de seguimiento")
        if not origin_city:
            missing_fields.append("Ciudad de origen")
        if not destination_city:
            missing_fields.append("Ciudad de destino")
        if not status_label:
            missing_fields.append("Estado")

        if missing_fields:
            self._show_validation_feedback(
                "Completa los campos obligatorios:\n- " + "\n- ".join(missing_fields)
            )
            return None

        if len(tracking_number) > self.MAX_TRACKING_NUMBER_LENGTH:
            self._show_validation_feedback(
                "Numero de seguimiento no puede superar 32 caracteres."
            )
            return None

        if len(origin_city) > self.MAX_CITY_LENGTH:
            self._show_validation_feedback(
                "Ciudad de origen no puede superar 120 caracteres."
            )
            return None

        if len(destination_city) > self.MAX_CITY_LENGTH:
            self._show_validation_feedback(
                "Ciudad de destino no puede superar 120 caracteres."
            )
            return None

        status_value: str = self._status_value_from_label(status_label)
        if len(status_value) > self.MAX_STATUS_LENGTH:
            self._show_validation_feedback("Estado no puede superar 20 caracteres.")
            return None

        estimated_delivery_date: date | None = None
        if estimated_delivery_date_input:
            try:
                estimated_delivery_date = date.fromisoformat(estimated_delivery_date_input)
            except ValueError:
                self._show_validation_feedback(
                    "Fecha de entrega prevista debe usar el formato YYYY-MM-DD."
                )
                return None

        return ShipmentMutation(
            destination_city=destination_city,
            estimated_delivery_date=estimated_delivery_date,
            origin_city=origin_city,
            status=status_value,
            tracking_number=tracking_number,
        )

    def _create_widgets(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        ttk.Label(self, style="Heading.TLabel", text="Gestion de envios").grid(
            column=0,
            row=0,
            sticky=tk.W,
        )

        content_frame = ttk.Frame(self)
        content_frame.grid(column=0, row=1, sticky=tk.NSEW, pady=(12, 0))
        content_frame.columnconfigure(0, weight=1)
        content_frame.rowconfigure(2, weight=1)

        self.shipment_form = ShipmentForm(
            content_frame,
            destination_city_var=self.destination_city_var,
            estimated_delivery_date_var=self.estimated_delivery_date_var,
            origin_city_var=self.origin_city_var,
            status_feedback_var=self.status_feedback_var,
            status_options=self._status_labels(),
            status_var=self.status_var,
            tracking_number_var=self.tracking_number_var,
        )
        self.shipment_form.grid(column=0, row=0, sticky=tk.EW)

        self.shipment_actions = ShipmentActions(
            content_frame,
            on_clear=self._on_clear,
            on_create=self._on_create,
            on_delete=self._on_delete,
            on_generate_report=self._on_generate_report,
            on_reload=self._on_reload,
            on_update=self._on_update,
        )
        self.shipment_actions.grid(column=0, row=1, sticky=tk.EW, pady=(12, 12))

        self.shipment_table = ShipmentTable(
            content_frame,
            on_select=self._on_table_select,
        )
        self.shipment_table.grid(column=0, row=2, sticky=tk.NSEW)

    def _enter_edit_mode(self, shipment: ShipmentRecord) -> None:
        self._selected_shipment_id = shipment.id
        self.shipment_actions.set_delete_enabled(True)
        self.shipment_actions.set_update_enabled(True)
        self.status_feedback_var.set(
            f"Editando el envio {shipment.tracking_number}. Actualiza los datos y guarda los cambios."
        )

    def _exit_edit_mode(self) -> None:
        self._selected_shipment_id = None
        self.shipment_actions.set_delete_enabled(False)
        self.shipment_actions.set_update_enabled(False)

    def _format_datetime(self, value: datetime | None) -> str:
        if value is None:
            return "-"
        return value.strftime("%Y-%m-%d %H:%M")

    def _format_date(self, value: date | None) -> str:
        if value is None:
            return "-"
        return value.isoformat()

    def _handle_action_error(
        self,
        exc: Exception,
        *,
        action_label: str,
        show_dialog: bool,
    ) -> None:
        if isinstance(exc, ShipmentSchemaCompatibilityError):
            self.status_feedback_var.set(exc.summary_message)
            if show_dialog:
                messagebox.showerror(
                    message=str(exc),
                    parent=self,
                    title="Compatibilidad de esquema",
                )
            return

        if isinstance(exc, DatabaseConfigurationError):
            self.status_feedback_var.set(
                "Falta configuracion de MySQL. Revisa MYSQL_DATABASE y MYSQL_USER en .env."
            )
            if show_dialog:
                messagebox.showerror(
                    message="Configura MYSQL_DATABASE y MYSQL_USER en tu archivo .env antes de usar la gestion de envios.",
                    parent=self,
                    title="Configuracion incompleta",
                )
            return

        if isinstance(exc, DuplicateTrackingNumberError):
            self.status_feedback_var.set(
                "El numero de seguimiento ya existe. Corrige el valor e intenta otra vez."
            )
            if show_dialog:
                messagebox.showwarning(
                    message="Ya existe un envio con ese numero de seguimiento.",
                    parent=self,
                    title="Seguimiento duplicado",
                )
            return

        if isinstance(exc, ShipmentNotFoundError):
            self.status_feedback_var.set(
                "El envio seleccionado ya no existe. Recarga la lista e intenta nuevamente."
            )
            if show_dialog:
                messagebox.showwarning(
                    message="El envio seleccionado ya no existe. Recarga la lista antes de continuar.",
                    parent=self,
                    title="Envio no disponible",
                )
            return

        if isinstance(exc, Error):
            self.status_feedback_var.set(
                "No fue posible completar la operacion en MySQL. Verifica la conexion y vuelve a intentar."
            )
            if show_dialog:
                messagebox.showerror(
                    message="No fue posible conectar con MySQL o completar la operacion solicitada.",
                    parent=self,
                    title="Error de base de datos",
                )
            return

        logger.exception("Unexpected UI error during %s", action_label, exc_info=exc)
        self.status_feedback_var.set(
            "Ocurrio un error inesperado. Revisa los logs para mas detalles."
        )
        if show_dialog:
            messagebox.showerror(
                message="Ocurrio un error inesperado durante la gestion de envios.",
                parent=self,
                title="Error inesperado",
            )

    def _load_initial_shipments(self) -> None:
        self._reload_shipments(show_dialog_on_error=False)

    def _on_clear(self) -> None:
        self._reset_form()
        self.status_feedback_var.set(
            "El formulario se limpio. Puedes crear un nuevo envio."
        )

    def _on_create(self) -> None:
        payload = self._build_payload()
        if payload is None:
            return

        try:
            shipment = self.repository.create_shipment(payload)
            if self._reload_shipments(show_dialog_on_error=True):
                self._reset_form()
                self.status_feedback_var.set(
                    f"Se registro el envio {shipment.tracking_number} correctamente."
                )
                messagebox.showinfo(
                    message="El envio fue registrado y la lista se actualizo correctamente.",
                    parent=self,
                    title="Envio creado",
                )
                return

            self.status_feedback_var.set(
                "El envio se guardo, pero no fue posible recargar la lista automaticamente."
            )
            messagebox.showwarning(
                message="El envio fue creado, pero la lista no pudo recargarse. Intenta usar Recargar lista.",
                parent=self,
                title="Recarga pendiente",
            )
        except Exception as exc:
            self._handle_action_error(
                exc,
                action_label="shipment creation",
                show_dialog=True,
            )

    def _on_delete(self) -> None:
        if self._selected_shipment_id is None:
            self._show_validation_feedback(
                "Selecciona un envio de la lista antes de eliminar."
            )
            return

        if not messagebox.askokcancel(
            message="Se eliminara el envio seleccionado de forma permanente. ¿Deseas continuar?",
            parent=self,
            title="Confirmar eliminacion",
        ):
            return

        try:
            self.repository.delete_shipment(self._selected_shipment_id)
            if self._reload_shipments(show_dialog_on_error=True):
                self._reset_form()
                self.status_feedback_var.set(
                    "Se elimino el envio seleccionado correctamente."
                )
                messagebox.showinfo(
                    message="El envio fue eliminado y la lista se recargo correctamente.",
                    parent=self,
                    title="Envio eliminado",
                )
                return

            self.status_feedback_var.set(
                "El envio se elimino, pero no fue posible recargar la lista automaticamente."
            )
            messagebox.showwarning(
                message="El envio fue eliminado, pero la lista no pudo recargarse. Intenta usar Recargar lista.",
                parent=self,
                title="Recarga pendiente",
            )
        except Exception as exc:
            self._handle_action_error(
                exc,
                action_label="shipment delete",
                show_dialog=True,
            )

    def _on_reload(self) -> None:
        self._reload_shipments(show_dialog_on_error=True)

    def _on_generate_report(self) -> None:
        try:
            summary = self.repository.summarize_shipments()
        except Exception as exc:
            self._handle_action_error(
                exc,
                action_label="shipment report generation",
                show_dialog=True,
            )
            return

        if not summary:
            self.status_feedback_var.set(
                "No hay datos para generar el reporte de estados. Crea envios o recarga la lista."
            )
            messagebox.showwarning(
                message="No hay envios registrados para resumir por estado.",
                parent=self,
                title="Reporte sin datos",
            )
            return

        report_message = self._format_shipment_report(summary)
        self.status_feedback_var.set("Se genero el reporte de estados de envios.")
        messagebox.showinfo(
            message=report_message,
            parent=self,
            title="Reporte de envios",
        )

    def _on_table_select(self, _event: tk.Event[tk.Misc] | None = None) -> None:
        selected_shipment_id = self.shipment_table.get_selected_shipment_id()
        if selected_shipment_id is None:
            self._exit_edit_mode()
            return

        shipment = self._shipments_by_id.get(selected_shipment_id)
        if shipment is None:
            self._exit_edit_mode()
            return

        self._load_shipment_into_form(shipment)
        self._enter_edit_mode(shipment)

    def _on_update(self) -> None:
        if self._selected_shipment_id is None:
            self._show_validation_feedback(
                "Selecciona un envio de la lista antes de actualizar."
            )
            return

        payload = self._build_payload()
        if payload is None:
            return

        try:
            shipment = self.repository.update_shipment(self._selected_shipment_id, payload)
            if self._reload_shipments(show_dialog_on_error=True):
                self._reset_form()
                self.status_feedback_var.set(
                    f"Se actualizo el envio {shipment.tracking_number} correctamente."
                )
                messagebox.showinfo(
                    message="El envio fue actualizado y la lista se recargo correctamente.",
                    parent=self,
                    title="Envio actualizado",
                )
                return

            self.status_feedback_var.set(
                "El envio se actualizo, pero no fue posible recargar la lista automaticamente."
            )
            messagebox.showwarning(
                message="El envio fue actualizado, pero la lista no pudo recargarse. Intenta usar Recargar lista.",
                parent=self,
                title="Recarga pendiente",
            )
        except Exception as exc:
            self._handle_action_error(
                exc,
                action_label="shipment update",
                show_dialog=True,
            )

    def _populate_table(self, shipments: tuple[ShipmentRecord, ...]) -> None:
        rows: tuple[tuple[int, tuple[str, ...]], ...] = tuple(
            (
                shipment.id,
                (
                    self._format_datetime(shipment.created_at),
                    shipment.destination_city,
                    self._format_date(shipment.estimated_delivery_date),
                    shipment.origin_city,
                    self._status_label_from_value(shipment.status),
                    shipment.tracking_number,
                    self._format_datetime(shipment.updated_at),
                ),
            )
            for shipment in shipments
        )
        self.shipment_table.load_rows(rows)

    def _load_shipment_into_form(self, shipment: ShipmentRecord) -> None:
        self.destination_city_var.set(shipment.destination_city)
        self.estimated_delivery_date_var.set(
            ""
            if shipment.estimated_delivery_date is None
            else shipment.estimated_delivery_date.isoformat()
        )
        self.origin_city_var.set(shipment.origin_city)
        self.shipment_form.configure_status_options(self._status_labels())
        self.shipment_form.set_status_value(
            self._status_label_from_value(shipment.status),
            extend_options=True,
        )
        self.tracking_number_var.set(shipment.tracking_number)

    def _reload_shipments(self, *, show_dialog_on_error: bool) -> bool:
        try:
            shipments = self.repository.list_shipments()
        except Exception as exc:
            self._handle_action_error(
                exc,
                action_label="shipment reload",
                show_dialog=show_dialog_on_error,
            )
            return False

        self._shipments_by_id = {shipment.id: shipment for shipment in shipments}
        self._populate_table(shipments)
        self._exit_edit_mode()
        self.shipment_table.clear_selection()
        if shipments:
            self.status_feedback_var.set(
                f"Se cargaron {len(shipments)} envios desde MySQL."
            )
            return True

        self.status_feedback_var.set(
            "No hay envios registrados todavia. Puedes crear el primero desde el formulario."
        )
        return True

    def _reset_form(self) -> None:
        self._exit_edit_mode()
        self.destination_city_var.set("")
        self.estimated_delivery_date_var.set("")
        self.origin_city_var.set("")
        self.shipment_form.configure_status_options(self._status_labels())
        self.shipment_form.set_status_value(self.STATUS_CHOICES[0][1])
        self.tracking_number_var.set("")
        self.shipment_table.clear_selection()

    def _show_validation_feedback(self, message: str) -> None:
        self.status_feedback_var.set(message)
        messagebox.showwarning(
            message=message,
            parent=self,
            title="Validacion de envios",
        )

    def _format_shipment_report(
        self,
        summary: tuple[ShipmentSummary, ...],
    ) -> str:
        lines: tuple[str, ...] = tuple(
            f"- {self._status_label_from_value(item.status)}: {item.shipment_count}"
            for item in summary
        )
        return "Resumen de envios por estado:\n" + "\n".join(lines)

    @classmethod
    def _status_label_from_value(cls, status: str) -> str:
        for value, label in cls.STATUS_CHOICES:
            if value == status:
                return label
        return status.replace("_", " ").strip().title()

    @classmethod
    def _status_labels(cls) -> tuple[str, ...]:
        return tuple(label for _, label in cls.STATUS_CHOICES)

    @classmethod
    def _status_value_from_label(cls, label: str) -> str:
        for value, display_label in cls.STATUS_CHOICES:
            if display_label == label:
                return value
        return label.strip().lower().replace(" ", "_")