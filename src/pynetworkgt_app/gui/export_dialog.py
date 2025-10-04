"""Dialog for configuring canvas export options."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

try:  # pragma: no cover - import guard
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColor
    from PySide6.QtWidgets import (
        QCheckBox,
        QComboBox,
        QDialog,
        QDialogButtonBox,
        QFileDialog,
        QFormLayout,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QPushButton,
        QSpinBox,
        QVBoxLayout,
        QWidget,
        QColorDialog,
    )
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("PySide6 is required to use the GUI components") from exc


@dataclass
class ExportSettings:
    path: Path
    format: str
    width: int
    height: int
    dpi: int
    background: QColor
    title: str
    include_legend: bool
    include_scale_bar: bool
    include_grid: bool


class ExportDialog(QDialog):
    """Collect export configuration from the user."""

    FORMATS = ["PNG", "JPEG", "SVG"]

    def __init__(
        self,
        parent: Optional[QWidget],
        *,
        default_path: Path,
        default_width: int,
        default_height: int,
        show_scale_bar: bool,
        show_grid: bool,
        include_legend: bool,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Export Canvas")
        self._path = default_path
        self._background = QColor("#ffffff")

        self._path_edit = QLineEdit(str(default_path))
        browse_button = QPushButton("Browse…")
        browse_button.clicked.connect(self._select_path)

        path_row = QHBoxLayout()
        path_row.addWidget(self._path_edit)
        path_row.addWidget(browse_button)

        self._format_combo = QComboBox()
        self._format_combo.addItems(self.FORMATS)
        self._format_combo.currentTextChanged.connect(self._on_format_changed)
        self._set_format_from_path(default_path)

        self._width_spin = QSpinBox()
        self._width_spin.setRange(1, 100_000)
        self._width_spin.setValue(max(default_width, 1))

        self._height_spin = QSpinBox()
        self._height_spin.setRange(1, 100_000)
        self._height_spin.setValue(max(default_height, 1))

        self._dpi_spin = QSpinBox()
        self._dpi_spin.setRange(30, 1200)
        self._dpi_spin.setValue(96)

        self._background_button = QPushButton()
        self._background_button.clicked.connect(self._choose_background)
        self._update_background_button()

        self._title_edit = QLineEdit()
        self._legend_check = QCheckBox("Include legend")
        self._legend_check.setChecked(include_legend)

        self._scale_bar_check = QCheckBox("Include scale bar")
        self._scale_bar_check.setChecked(show_scale_bar)

        self._grid_check = QCheckBox("Include grid")
        self._grid_check.setChecked(show_grid)

        form = QFormLayout()
        form.addRow("File", path_row)
        form.addRow("Format", self._format_combo)
        form.addRow("Width (px)", self._width_spin)
        form.addRow("Height (px)", self._height_spin)
        form.addRow("DPI", self._dpi_spin)
        form.addRow("Background", self._background_button)
        form.addRow("Title", self._title_edit)
        options_row = QHBoxLayout()
        options_row.addWidget(self._legend_check)
        options_row.addWidget(self._scale_bar_check)
        options_row.addWidget(self._grid_check)
        form.addRow("Options", options_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.setLayout(layout)

        self.resize(420, self.sizeHint().height())

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------
    def _select_path(self) -> None:
        current_dir = self._path.parent if self._path else Path.home()
        filters = ";;".join(f"{fmt} (*.{fmt.lower()})" for fmt in self.FORMATS)
        selected, _ = QFileDialog.getSaveFileName(
            self,
            "Select export file",
            str(current_dir),
            filters,
        )
        if not selected:
            return
        self._path = Path(selected)
        self._path_edit.setText(str(self._path))
        self._set_format_from_path(self._path)

    def _on_format_changed(self, fmt: str) -> None:
        suffix = fmt.lower()
        if self._path.suffix.lower() != f".{suffix}":
            self._path = self._path.with_suffix(f".{suffix}")
            self._path_edit.setText(str(self._path))

    def _choose_background(self) -> None:
        color = QColorDialog.getColor(self._background, self, "Background colour")
        if not color.isValid():
            return
        self._background = color
        self._update_background_button()

    def _update_background_button(self) -> None:
        text = self._background.name()
        self._background_button.setText(text)
        luminance = self._background.lightness()
        text_color = "#000000" if luminance > 128 else "#ffffff"
        self._background_button.setStyleSheet(
            f"background-color: {text}; color: {text_color};"
        )

    def _set_format_from_path(self, path: Path) -> None:
        suffix = path.suffix.lower().lstrip('.')
        if suffix.upper() in self.FORMATS:
            idx = self.FORMATS.index(suffix.upper())
            self._format_combo.setCurrentIndex(idx)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def settings(self) -> ExportSettings:
        fmt = self._format_combo.currentText()
        path = Path(self._path_edit.text()).with_suffix(f".{fmt.lower()}")
        return ExportSettings(
            path=path,
            format=fmt,
            width=self._width_spin.value(),
            height=self._height_spin.value(),
            dpi=self._dpi_spin.value(),
            background=self._background,
            title=self._title_edit.text().strip(),
            include_legend=self._legend_check.isChecked(),
            include_scale_bar=self._scale_bar_check.isChecked(),
            include_grid=self._grid_check.isChecked(),
        )
