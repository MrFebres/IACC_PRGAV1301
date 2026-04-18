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
        on_reload: Callable[[], None],
    ) -> None:
        super().__init__(parent)
        self.on_clear = on_clear
        self.on_create = on_create
        self.on_reload = on_reload

        self.columnconfigure(3, weight=1)
        self._create_widgets()

    def _create_widgets(self) -> None:
        ttk.Button(self, command=self.on_create, text="Crear envio").grid(
            column=0,
            row=0,
            padx=(0, 8),
            sticky=tk.EW,
        )
        ttk.Button(self, command=self.on_clear, text="Limpiar formulario").grid(
            column=1,
            row=0,
            padx=(0, 8),
            sticky=tk.EW,
        )
        ttk.Button(self, command=self.on_reload, text="Recargar lista").grid(
            column=2,
            row=0,
            sticky=tk.EW,
        )