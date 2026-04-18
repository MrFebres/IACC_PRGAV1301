from __future__ import annotations

from collections.abc import Callable
import tkinter as tk
from tkinter import ttk


class ShipmentActions(ttk.Frame):
    def __init__(
        self,
        parent: ttk.Frame,
        *,
        mode_var: tk.StringVar,
        on_clear: Callable[[], None],
        on_create: Callable[[], None],
        on_reload: Callable[[], None],
        on_show_summary: Callable[[], None],
        on_update: Callable[[], None],
    ) -> None:
        super().__init__(parent)
        self.mode_var = mode_var
        self.on_clear = on_clear
        self.on_create = on_create
        self.on_reload = on_reload
        self.on_show_summary = on_show_summary
        self.on_update = on_update

        self.columnconfigure(5, weight=1)
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
        self.update_button.grid(column=1, row=0, padx=(0, 8), sticky=tk.EW)
        ttk.Button(self, command=self.on_clear, text="Limpiar seleccion").grid(
            column=2,
            row=0,
            padx=(0, 8),
            sticky=tk.EW,
        )
        ttk.Button(self, command=self.on_reload, text="Recargar lista").grid(
            column=3,
            row=0,
            padx=(0, 8),
            sticky=tk.EW,
        )
        ttk.Button(
            self,
            command=self.on_show_summary,
            text="Resumen por estado",
        ).grid(column=4, row=0, sticky=tk.EW)
        ttk.Label(
            self,
            style="Muted.TLabel",
            textvariable=self.mode_var,
        ).grid(column=5, row=0, padx=(16, 0), sticky=tk.E)

    def set_update_enabled(self, is_enabled: bool) -> None:
        state = tk.NORMAL if is_enabled else tk.DISABLED
        self.update_button.configure(state=state)