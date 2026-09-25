# -*- coding: utf-8 -*-
"""Entry point: `Pose2Sim` script and `python -m GUI` both land here."""
import sys


def main():
    # Child mode for frozen exe: same binary acts as the pipeline runner,
    # so `sys.executable -m GUI.runner` keeps working after PyInstaller.
    if "--project" in sys.argv and "--steps" in sys.argv:
        from .runner import main as runner_main
        sys.exit(runner_main())
    from PySide6.QtWidgets import QApplication
    from .theme import APP_QSS
    from .main_window import run_app

    app = QApplication.instance() or QApplication(sys.argv)
    app.setOrganizationName("Pose2Sim")
    app.setApplicationName("Pose2Sim GUI")
    app.setStyleSheet(APP_QSS)
    # Vazirmatn if bundled later; fallback to system font
    try:
        from PySide6.QtGui import QFontDatabase
        from pathlib import Path
        fp = Path(__file__).resolve().parent / "assets" / "Vazirmatn-Regular.ttf"
        if fp.is_file():
            QFontDatabase.addApplicationFont(str(fp))
    except Exception:
        pass
    sys.exit(run_app())


if __name__ == "__main__":
    main()
