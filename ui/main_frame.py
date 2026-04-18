from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class MainFrame(ttk.Frame):
    def __init__(self, parent: tk.Tk) -> None:
        super().__init__(parent, padding=24)
        self.heading_var: tk.StringVar = tk.StringVar(
            value="Base lista para construir la siguiente iteracion del proyecto."
        )
        self.status_var: tk.StringVar = tk.StringVar(
            value="Las operaciones de envios todavia no estan habilitadas en este scaffold."
        )
        self.summary_var: tk.StringVar = tk.StringVar(
            value="El arranque carga configuracion local, conserva el acceso a MySQL diferido y mantiene la UI en estado seguro."
        )
        self._create_widgets()

    def _create_widgets(self) -> None:
        ttk.Label(self, style="Heading.TLabel", text="Sistema de Logistica").pack(anchor=tk.W)
        ttk.Label(
            self,
            style="Body.TLabel",
            textvariable=self.heading_var,
            wraplength=640,
        ).pack(anchor=tk.W, pady=(12, 0))
        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=18)
        ttk.Label(
            self,
            style="Muted.TLabel",
            text="Estado del scaffold",
        ).pack(anchor=tk.W)
        ttk.Label(
            self,
            style="Body.TLabel",
            textvariable=self.status_var,
            wraplength=640,
        ).pack(anchor=tk.W, pady=(6, 0))
        ttk.Label(
            self,
            style="Body.TLabel",
            textvariable=self.summary_var,
            wraplength=640,
        ).pack(anchor=tk.W, pady=(14, 0))