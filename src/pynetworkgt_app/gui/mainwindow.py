"""Main Qt window for the PyNetworkGT application."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

try:  # pragma: no cover - import guard for PySide6
    from PySide6.QtCore import QSettings, Qt
    from PySide6.QtGui import QAction, QActionGroup, QIcon, QPixmap, QColor
    from PySide6.QtWidgets import (
        QFileDialog,
        QLabel,
        QListWidget,
        QListWidgetItem,
        QMainWindow,
        QMessageBox,
        QSplitter,
        QVBoxLayout,
        QWidget,
        QMenu,
        QAbstractItemView,
        QColorDialog,
        QDialog,
        QInputDialog,
    )
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("PySide6 is required to use the GUI components") from exc

from ..core.fracture import FractureNetwork
from ..io import (
    FractureGpkgError,
    FractureTxtError,
    read_fracture_gpkg,
    read_fracture_txt,
)
from .canvas import CanvasLayer, NetworkCanvas
from .crs_dialog import CrsAssignmentDialog
from .export_dialog import ExportDialog
from .overlay_dialog import OverlayConfigDialog


@dataclass
class LayerEntry:
    """Association between GUI list item and rendered layer."""

    item: QListWidgetItem
    network: FractureNetwork
    canvas_layer: CanvasLayer
    color: QColor
    width: float


STYLE_PRESETS = {
    "Default": {
        "colors": [
            "#0097a7", "#c62828", "#2e7d32", "#1565c0", "#6a1b9a", "#f57f17",
        ],
        "width": 1.5,
    },
    "High Contrast": {
        "colors": [
            "#000000", "#ff1744", "#00e676", "#2979ff", "#ff9100", "#d500f9",
        ],
        "width": 2.0,
    },
    "Pastel": {
        "colors": [
            "#80cbc4", "#f48fb1", "#ce93d8", "#ffab91", "#9fa8da", "#b39ddb",
        ],
        "width": 1.8,
    },
}



class MainWindow(QMainWindow):
    """Primary application window with menus and layer management."""

    PROJECT_FILTER = "PyNetworkGT Project (*.pngt);;JSON (*.json);;All Files (*)"
    IMAGE_FILTER = "PNG Image (*.png);;All Files (*)"

    def __init__(self) -> None:
        super().__init__()
        self._project_path: Optional[Path] = None
        self._last_export_path: Optional[Path] = None
        self._last_open_dir: Optional[Path] = None
        self._current_style_preset: str = "Default"
        self._layer_entries: List[LayerEntry] = []
        self._settings = QSettings("PyNetworkGT", "PyNetworkGTApp")
        self._style_actions: Dict[str, QAction] = {}
        self._style_action_group: Optional[QActionGroup] = None
        self._last_used_crs: Optional[str] = None

        self._setup_actions()
        self._setup_ui()
        self._load_preferences()
        self._set_project_path(None)

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------
    def _setup_actions(self) -> None:
        self.open_file_action = QAction("Open…", self)
        self.open_file_action.setShortcut("Ctrl+O")
        self.open_file_action.triggered.connect(self.open_file_dialog)

        self.save_project_action = QAction("Save Project…", self)
        self.save_project_action.setShortcut("Ctrl+S")
        self.save_project_action.triggered.connect(self.save_project_dialog)

        self.load_project_action = QAction("Load Project…", self)
        self.load_project_action.setShortcut("Ctrl+L")
        self.load_project_action.triggered.connect(self.load_project_dialog)

        self.export_view_action = QAction("Export View…", self)
        self.export_view_action.setShortcut("Ctrl+E")
        self.export_view_action.triggered.connect(self.export_view_dialog)

        self.exit_action = QAction("Exit", self)
        self.exit_action.setShortcut("Ctrl+Q")
        self.exit_action.triggered.connect(self.close)

        self.remove_layer_action = QAction("Remove Layer", self)
        self.remove_layer_action.setShortcut("Delete")
        self.remove_layer_action.triggered.connect(self.remove_selected_layer)

        self.clear_layers_action = QAction("Clear Layers", self)
        self.clear_layers_action.setShortcut("Ctrl+Shift+Delete")
        self.clear_layers_action.triggered.connect(self.clear_layers)

        self.reset_view_action = QAction("Reset View", self)
        self.reset_view_action.setShortcut("Ctrl+R")
        self.reset_view_action.triggered.connect(self.reset_view)

        self.zoom_in_action = QAction("Zoom In", self)
        self.zoom_in_action.setShortcut("Ctrl+=")
        self.zoom_in_action.triggered.connect(self.zoom_in)

        self.zoom_out_action = QAction("Zoom Out", self)
        self.zoom_out_action.setShortcut("Ctrl+-")
        self.zoom_out_action.triggered.connect(self.zoom_out)

        self.toggle_scale_action = QAction("Show Scale Bar", self)
        self.toggle_scale_action.setCheckable(True)
        self.toggle_scale_action.setChecked(False)
        self.toggle_scale_action.triggered.connect(self._toggle_scale_bar)

        self.toggle_grid_action = QAction("Show Grid", self)
        self.toggle_grid_action.setCheckable(True)
        self.toggle_grid_action.setChecked(False)
        self.toggle_grid_action.triggered.connect(self._toggle_grid)

        self.configure_overlays_action = QAction("Configure Overlays…", self)
        self.configure_overlays_action.triggered.connect(self._configure_overlays)

        self.change_color_action = QAction("Change Color", self)
        self.change_color_action.setShortcut("Ctrl+Shift+C")
        self.change_color_action.triggered.connect(self.change_selected_layer_color)

        self.change_width_action = QAction("Change Width", self)
        self.change_width_action.setShortcut("Ctrl+Shift+W")
        self.change_width_action.triggered.connect(self.change_selected_layer_width)

    def _setup_ui(self) -> None:
        self.layer_list = QListWidget()
        self.layer_list.setSelectionMode(QListWidget.SingleSelection)
        self.layer_list.setDragDropMode(QAbstractItemView.InternalMove)
        self.layer_list.setDefaultDropAction(Qt.MoveAction)
        self.layer_list.setDragEnabled(True)
        self.layer_list.setAcceptDrops(True)
        self.layer_list.itemChanged.connect(self._on_layer_item_changed)
        self.layer_list.model().rowsMoved.connect(self._on_layers_reordered)
        self.layer_list.currentItemChanged.connect(self._on_current_layer_changed)
        self.layer_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.layer_list.customContextMenuRequested.connect(self._open_layer_context_menu)
        self.layer_list.setMinimumWidth(260)

        layer_panel = QWidget()
        layer_layout = QVBoxLayout(layer_panel)
        layer_layout.setContentsMargins(6, 6, 6, 6)
        layer_layout.setSpacing(6)

        header_label = QLabel("Layers")
        header_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        header_label.setStyleSheet("font-weight: bold;")
        layer_layout.addWidget(header_label)
        layer_layout.addWidget(self.layer_list)

        legend_label = QLabel("Legend")
        legend_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        legend_label.setStyleSheet("font-weight: bold; margin-top: 8px;")
        self.legend_list = QListWidget()
        self.legend_list.setSelectionMode(QAbstractItemView.NoSelection)
        self.legend_list.setFocusPolicy(Qt.NoFocus)
        layer_layout.addWidget(legend_label)
        layer_layout.addWidget(self.legend_list)

        self.canvas = NetworkCanvas()

        splitter = QSplitter()
        splitter.addWidget(layer_panel)
        splitter.addWidget(self.canvas)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([280, 920])

        self.setCentralWidget(splitter)

        file_menu = self.menuBar().addMenu("File")
        file_menu.addAction(self.open_file_action)
        file_menu.addAction(self.save_project_action)
        file_menu.addAction(self.load_project_action)
        file_menu.addSeparator()
        file_menu.addAction(self.export_view_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)

        layer_menu = self.menuBar().addMenu("Layers")
        self._style_action_group = QActionGroup(self)
        self._style_action_group.setExclusive(True)
        self._style_menu = layer_menu.addMenu("Style Preset")
        self._populate_style_menu()
        layer_menu.addSeparator()
        layer_menu.addAction(self.change_color_action)
        layer_menu.addAction(self.change_width_action)
        layer_menu.addSeparator()
        layer_menu.addAction(self.remove_layer_action)
        layer_menu.addAction(self.clear_layers_action)

        tools_menu = self.menuBar().addMenu("Tools")
        self._populate_tools_menu(tools_menu)

        view_menu = self.menuBar().addMenu("View")
        view_menu.addAction(self.zoom_in_action)
        view_menu.addAction(self.zoom_out_action)
        view_menu.addAction(self.reset_view_action)
        view_menu.addSeparator()
        view_menu.addAction(self.toggle_scale_action)
        view_menu.addAction(self.toggle_grid_action)
        view_menu.addAction(self.configure_overlays_action)

        for action in (
            self.open_file_action,
            self.save_project_action,
            self.load_project_action,
            self.export_view_action,
            self.remove_layer_action,
            self.clear_layers_action,
            self.reset_view_action,
            self.zoom_in_action,
            self.zoom_out_action,
            self.toggle_scale_action,
            self.toggle_grid_action,
            self.configure_overlays_action,
            self.change_color_action,
            self.change_width_action,
        ):
            self.addAction(action)

        self.statusBar().showMessage("Ready")
        self._update_action_states()

    def _populate_tools_menu(self, menu: QMenu) -> None:
        menu.addMenu("Digitising")
        menu.addMenu("Sampling")
        menu.addMenu("Geometry")
        topology_menu = menu.addMenu("Topology")
        self._populate_topology_menu(topology_menu)
        menu.addMenu("Flow")

    def _populate_topology_menu(self, menu: QMenu) -> None:
        menu.addAction("Branches and Nodes")
        menu.addAction("Define Clusters")
        menu.addAction("Identify Blocks")
        menu.addAction("Relationships")
        menu.addAction("Shortest Pathway")
        menu.addAction("Theoretical Blocks")
        menu.addAction("Topology Parameters")

    # ------------------------------------------------------------------
    # File handling
    # ------------------------------------------------------------------
    def open_file_dialog(self) -> None:
        filters = "Fracture Data (*.txt *.gpkg);;Text files (*.txt);;GeoPackage (*.gpkg)"
        default_dir = str(self._default_open_dir())
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open fracture dataset", default_dir, filters
        )
        if not file_path:
            return

        self.load_network(Path(file_path))

    def save_project_dialog(self) -> None:
        if not self._layer_entries:
            QMessageBox.information(self, "Save Project", "No layers to save.")
            return
        serializable = self._collect_serializable_layers()
        if not serializable:
            QMessageBox.warning(
                self,
                "Save Project",
                "None of the layers have an associated source file to save.",
            )
            return

        suggested = self._project_path or (Path.home() / "project.pngt")
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save project",
            str(suggested),
            self.PROJECT_FILTER,
        )
        if not file_path:
            return

        path = Path(file_path)
        try:
            data = {"layers": serializable}
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as exc:  # pragma: no cover
            QMessageBox.critical(self, "Save Project", f"Failed to save project: {exc}")
            return

        self._set_project_path(path)
        self.statusBar().showMessage(f"Project saved to {path}")

    def load_project_dialog(self) -> None:
        default_dir = self._project_path.parent if self._project_path else self._default_open_dir()
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load project",
            str(default_dir),
            self.PROJECT_FILTER,
        )
        if not file_path:
            return
        self._load_project_file(Path(file_path))

    def export_view_dialog(self) -> None:
        if not self._layer_entries:
            QMessageBox.information(self, "Export View", "No layers to export.")
            return

        if self._last_export_path is not None:
            default_path = self._last_export_path
        elif self._project_path is not None:
            default_path = self._project_path.with_name("export.png")
        else:
            default_path = Path.home() / "export.png"

        width, height = self.canvas.scene_dimensions()
        if width == 0 or height == 0:
            width, height = 1024, 768
        dialog = ExportDialog(
            self,
            default_path=default_path,
            default_width=width,
            default_height=height,
            show_scale_bar=self.canvas.scale_bar_visible(),
            show_grid=self.canvas.grid_visible(),
            include_legend=True,
        )

        if dialog.exec() != QDialog.Accepted:
            return

        settings = dialog.settings()
        if not settings.path.name:
            QMessageBox.warning(self, "Export View", "Please provide a valid filename.")
            return
        success = self.canvas.export_image(
            settings.path,
            size=(settings.width, settings.height),
            background=settings.background,
            dpi=settings.dpi,
            fmt=settings.format,
            title=settings.title,
            include_legend=settings.include_legend,
            include_scale_bar=settings.include_scale_bar,
            include_grid=settings.include_grid,
        )

        if success:
            self._last_export_path = settings.path
            self._settings.setValue("last_export_path", str(settings.path))
            self.statusBar().showMessage(f"View exported to {settings.path}")
        else:
            QMessageBox.warning(self, "Export View", "Failed to export image.")

    def load_network(self, path: Path) -> None:
        try:
            network = self._read_network(path)
        except (FractureTxtError, FractureGpkgError) as exc:
            QMessageBox.critical(self, "Failed to load", str(exc))
            return
        except Exception as exc:  # pragma: no cover
            QMessageBox.critical(self, "Unexpected error", str(exc))
            return

        self._assign_missing_crs(network)
        label = path.name
        self.add_network_layer(network, label=label)
        self._last_open_dir = path.parent
        self._settings.setValue("last_open_dir", str(self._last_open_dir))
        self.statusBar().showMessage(f"Loaded {label}")
        self._set_project_path(None)

    def _read_network(self, path: Path) -> FractureNetwork:
        suffix = path.suffix.lower()
        if suffix == ".txt":
            return read_fracture_txt(path)
        if suffix == ".gpkg":
            return read_fracture_gpkg(path)
        raise FractureTxtError(f"Unsupported file extension: {suffix}")

    def _assign_missing_crs(self, network: FractureNetwork) -> None:
        if network.crs:
            return

        dialog = CrsAssignmentDialog(self, last_crs=self._last_used_crs)
        if dialog.exec() != QDialog.Accepted:
            return

        crs_value = dialog.selected_crs()
        if not crs_value:
            return

        network.crs = crs_value
        self._last_used_crs = crs_value
        self._settings.setValue("last_crs", crs_value)
        label = network.source.name if isinstance(network.source, Path) else None
        target = str(label) if label else "dataset"
        self.statusBar().showMessage(f"Assigned CRS {crs_value} to {target}", 5000)

    # ------------------------------------------------------------------
    # Layer handling
    # ------------------------------------------------------------------
    def add_network_layer(self, network: FractureNetwork, label: Optional[str] = None) -> None:
        label = label or f"Fracture Network {len(self._layer_entries) + 1}"

        item = QListWidgetItem(label)
        tooltip_parts = []
        if network.source:
            tooltip_parts.append(str(network.source))
        else:
            tooltip_parts.append(label)
        tooltip_parts.append(f"CRS: {network.crs}" if network.crs else "CRS: not set")
        item.setToolTip("\n".join(tooltip_parts))
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsDragEnabled)
        item.setCheckState(Qt.Checked)
        self.layer_list.addItem(item)
        self.layer_list.setCurrentItem(item)

        color = self._color_for_layer_index(len(self._layer_entries))
        width = self._preset_width()
        canvas_layer = self.canvas.add_network(
            network, name=label, color=color, width=width
        )
        entry = LayerEntry(item=item, network=network, canvas_layer=canvas_layer, color=color, width=width)
        self._layer_entries.append(entry)
        self.canvas.reorder_layers([entry.canvas_layer for entry in self._layer_entries])
        self._refresh_legend()
        self._update_action_states()

    def clear_layers(self) -> None:
        self.layer_list.clear()
        if hasattr(self, 'legend_list'):
            self.legend_list.clear()
        self.canvas.clear_layers()
        self._layer_entries.clear()
        self.reset_view()
        self._set_project_path(None)
        self.statusBar().showMessage("Cleared layers")
        self._refresh_legend()
        self._update_action_states()

    def reset_view(self) -> None:
        self.canvas.reset_view()

    def remove_selected_layer(self) -> None:
        entry = self._current_entry()
        if entry is None:
            return
        self._remove_entry(entry)

    def change_selected_layer_color(self) -> None:
        entry = self._current_entry()
        if entry is None:
            return
        current_color = entry.canvas_layer.color
        color = QColorDialog.getColor(current_color, self, "Select layer color")
        if not color.isValid():
            return
        self.canvas.update_layer_style(entry.canvas_layer, color=color)
        entry.color = color
        self._mark_style_custom()
        self._refresh_legend()
        self.statusBar().showMessage(f"Updated color for {entry.item.text()}")

    def change_selected_layer_width(self) -> None:
        entry = self._current_entry()
        if entry is None:
            return
        current_width = entry.canvas_layer.width
        value, ok = QInputDialog.getDouble(
            self,
            "Line width",
            "Width (pixels):",
            current_width,
            0.1,
            10.0,
            decimals=2,
        )
        if not ok:
            return
        self.canvas.update_layer_style(entry.canvas_layer, width=value)
        entry.width = value
        self._mark_style_custom()
        self.statusBar().showMessage(f"Updated width for {entry.item.text()}")

    def apply_style_preset(self, name: str) -> None:
        if name not in STYLE_PRESETS:
            self._mark_style_custom()
            return
        preset = STYLE_PRESETS[name]
        colors = preset.get("colors", [])
        if not colors:
            colors = STYLE_PRESETS["Default"]["colors"]
        width = float(preset.get("width", 1.5))
        for index, entry in enumerate(self._layer_entries):
            color = QColor(colors[index % len(colors)])
            entry.color = color
            entry.width = width
            self.canvas.update_layer_style(entry.canvas_layer, color=color, width=width)
        self._current_style_preset = name
        self._settings.setValue("style_preset", name)
        self._set_style_action_checked(name)
        self._refresh_legend()

    def zoom_in(self) -> None:
        self.canvas.zoom_in()
        self.statusBar().showMessage("Zoomed in")

    def zoom_out(self) -> None:
        self.canvas.zoom_out()
        self.statusBar().showMessage("Zoomed out")

    def _remove_entry(self, entry: LayerEntry) -> None:
        row = self.layer_list.row(entry.item)
        self.layer_list.takeItem(row)
        self.canvas.remove_layer(entry.canvas_layer)
        if entry in self._layer_entries:
            self._layer_entries.remove(entry)
        if self._layer_entries:
            self.canvas.reorder_layers([e.canvas_layer for e in self._layer_entries])
        else:
            self.canvas.reset_view()
        self.statusBar().showMessage(f"Removed {entry.item.text()}")
        self._refresh_legend()
        self._update_action_states()

    def _find_entry(self, item: QListWidgetItem) -> Optional[LayerEntry]:
        for entry in self._layer_entries:
            if entry.item is item:
                return entry
        return None

    def _current_entry(self) -> Optional[LayerEntry]:
        item = self.layer_list.currentItem()
        if item is None:
            return None
        return self._find_entry(item)

    def _on_current_layer_changed(self, *_args) -> None:
        self._update_action_states()

    def _on_layer_item_changed(self, item: QListWidgetItem) -> None:
        entry = self._find_entry(item)
        if entry is None:
            return
        visible = item.checkState() == Qt.Checked
        self.canvas.set_layer_visibility(entry.canvas_layer, visible)
        self.statusBar().showMessage(
            f"{'Shown' if visible else 'Hidden'} {entry.item.text()}"
        )
        self._refresh_legend()
        self._update_action_states()

    def _on_layers_reordered(self, *args) -> None:
        ordered_items = [self.layer_list.item(index) for index in range(self.layer_list.count())]
        ordered_entries: List[LayerEntry] = []
        for list_item in ordered_items:
            entry = self._find_entry(list_item)
            if entry is not None:
                ordered_entries.append(entry)
        if len(ordered_entries) != len(self._layer_entries):
            return
        self._layer_entries = ordered_entries
        self.canvas.reorder_layers([entry.canvas_layer for entry in self._layer_entries])
        self._refresh_legend()
        self.statusBar().showMessage("Reordered layers")

    def _populate_style_menu(self) -> None:
        self._style_actions = {}
        self._style_menu.clear()
        for name in STYLE_PRESETS.keys():
            action = self._style_menu.addAction(name)
            action.setCheckable(True)
            action.triggered.connect(self._make_style_callback(name))
            self._style_action_group.addAction(action)
            self._style_actions[name] = action
        custom_action = self._style_menu.addAction("Custom")
        custom_action.setCheckable(True)
        custom_action.triggered.connect(self._custom_style_selected)
        self._style_action_group.addAction(custom_action)
        self._style_actions["Custom"] = custom_action

    def _make_style_callback(self, name: str):
        def _callback(checked: bool) -> None:
            if checked:
                self.apply_style_preset(name)
        return _callback

    def _custom_style_selected(self, checked: bool) -> None:
        if checked:
            self._mark_style_custom()

    def _set_style_action_checked(self, name: str) -> None:
        if not self._style_actions:
            return
        for action_name, action in self._style_actions.items():
            action.blockSignals(True)
            action.setChecked(action_name == name)
            action.blockSignals(False)

    def _mark_style_custom(self) -> None:
        self._current_style_preset = "Custom"
        self._settings.setValue("style_preset", "Custom")
        self._set_style_action_checked("Custom")

    def _current_preset_data(self) -> Dict[str, Any]:
        return STYLE_PRESETS.get(self._current_style_preset, STYLE_PRESETS.get("Default", {}))

    def _color_for_layer_index(self, index: int) -> QColor:
        preset = self._current_preset_data()
        colors = preset.get("colors", STYLE_PRESETS["Default"]["colors"])
        if not colors:
            colors = STYLE_PRESETS["Default"]["colors"]
        return QColor(colors[index % len(colors)])

    def _preset_width(self) -> float:
        preset = self._current_preset_data()
        return float(preset.get("width", 1.5))

    def _refresh_legend(self) -> None:
        if not hasattr(self, "legend_list"):
            return
        self.legend_list.clear()
        for entry in self._layer_entries:
            base_label = entry.item.text()
            text = base_label
            if entry.item.checkState() != Qt.Checked:
                text += " (hidden)"
            crs_info = entry.network.crs or "CRS not set"
            width_info = f"Width: {entry.width:.2f} px"
            pixmap = QPixmap(16, 16)
            pixmap.fill(entry.color)
            icon = QIcon(pixmap)
            legend_item = QListWidgetItem(icon, text)
            legend_item.setFlags(Qt.ItemIsEnabled)
            legend_item.setToolTip(
                "\n".join(
                    [
                        base_label,
                        f"CRS: {crs_info}",
                        width_info,
                    ]
                )
            )
            self.legend_list.addItem(legend_item)

    def _refresh_canvas_layers(self, fit: bool = False) -> None:
        if not self._layer_entries:
            return
        current_item = self.layer_list.currentItem()
        self.canvas.remove_all_layers()
        for entry in self._layer_entries:
            canvas_layer = self.canvas.add_network(
                entry.network,
                name=entry.item.text(),
                color=entry.color,
                width=entry.width,
                auto_fit=fit,
            )
            entry.canvas_layer = canvas_layer
            visible = entry.item.checkState() == Qt.Checked
            self.canvas.set_layer_visibility(canvas_layer, visible)
        self.canvas.reorder_layers([entry.canvas_layer for entry in self._layer_entries])
        if fit:
            self.canvas.reset_view()
        if current_item is not None:
            self.layer_list.setCurrentItem(current_item)
        self._refresh_legend()


    def _toggle_scale_bar(self, checked: bool) -> None:
        self.canvas.set_scale_bar_visible(checked)
        self._settings.setValue("scale_bar_visible", checked)
        self.canvas.viewport().update()

    def _toggle_grid(self, checked: bool) -> None:
        self.canvas.set_grid_visible(checked)
        self._settings.setValue("grid_visible", checked)
        self.canvas.viewport().update()

    def _configure_overlays(self) -> None:
        dialog = OverlayConfigDialog(
            self,
            scale_length=self.canvas.scale_bar_parameters()[0],
            scale_units=self.canvas.scale_bar_parameters()[1],
            grid_spacing=self.canvas.grid_spacing(),
        )
        if dialog.exec() != QDialog.Accepted:
            return
        length, units, spacing = dialog.values()
        self.canvas.set_scale_bar_parameters(length, units)
        self.canvas.set_grid_spacing(spacing)
        self._settings.setValue("scale_bar_length", length)
        self._settings.setValue("scale_bar_units", units)
        self._settings.setValue("grid_spacing", spacing)
        self.canvas.viewport().update()

    def _default_open_dir(self) -> Path:
        if self._last_open_dir and self._last_open_dir.exists():
            return self._last_open_dir
        if self._project_path is not None:
            return self._project_path.parent
        return Path.home()

    def _load_preferences(self) -> None:
        last_export = self._settings.value("last_export_path")
        if last_export:
            self._last_export_path = Path(str(last_export))
        last_open = self._settings.value("last_open_dir")
        if last_open:
            self._last_open_dir = Path(str(last_open))
        last_crs = self._settings.value("last_crs")
        if last_crs:
            self._last_used_crs = str(last_crs)
        scale_value = str(self._settings.value("scale_bar_visible", "true")).lower()
        scale_flag = scale_value in ("1", "true", "yes")
        self.toggle_scale_action.blockSignals(True)
        self.toggle_scale_action.setChecked(scale_flag)
        self.toggle_scale_action.blockSignals(False)
        self.canvas.set_scale_bar_visible(scale_flag)

        grid_value = str(self._settings.value("grid_visible", "false")).lower()
        grid_flag = grid_value in ("1", "true", "yes")
        self.toggle_grid_action.blockSignals(True)
        self.toggle_grid_action.setChecked(grid_flag)
        self.toggle_grid_action.blockSignals(False)
        self.canvas.set_grid_visible(grid_flag)

        length_value = self._settings.value("scale_bar_length")
        if length_value is not None:
            try:
                self.canvas.set_scale_bar_parameters(float(length_value), self.canvas.scale_bar_parameters()[1])
            except ValueError:
                pass
        units_value = self._settings.value("scale_bar_units")
        if units_value:
            self.canvas.set_scale_bar_parameters(self.canvas.scale_bar_parameters()[0], str(units_value))
        spacing_value = self._settings.value("grid_spacing")
        if spacing_value is not None:
            try:
                self.canvas.set_grid_spacing(float(spacing_value))
            except ValueError:
                pass

        style_value = str(self._settings.value("style_preset", "Default"))
        if style_value not in STYLE_PRESETS and style_value != "Custom":
            style_value = "Default"
        self._current_style_preset = style_value
        self._set_style_action_checked(style_value if style_value in self._style_actions else "Custom")
    def _open_layer_context_menu(self, position) -> None:
        item = self.layer_list.itemAt(position)
        if item is not None:
            self.layer_list.setCurrentItem(item)

        self._update_action_states()

        menu = QMenu(self.layer_list)
        menu.addAction(self.open_file_action)
        menu.addSeparator()
        menu.addAction(self.change_color_action)
        menu.addAction(self.change_width_action)
        menu.addSeparator()
        menu.addAction(self.zoom_in_action)
        menu.addAction(self.zoom_out_action)
        menu.addAction(self.reset_view_action)
        menu.addSeparator()
        menu.addAction(self.toggle_scale_action)
        menu.addAction(self.toggle_grid_action)
        menu.addAction(self.configure_overlays_action)
        menu.addSeparator()
        menu.addAction(self.remove_layer_action)
        menu.addAction(self.clear_layers_action)
        menu.exec(self.layer_list.mapToGlobal(position))

    # ------------------------------------------------------------------
    # Project helpers
    # ------------------------------------------------------------------
    def _collect_serializable_layers(self) -> List[Dict[str, Any]]:
        layers = []
        for entry in self._layer_entries:
            source = entry.network.source
            if source is None:
                continue
            layers.append(
                {
                    "path": str(source),
                    "label": entry.item.text(),
                    "visible": entry.item.checkState() == Qt.Checked,
                    "color": entry.color.name(),
                    "width": entry.width,
                    "crs": entry.network.crs,
                }
            )
        return layers

    def _load_project_file(self, path: Path) -> None:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover
            QMessageBox.critical(self, "Load Project", f"Failed to read project: {exc}")
            return

        layers = data.get("layers", [])
        if not isinstance(layers, list):
            QMessageBox.critical(self, "Load Project", "Invalid project format.")
            return

        self.clear_layers()
        skipped = []

        for layer in layers:
            try:
                file_path = Path(layer["path"])
            except KeyError:
                skipped.append("Missing path entry in project.")
                continue

            label = layer.get("label") or file_path.name
            color = layer.get("color")
            width = float(layer.get("width", 1.5))
            visible = bool(layer.get("visible", True))
            stored_crs = layer.get("crs")

            if not file_path.exists():
                skipped.append(f"File not found: {file_path}")
                continue

            try:
                network = self._read_network(file_path)
            except Exception as exc:
                skipped.append(f"Failed to load {file_path}: {exc}")
                continue

            if stored_crs and not network.crs:
                network.crs = str(stored_crs)

            self.add_network_layer(network, label=label)
            entry = self._layer_entries[-1]

            if color:
                self.canvas.update_layer_style(entry.canvas_layer, color=color)
            if width:
                self.canvas.update_layer_style(entry.canvas_layer, width=width)

            entry.color = entry.canvas_layer.color
            entry.width = entry.canvas_layer.width

            self.layer_list.blockSignals(True)
            entry.item.setCheckState(Qt.Checked if visible else Qt.Unchecked)
            self.layer_list.blockSignals(False)
            self.canvas.set_layer_visibility(entry.canvas_layer, visible)

        self._set_project_path(path)
        self._update_action_states()
        self._refresh_legend()
        self._mark_style_custom()
        self._last_open_dir = path.parent
        self._settings.setValue("last_open_dir", str(self._last_open_dir))

        if skipped:
            QMessageBox.warning(
                self,
                "Load Project",
                "\n".join(skipped),
            )
        else:
            self.statusBar().showMessage(f"Project loaded from {path}")

    def _set_project_path(self, path: Optional[Path]) -> None:
        self._project_path = path
        title = "PyNetworkGT"
        if path:
            title += f" — {path.name}"
        self.setWindowTitle(title)

    def _update_action_states(self) -> None:
        has_layers = bool(self._layer_entries)
        has_selection = self.layer_list.currentItem() is not None
        has_serializable = any(entry.network.source for entry in self._layer_entries)

        self.remove_layer_action.setEnabled(has_selection)
        self.clear_layers_action.setEnabled(has_layers)
        self.change_color_action.setEnabled(has_selection)
        self.change_width_action.setEnabled(has_selection)
        self.zoom_in_action.setEnabled(has_layers)
        self.zoom_out_action.setEnabled(has_layers)
        self.save_project_action.setEnabled(has_serializable)
        self.export_view_action.setEnabled(has_layers)
        self.toggle_scale_action.blockSignals(True)
        self.toggle_scale_action.setChecked(self.canvas.scale_bar_visible())
        self.toggle_scale_action.blockSignals(False)
        self.toggle_grid_action.blockSignals(True)
        self.toggle_grid_action.setChecked(self.canvas.grid_visible())
        self.toggle_grid_action.blockSignals(False)

    def _save_preferences(self) -> None:
        if self._last_export_path is not None:
            self._settings.setValue("last_export_path", str(self._last_export_path))
        if self._last_open_dir is not None:
            self._settings.setValue("last_open_dir", str(self._last_open_dir))
        self._settings.setValue("scale_bar_visible", self.canvas.scale_bar_visible())
        self._settings.setValue("grid_visible", self.canvas.grid_visible())
        length, units = self.canvas.scale_bar_parameters()
        self._settings.setValue("scale_bar_length", length)
        self._settings.setValue("scale_bar_units", units)
        self._settings.setValue("grid_spacing", self.canvas.grid_spacing())
        self._settings.setValue("style_preset", self._current_style_preset)
        if self._last_used_crs:
            self._settings.setValue("last_crs", self._last_used_crs)

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self._save_preferences()
        super().closeEvent(event)
