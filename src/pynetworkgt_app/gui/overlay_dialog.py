"""Dialog to configure scale bar and grid overlays."""

from __future__ import annotations

from typing import Tuple

try:
    from PySide6.QtWidgets import (
        QDialog,
        QDialogButtonBox,
        QDoubleSpinBox,
        QFormLayout,
        QLineEdit,
        QVBoxLayout,
    )
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("PySide6 is required to use the GUI components") from exc


class OverlayConfigDialog(QDialog):
    """Configure scale bar length/units and grid spacing."""

    def __init__(
        self,
        parent,
        *,
        scale_length: float,
        scale_units: str,
        grid_spacing: float,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Overlay Settings")

        self._scale_spin = QDoubleSpinBox()
        self._scale_spin.setRange(0.01, 1_000_000.0)
        self._scale_spin.setValue(max(scale_length, 0.01))
        self._scale_spin.setDecimals(3)

        self._units_edit = QLineEdit(scale_units)

        self._grid_spin = QDoubleSpinBox()
        self._grid_spin.setRange(0.01, 1_000_000.0)
        self._grid_spin.setValue(max(grid_spacing, 0.01))
        self._grid_spin.setDecimals(3)

        form = QFormLayout()
        form.addRow("Scale bar length", self._scale_spin)
        form.addRow("Scale bar units", self._units_edit)
        form.addRow("Grid spacing", self._grid_spin)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def values(self) -> Tuple[float, str, float]:
        return (
            float(self._scale_spin.value()),
            self._units_edit.text().strip() or "units",
            float(self._grid_spin.value()),
        )
