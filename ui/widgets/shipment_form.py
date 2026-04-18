from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class ShipmentForm(ttk.LabelFrame):
    def __init__(
        self,
        parent: ttk.Frame,
        *,
        destination_city_var: tk.StringVar,
        estimated_delivery_date_var: tk.StringVar,
        origin_city_var: tk.StringVar,
        status_feedback_var: tk.StringVar,
        status_options: tuple[str, ...],
        status_var: tk.StringVar,
        tracking_number_var: tk.StringVar,
    ) -> None:
        super().__init__(parent, padding=16, text="Datos del envio")
        self.destination_city_var = destination_city_var
        self.estimated_delivery_date_var = estimated_delivery_date_var
        self.origin_city_var = origin_city_var
        self.status_feedback_var = status_feedback_var
        self.status_options: tuple[str, ...] = status_options
        self.status_var = status_var
        self.tracking_number_var = tracking_number_var

        self.columnconfigure(1, weight=1)
        self.columnconfigure(3, weight=1)
        self._create_widgets()

    def _create_widgets(self) -> None:
        ttk.Label(self, text="Numero de seguimiento").grid(
            column=0,
            row=0,
            padx=(0, 10),
            pady=(0, 10),
            sticky=tk.W,
        )
        ttk.Entry(self, textvariable=self.tracking_number_var).grid(
            column=1,
            row=0,
            pady=(0, 10),
            sticky=tk.EW,
        )
        ttk.Label(self, text="Ciudad de origen").grid(
            column=2,
            row=0,
            padx=(16, 10),
            pady=(0, 10),
            sticky=tk.W,
        )
        ttk.Entry(self, textvariable=self.origin_city_var).grid(
            column=3,
            row=0,
            pady=(0, 10),
            sticky=tk.EW,
        )
        ttk.Label(self, text="Ciudad de destino").grid(
            column=0,
            row=1,
            padx=(0, 10),
            sticky=tk.W,
        )
        ttk.Entry(self, textvariable=self.destination_city_var).grid(
            column=1,
            row=1,
            sticky=tk.EW,
        )
        ttk.Label(self, text="Estado").grid(
            column=2,
            row=1,
            padx=(16, 10),
            sticky=tk.W,
        )
        self.status_combobox = ttk.Combobox(
            self,
            state="readonly",
            textvariable=self.status_var,
            values=self.status_options,
        )
        self.status_combobox.grid(column=3, row=1, sticky=tk.EW)
        ttk.Label(self, text="Fecha de entrega prevista").grid(
            column=0,
            row=2,
            padx=(0, 10),
            pady=(10, 0),
            sticky=tk.W,
        )
        ttk.Entry(self, textvariable=self.estimated_delivery_date_var).grid(
            column=1,
            row=2,
            pady=(10, 0),
            sticky=tk.EW,
        )
        ttk.Label(
            self,
            style="Body.TLabel",
            textvariable=self.status_feedback_var,
            wraplength=720,
        ).grid(column=0, columnspan=4, pady=(14, 0), row=3, sticky=tk.W)

    def configure_status_options(self, status_options: tuple[str, ...]) -> None:
        self.status_options = status_options
        self.status_combobox.configure(values=status_options)

    def set_status_value(
        self,
        status_label: str,
        *,
        extend_options: bool = False,
    ) -> None:
        if extend_options and status_label not in self.status_options:
            self.configure_status_options((*self.status_options, status_label))
        self.status_var.set(status_label)