"""Qt application bootstrap helpers."""

from __future__ import annotations

from typing import Optional

try:  # pragma: no cover - import guard for PySide6
    from PySide6.QtWidgets import QApplication
except ImportError as exc:  # pragma: no cover - runtime dependency
    QApplication = None  # type: ignore
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None

from .mainwindow import MainWindow


def create_application(argv: Optional[list[str]] = None) -> QApplication:
    """Instantiate the Qt application and main window.

    Parameters
    ----------
    argv:
        Optional list of command-line arguments.

    Returns
    -------
    QApplication
        The configured Qt application instance ready to execute.
    """

    if QApplication is None:  # pragma: no cover - executed without PySide6
        raise RuntimeError("PySide6 is required to run the GUI") from _IMPORT_ERROR

    app = QApplication(argv or [])
    window = MainWindow()
    window.show()
    # Keep a reference to prevent premature garbage collection
    app._pynetworkgt_main_window = window  # type: ignore[attr-defined]
    return app


__all__ = ["create_application"]

