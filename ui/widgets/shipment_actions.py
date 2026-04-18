from __future__ import annotations

from collections.abc import Callable
import tkinter as tk
from tkinter import ttk


class ShipmentActions(ttk.Frame):
    def __init__(
        self,
        parent: ttk.Frame,
        *,
        on_clear: Callable[[], None],
        on_create: Callable[[], None],
        on_delete: Callable[[], None],
        on_generate_report: Callable[[], None],
        on_update: Callable[[], None],
        on_reload: Callable[[], None],
    ) -> None:
        super().__init__(parent)
        self.on_clear = on_clear
        self.on_create = on_create
        self.on_delete = on_delete
        self.on_generate_report = on_generate_report
        self.on_reload = on_reload
        self.on_update = on_update

        self.columnconfigure(6, weight=1)
        self._create_widgets()

    def _create_widgets(self) -> None:
        ttk.Button(self, command=self.on_create, text="Crear envio").grid(
            column=0,
            row=0,
            padx=(0, 8),
            sticky=tk.EW,
        )
        self.update_button = ttk.Button(
            self,
            command=self.on_update,
            state=tk.DISABLED,
            text="Actualizar envio",
        )
        self.update_button.grid(
            column=1,
            row=0,
            padx=(0, 8),
            sticky=tk.EW,
        )
        self.delete_button = ttk.Button(
            self,
            command=self.on_delete,
            state=tk.DISABLED,
            text="Eliminar envio",
        )
        self.delete_button.grid(
            column=2,
            row=0,
            padx=(0, 8),
            sticky=tk.EW,
        )
        ttk.Button(self, command=self.on_clear, text="Limpiar formulario").grid(
            column=3,
            row=0,
            padx=(0, 8),
            sticky=tk.EW,
        )
        ttk.Button(self, command=self.on_reload, text="Recargar lista").grid(
            column=4,
            row=0,
            padx=(0, 8),
            sticky=tk.EW,
        )
        ttk.Button(self, command=self.on_generate_report, text="Generar reporte").grid(
            column=5,
            row=0,
            sticky=tk.EW,
        )

    def set_delete_enabled(self, enabled: bool) -> None:
        state = tk.NORMAL if enabled else tk.DISABLED
        self.delete_button.configure(state=state)

    def set_update_enabled(self, enabled: bool) -> None:
        state = tk.NORMAL if enabled else tk.DISABLED
        self.update_button.configure(state=state)