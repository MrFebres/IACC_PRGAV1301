from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ui.views import ShipmentManagementView


class MainFrame(ttk.Frame):
    def __init__(self, parent: tk.Tk) -> None:
        super().__init__(parent, padding=16)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        shipment_management_view = ShipmentManagementView(self)
        shipment_management_view.grid(column=0, row=0, sticky=tk.NSEW)