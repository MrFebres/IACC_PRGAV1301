from __future__ import annotations

from pathlib import Path
import sys
import tkinter as tk

import pytest


PROJECT_ROOT: Path = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def tk_root() -> tk.Tk:
    root = tk.Tk()
    root.withdraw()
    yield root
    if root.winfo_exists():
        root.update_idletasks()
        root.destroy()