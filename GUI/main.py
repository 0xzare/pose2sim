# -*- coding: utf-8 -*-
"""Entry point for the Pose2Sim GUI.

Works in every launch mode:
- `python -m GUI.main` or `python -m GUI` (dev, from repo root)
- `python GUI/main.py` (dev, direct script — no package context)
- frozen exe (PyInstaller onedir): `Pose2Sim` / `Pose2Sim.exe`
"""
import sys
from pathlib import Path


def _bootstrap():
    # Direct script run (`python GUI/main.py`) or frozen exe: there is no
    # parent package, so make absolute `GUI.*` imports resolvable.
    # (`python -m ...` already sets this up; the frozen importer handles
    # the exe case — the extra path entry below is harmless there.)
    if __package__ is None:
        root = str(Path(__file__).resolve().parent.parent)
        if root not in sys.path:
            sys.path.insert(0, root)


_bootstrap()

from GUI.theme import APP_QSS  # noqa: E402


def main():
    # Child mode for frozen exe: the same binary acts as the pipeline
    # runner, so `sys.executable --project ... --steps ...` keeps working
    # after PyInstaller (see GUI/worker.py).
    if "--project" in sys.argv and "--steps" in sys.argv:
        from GUI.runner import main as runner_main
        sys.exit(runner_main())
    from PySide6.QtWidgets import QApplication
    from GUI.main_window import run_app

    app = QApplication.instance() or QApplication(sys.argv)
    app.setOrganizationName("Pose2Sim")
    app.setApplicationName("Pose2Sim GUI")
    app.setStyleSheet(APP_QSS)
    # Vazirmatn if bundled later; fallback to system font
    try:
        from PySide6.QtGui import QFontDatabase
        fp = Path(__file__).resolve().parent / "assets" / "Vazirmatn-Regular.ttf"
        if fp.is_file():
            QFontDatabase.addApplicationFont(str(fp))
    except Exception:
        pass
    sys.exit(run_app())


if __name__ == "__main__":
    main()
