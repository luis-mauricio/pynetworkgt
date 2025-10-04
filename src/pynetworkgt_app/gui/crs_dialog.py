"""Dialog used to assign a coordinate reference system to a dataset."""

from __future__ import annotations

from typing import Optional

try:  # pragma: no cover - import guard for PySide6
    from PySide6.QtWidgets import (
        QDialog,
        QDialogButtonBox,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMessageBox,
        QVBoxLayout,
        QWidget,
    )
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("PySide6 is required to use the GUI components") from exc


class CrsAssignmentDialog(QDialog):
    """Collect a CRS definition (EPSG code) from the user."""

    def __init__(self, parent: Optional[QWidget] = None, *, last_crs: Optional[str] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Assign Coordinate Reference System")
        self._selected_crs: Optional[str] = None

        self._epsg_edit = QLineEdit()
        self._epsg_edit.setPlaceholderText("e.g. EPSG:4326 or 4326")
        if last_crs:
            self._epsg_edit.setText(last_crs)

        message = QLabel(
            "The input file does not declare a CRS. Provide an EPSG code to be associated with the dataset.\n"
            "Leave the dialog without confirming to keep the dataset unreferenced."
        )
        message.setWordWrap(True)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(message)
        layout.addWidget(self._epsg_edit)
        layout.addWidget(buttons)
        self.setLayout(layout)

        self.resize(420, self.sizeHint().height())

    # ------------------------------------------------------------------
    # Dialog helpers
    # ------------------------------------------------------------------
    def selected_crs(self) -> Optional[str]:
        """Return the CRS string chosen by the user (if any)."""

        return self._selected_crs

    def _on_accept(self) -> None:
        value = self._normalise_epsg(self._epsg_edit.text())
        if not value:
            QMessageBox.warning(
                self,
                "Assign Coordinate Reference System",
                "Enter a valid EPSG code (for example 4326) or choose Cancel to skip.",
            )
            return
        self._selected_crs = value
        self.accept()

    @staticmethod
    def _normalise_epsg(text: str) -> str:
        value = text.strip()
        if not value:
            return ""
        upper = value.upper()
        if upper.startswith("EPSG:"):
            suffix = upper.split("EPSG:", 1)[1]
        else:
            suffix = upper
        suffix = suffix.strip()
        if not suffix.isdigit():
            return ""
        return f"EPSG:{suffix}"


__all__ = ["CrsAssignmentDialog"]

