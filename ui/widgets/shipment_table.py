from __future__ import annotations

from collections.abc import Callable
import tkinter as tk
from tkinter import ttk


class ShipmentTable(ttk.LabelFrame):
    COLUMNS: tuple[str, ...] = (
        "created_at",
        "destination_city",
        "origin_city",
        "status",
        "tracking_number",
        "updated_at",
    )

    def __init__(
        self,
        parent: ttk.Frame,
        *,
        on_select: Callable[[tk.Event[tk.Misc]], None] | None = None,
    ) -> None:
        super().__init__(parent, padding=12, text="Envios registrados")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self._create_widgets(on_select)

    def _create_widgets(
        self,
        on_select: Callable[[tk.Event[tk.Misc]], None] | None,
    ) -> None:
        self.shipments_tree = ttk.Treeview(
            self,
            columns=self.COLUMNS,
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
        if on_select is not None:
            self.shipments_tree.bind("<<TreeviewSelect>>", on_select)
        self.shipments_tree.grid(column=0, row=0, sticky=tk.NSEW)

        scrollbar = ttk.Scrollbar(
            self,
            command=self.shipments_tree.yview,
            orient=tk.VERTICAL,
        )
        scrollbar.grid(column=1, row=0, sticky=tk.NS)
        self.shipments_tree.configure(yscrollcommand=scrollbar.set)

    def clear_selection(self) -> None:
        selection = self.shipments_tree.selection()
        if selection:
            self.shipments_tree.selection_remove(selection)

    def get_selected_shipment_id(self) -> int | None:
        selection = self.shipments_tree.selection()
        if not selection:
            return None

        try:
            return int(selection[0])
        except ValueError:
            return None

    def load_rows(self, rows: tuple[tuple[int, tuple[str, ...]], ...]) -> None:
        children = self.shipments_tree.get_children()
        if children:
            self.shipments_tree.delete(*children)

        for shipment_id, values in rows:
            self.shipments_tree.insert(
                "",
                tk.END,
                iid=str(shipment_id),
                values=values,
            )