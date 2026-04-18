from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from settings import get_settings
from ui.main_frame import MainFrame


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        settings = get_settings()
        self.title(settings.app.title)
        self.geometry(settings.app.window_geometry)
        self.minsize(width=640, height=400)

        self._configure_styles()
        self._create_widgets()

    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("Body.TLabel", foreground="#30475E")
        style.configure("Heading.TLabel", font=("Helvetica", 20, "bold"))
        style.configure("Muted.TLabel", foreground="#52616B")

    def _create_widgets(self) -> None:
        main_frame = MainFrame(self)
        main_frame.pack(expand=True, fill=tk.BOTH)