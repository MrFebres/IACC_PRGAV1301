from __future__ import annotations

from datetime import datetime
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
    ShipmentSummary,
)


logger = logging.getLogger(__name__)


class MainFrame(ttk.Frame):
    STATUS_CHOICES: tuple[tuple[str, str], ...] = (
        ("pendiente", "Pendiente"),
        ("en_transito", "En transito"),
        ("entregado", "Entregado"),
    )

    def __init__(self, parent: tk.Tk) -> None:
        super().__init__(parent, padding=16)
        self.repository: ShipmentRepository = MySQLShipmentRepository()
        self.selected_shipment_id: int | None = None
        self.shipments_by_id: dict[int, ShipmentRecord] = {}

        self.destination_city_var: tk.StringVar = tk.StringVar()
        self.mode_var: tk.StringVar = tk.StringVar(value="Modo actual: nuevo envio")
        self.origin_city_var: tk.StringVar = tk.StringVar()
        self.status_feedback_var: tk.StringVar = tk.StringVar(
            value="Completa el formulario y usa Recargar lista para consultar MySQL."
        )
        self.status_var: tk.StringVar = tk.StringVar(value=self.STATUS_CHOICES[0][1])
        self.tracking_number_var: tk.StringVar = tk.StringVar()

        self._create_widgets()
        self.after(0, self._load_initial_shipments)

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

        self._create_form_section(content_frame)
        self._create_action_section(content_frame)
        self._create_table_section(content_frame)

    def _create_action_section(self, parent: ttk.Frame) -> None:
        action_frame = ttk.Frame(parent)
        action_frame.grid(column=0, row=1, sticky=tk.EW, pady=(12, 12))
        action_frame.columnconfigure(5, weight=1)

        ttk.Button(action_frame, command=self._on_create, text="Crear envio").grid(
            column=0,
            row=0,
            padx=(0, 8),
            sticky=tk.EW,
        )
        self.update_button = ttk.Button(
            action_frame,
            command=self._on_update,
            state=tk.DISABLED,
            text="Actualizar envio",
        )
        self.update_button.grid(column=1, row=0, padx=(0, 8), sticky=tk.EW)
        ttk.Button(action_frame, command=self._on_clear, text="Limpiar seleccion").grid(
            column=2,
            row=0,
            padx=(0, 8),
            sticky=tk.EW,
        )
        ttk.Button(action_frame, command=self._on_reload, text="Recargar lista").grid(
            column=3,
            row=0,
            padx=(0, 8),
            sticky=tk.EW,
        )
        ttk.Button(action_frame, command=self._on_show_summary, text="Resumen por estado").grid(
            column=4,
            row=0,
            sticky=tk.EW,
        )
        ttk.Label(
            action_frame,
            style="Muted.TLabel",
            textvariable=self.mode_var,
        ).grid(column=5, row=0, padx=(16, 0), sticky=tk.E)

    def _create_form_section(self, parent: ttk.Frame) -> None:
        form_frame = ttk.LabelFrame(parent, padding=16, text="Datos del envio")
        form_frame.grid(column=0, row=0, sticky=tk.EW)
        form_frame.columnconfigure(1, weight=1)
        form_frame.columnconfigure(3, weight=1)

        ttk.Label(form_frame, text="Numero de seguimiento").grid(
            column=0,
            row=0,
            padx=(0, 10),
            pady=(0, 10),
            sticky=tk.W,
        )
        ttk.Entry(form_frame, textvariable=self.tracking_number_var).grid(
            column=1,
            row=0,
            pady=(0, 10),
            sticky=tk.EW,
        )
        ttk.Label(form_frame, text="Ciudad de origen").grid(
            column=2,
            row=0,
            padx=(16, 10),
            pady=(0, 10),
            sticky=tk.W,
        )
        ttk.Entry(form_frame, textvariable=self.origin_city_var).grid(
            column=3,
            row=0,
            pady=(0, 10),
            sticky=tk.EW,
        )
        ttk.Label(form_frame, text="Ciudad de destino").grid(
            column=0,
            row=1,
            padx=(0, 10),
            sticky=tk.W,
        )
        ttk.Entry(form_frame, textvariable=self.destination_city_var).grid(
            column=1,
            row=1,
            sticky=tk.EW,
        )
        ttk.Label(form_frame, text="Estado").grid(
            column=2,
            row=1,
            padx=(16, 10),
            sticky=tk.W,
        )
        self.status_combobox = ttk.Combobox(
            form_frame,
            state="readonly",
            textvariable=self.status_var,
            values=self._status_labels(),
        )
        self.status_combobox.grid(column=3, row=1, sticky=tk.EW)
        ttk.Label(
            form_frame,
            style="Body.TLabel",
            textvariable=self.status_feedback_var,
            wraplength=720,
        ).grid(column=0, columnspan=4, pady=(14, 0), row=2, sticky=tk.W)

    def _create_table_section(self, parent: ttk.Frame) -> None:
        table_frame = ttk.LabelFrame(parent, padding=12, text="Envios registrados")
        table_frame.grid(column=0, row=2, sticky=tk.NSEW)
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        columns: tuple[str, ...] = (
            "created_at",
            "destination_city",
            "origin_city",
            "status",
            "tracking_number",
            "updated_at",
        )
        self.shipments_tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
        )
        self.shipments_tree.heading("created_at", text="Creado")
        self.shipments_tree.heading("destination_city", text="Destino")
        self.shipments_tree.heading("origin_city", text="Origen")
        self.shipments_tree.heading("status", text="Estado")
        self.shipments_tree.heading("tracking_number", text="Seguimiento")
        self.shipments_tree.heading("updated_at", text="Actualizado")
        self.shipments_tree.column("created_at", minwidth=120, width=130)
        self.shipments_tree.column("destination_city", minwidth=120, width=150)
        self.shipments_tree.column("origin_city", minwidth=120, width=150)
        self.shipments_tree.column("status", minwidth=110, width=120)
        self.shipments_tree.column("tracking_number", minwidth=140, width=170)
        self.shipments_tree.column("updated_at", minwidth=120, width=130)
        self.shipments_tree.bind("<<TreeviewSelect>>", self._on_tree_selection)
        self.shipments_tree.grid(column=0, row=0, sticky=tk.NSEW)

        scrollbar = ttk.Scrollbar(
            table_frame,
            command=self.shipments_tree.yview,
            orient=tk.VERTICAL,
        )
        scrollbar.grid(column=1, row=0, sticky=tk.NS)
        self.shipments_tree.configure(yscrollcommand=scrollbar.set)

    def _build_payload(self) -> ShipmentMutation | None:
        destination_city: str = self.destination_city_var.get().strip()
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
            messagebox.showwarning(
                message="Completa los campos obligatorios:\n- " + "\n- ".join(missing_fields),
                parent=self,
                title="Validacion de envios",
            )
            return None

        return ShipmentMutation(
            destination_city=destination_city,
            origin_city=origin_city,
            status=self._status_value_from_label(status_label),
            tracking_number=tracking_number,
        )

    def _clear_tree_selection(self) -> None:
        selection = self.shipments_tree.selection()
        if selection:
            self.shipments_tree.selection_remove(selection)

    def _handle_action_error(self, exc: Exception, *, action_label: str, show_dialog: bool) -> None:
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
            self.status_feedback_var.set("El numero de seguimiento ya existe. Corrige el valor e intenta otra vez.")
            if show_dialog:
                messagebox.showwarning(
                    message="Ya existe un envio con ese numero de seguimiento.",
                    parent=self,
                    title="Seguimiento duplicado",
                )
            return

        if isinstance(exc, ShipmentNotFoundError):
            self.status_feedback_var.set("El envio seleccionado ya no existe en la base de datos.")
            if show_dialog:
                messagebox.showwarning(
                    message="El envio seleccionado ya no existe. Recarga la lista para sincronizar la vista.",
                    parent=self,
                    title="Envio no encontrado",
                )
            self._reset_form()
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
        self.status_feedback_var.set("Ocurrio un error inesperado. Revisa los logs para mas detalles.")
        if show_dialog:
            messagebox.showerror(
                message="Ocurrio un error inesperado durante la gestion de envios.",
                parent=self,
                title="Error inesperado",
            )

    def _format_datetime(self, value: datetime | None) -> str:
        if value is None:
            return "-"
        return value.strftime("%Y-%m-%d %H:%M")

    def _hydrate_form(self, shipment: ShipmentRecord) -> None:
        self.destination_city_var.set(shipment.destination_city)
        self.origin_city_var.set(shipment.origin_city)
        self.tracking_number_var.set(shipment.tracking_number)
        self._set_status_value(shipment.status)

    def _load_initial_shipments(self) -> None:
        self._reload_shipments(show_dialog_on_error=False)

    def _on_clear(self) -> None:
        self._reset_form()
        self.status_feedback_var.set("La seleccion se limpio. Puedes crear un nuevo envio.")

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
            self._handle_action_error(exc, action_label="shipment creation", show_dialog=True)

    def _on_reload(self) -> None:
        self._reload_shipments(show_dialog_on_error=True)

    def _on_show_summary(self) -> None:
        try:
            summary = self.repository.summarize_shipments()
        except Exception as exc:
            self._handle_action_error(exc, action_label="shipment summary", show_dialog=True)
            return

        if not summary:
            self.status_feedback_var.set("No hay envios registrados para resumir.")
            messagebox.showinfo(
                message="No hay envios registrados para mostrar en el resumen.",
                parent=self,
                title="Resumen de estados",
            )
            return

        report_lines = tuple(
            f"{self._status_label_from_value(item.status)}: {item.shipment_count}"
            for item in summary
        )
        self.status_feedback_var.set("Se genero el resumen agrupado por estado.")
        messagebox.showinfo(
            message="\n".join(report_lines),
            parent=self,
            title="Resumen de estados",
        )

    def _on_tree_selection(self, _event: tk.Event[tk.Misc]) -> None:
        selection = self.shipments_tree.selection()
        if not selection:
            self.selected_shipment_id = None
            self.update_button.configure(state=tk.DISABLED)
            self.mode_var.set("Modo actual: nuevo envio")
            return

        shipment_id = int(selection[0])
        shipment = self.shipments_by_id.get(shipment_id)
        if shipment is None:
            self._reset_form()
            return

        self.selected_shipment_id = shipment_id
        self._hydrate_form(shipment)
        self.mode_var.set(f"Modo actual: editando envio #{shipment_id}")
        self.status_feedback_var.set(
            "El formulario se cargo con el envio seleccionado. Actualiza los campos y guarda cambios."
        )
        self.update_button.configure(state=tk.NORMAL)

    def _on_update(self) -> None:
        if self.selected_shipment_id is None:
            messagebox.showwarning(
                message="Selecciona un envio de la tabla antes de intentar actualizarlo.",
                parent=self,
                title="Seleccion requerida",
            )
            return

        payload = self._build_payload()
        if payload is None:
            return

        try:
            shipment = self.repository.update_shipment(self.selected_shipment_id, payload)
            if self._reload_shipments(show_dialog_on_error=True):
                self._reset_form()
                self.status_feedback_var.set(
                    f"Se actualizaron los datos del envio {shipment.tracking_number}."
                )
                messagebox.showinfo(
                    message="El envio seleccionado fue actualizado correctamente.",
                    parent=self,
                    title="Envio actualizado",
                )
                return

            self.status_feedback_var.set(
                "El envio se actualizo, pero no fue posible recargar la lista automaticamente."
            )
            messagebox.showwarning(
                message="Los datos fueron actualizados, pero la lista no pudo recargarse. Intenta usar Recargar lista.",
                parent=self,
                title="Recarga pendiente",
            )
        except Exception as exc:
            self._handle_action_error(exc, action_label="shipment update", show_dialog=True)

    def _populate_tree(self, shipments: tuple[ShipmentRecord, ...]) -> None:
        children = self.shipments_tree.get_children()
        if children:
            self.shipments_tree.delete(*children)

        for shipment in shipments:
            self.shipments_tree.insert(
                "",
                tk.END,
                iid=str(shipment.id),
                values=(
                    self._format_datetime(shipment.created_at),
                    shipment.destination_city,
                    shipment.origin_city,
                    self._status_label_from_value(shipment.status),
                    shipment.tracking_number,
                    self._format_datetime(shipment.updated_at),
                ),
            )

    def _reload_shipments(self, *, show_dialog_on_error: bool) -> bool:
        try:
            shipments = self.repository.list_shipments()
        except Exception as exc:
            self._handle_action_error(exc, action_label="shipment reload", show_dialog=show_dialog_on_error)
            return False

        self.shipments_by_id = {shipment.id: shipment for shipment in shipments}
        self._populate_tree(shipments)
        self._reset_form()
        if shipments:
            self.status_feedback_var.set(
                f"Se cargaron {len(shipments)} envios desde MySQL."
            )
            return True
        self.status_feedback_var.set("No hay envios registrados todavia. Puedes crear el primero desde el formulario.")
        return True

    def _reset_form(self) -> None:
        self.destination_city_var.set("")
        self.origin_city_var.set("")
        self.selected_shipment_id = None
        self.status_combobox.configure(values=self._status_labels())
        self.status_var.set(self.STATUS_CHOICES[0][1])
        self.tracking_number_var.set("")
        self.update_button.configure(state=tk.DISABLED)
        self.mode_var.set("Modo actual: nuevo envio")
        self._clear_tree_selection()

    def _set_status_value(self, status: str) -> None:
        status_label = self._status_label_from_value(status)
        values = self._status_labels()
        if status_label not in values:
            self.status_combobox.configure(values=(*values, status_label))
        self.status_var.set(status_label)

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