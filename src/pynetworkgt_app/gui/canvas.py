"""Graphics canvas for displaying fracture networks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from shapely.geometry.base import BaseGeometry

try:  # pragma: no cover - import guard for PySide6
    from PySide6.QtCore import QPointF, QRectF, QSize, Qt
    from PySide6.QtGui import QColor, QCursor, QFont, QFontMetrics, QImage, QPainter, QPainterPath, QPen
    from PySide6.QtWidgets import QGraphicsPathItem, QGraphicsScene, QGraphicsView
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("PySide6 is required to use the GUI components") from exc

from ..core.fracture import FractureNetwork


@dataclass
class CanvasLayer:
    """Represents an individual layer rendered on the canvas."""

    name: str
    items: List[QGraphicsPathItem]
    color: QColor
    width: float
    z_value: float = 0.0


class NetworkCanvas(QGraphicsView):
    """2D canvas backed by QGraphicsView/QGraphicsScene."""

    DEFAULT_COLORS = [
        Qt.darkCyan,
        Qt.darkRed,
        Qt.darkGreen,
        Qt.darkBlue,
        Qt.darkMagenta,
        Qt.darkYellow,
    ]

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        self.setRenderHint(QPainter.Antialiasing, True)
        self.setRenderHint(QPainter.TextAntialiasing, True)
        self.setViewportUpdateMode(QGraphicsView.BoundingRectViewportUpdate)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setCursor(QCursor(Qt.OpenHandCursor))

        self._layers: List[CanvasLayer] = []
        self._color_index = 0
        self._auto_fit_pending = True
        self._zoom_limits = (0.05, 100.0)
        self._zoom_step = 1.25
        self._is_panning = False
        self._pan_start: Optional[QPointF] = None
        self._show_scale_bar = False
        self._show_grid = False
        self._scale_bar_length = 100.0
        self._scale_bar_units = 'units'
        self._grid_spacing = 100.0
        self._grid_pen = QPen(QColor(0, 0, 0, 100), 1, Qt.SolidLine)
        self._scale_pen = QPen(Qt.black, 2)
        self._font = QFont()

    # ------------------------------------------------------------------
    # Layer handling
    # ------------------------------------------------------------------
    def clear_layers(self) -> None:
        for layer in self._layers:
            for item in layer.items:
                self._scene.removeItem(item)
        self._layers.clear()
        self._scene.clear()
        self.resetTransform()
        self._color_index = 0
        self._auto_fit_pending = True

    def add_network(
        self,
        network: FractureNetwork,
        *,
        name: Optional[str] = None,
        color: Optional[QColor] = None,
        width: float = 1.5,
        auto_fit: bool = True,
    ) -> CanvasLayer:
        """Render a fracture network on the canvas."""

        layer_name = name or network.source.name if network.source else "Network"
        qcolor = self._coerce_color(color)

        painter_path = QPainterPath()
        for fracture in network.lines:
            path = self._create_path(fracture.geometry)
            if path is not None:
                painter_path.addPath(path)

        pen = QPen(qcolor)
        pen.setWidthF(width)

        item = QGraphicsPathItem(painter_path)
        item.setPen(pen)
        self._scene.addItem(item)

        layer = CanvasLayer(name=layer_name, items=[item], color=qcolor, width=width)
        self._layers.append(layer)
        self.reorder_layers(self._layers)
        if auto_fit:
            self._auto_fit_pending = True
            self._fit_scene(force=True)
        else:
            self._fit_scene(force=False)
        return layer

    def remove_layer(self, layer: CanvasLayer) -> None:
        if layer not in self._layers:
            return
        for item in layer.items:
            self._scene.removeItem(item)
        self._layers.remove(layer)
        self._scene.update()
        self._fit_scene()

    def set_layer_visibility(self, layer: CanvasLayer, visible: bool) -> None:
        if layer not in self._layers:
            return
        for item in layer.items:
            item.setVisible(visible)
        self._scene.update()

    def reorder_layers(self, ordered_layers: List[CanvasLayer]) -> None:
        ordered: List[CanvasLayer] = []
        for layer in ordered_layers:
            if layer in self._layers and layer not in ordered:
                ordered.append(layer)
        for layer in self._layers:
            if layer not in ordered:
                ordered.append(layer)
        self._layers = ordered
        total = len(self._layers)
        for index, layer in enumerate(self._layers):
            z_value = float(total - index)
            layer.z_value = z_value
            for item in layer.items:
                item.setZValue(z_value)
        self._scene.update()
        self._fit_scene()

    def update_layer_style(
        self,
        layer: CanvasLayer,
        *,
        color: Optional[QColor] = None,
        width: Optional[float] = None,
    ) -> None:
        if layer not in self._layers:
            return
        if color is not None:
            layer.color = QColor(color)
        if width is not None:
            layer.width = width
        for item in layer.items:
            pen = item.pen()
            pen.setColor(layer.color)
            pen.setWidthF(layer.width)
            item.setPen(pen)
        self._scene.update()

    def reset_view(self) -> None:
        self._auto_fit_pending = True
        self._fit_scene(force=True)

    def export_image(
        self,
        path: Path,
        *,
        size: Optional[Tuple[int, int]] = None,
        background: QColor | int = Qt.white,
        dpi: int = 96,
        fmt: str = "PNG",
        title: Optional[str] = None,
        include_legend: bool = False,
        include_scale_bar: Optional[bool] = None,
        include_grid: Optional[bool] = None,
    ) -> bool:
        """Export the current scene to disk using the desired settings."""

        if not self._layers:
            return False

        scene_rect = self._scene.sceneRect()
        if scene_rect.isNull():
            scene_rect = self._scene.itemsBoundingRect()
        if scene_rect.isNull():
            return False

        if size is None:
            width = max(int(scene_rect.width()), 1)
            height = max(int(scene_rect.height()), 1)
        else:
            width = max(int(size[0]), 1)
            height = max(int(size[1]), 1)

        fmt = fmt.upper()
        bg_color = QColor(background)
        title_text = title or ""
        show_scale = self._show_scale_bar if include_scale_bar is None else include_scale_bar
        show_grid = self._show_grid if include_grid is None else include_grid

        if fmt == "SVG":
            try:
                from PySide6.QtSvg import QSvgGenerator  # type: ignore
            except ImportError:
                return False

            generator = QSvgGenerator()
            generator.setFileName(str(path))
            generator.setSize(QSize(width, height))
            generator.setViewBox(QRectF(0, 0, width, height))
            if title_text:
                generator.setTitle(title_text)

            painter = QPainter(generator)
            painter.fillRect(QRectF(0, 0, width, height), bg_color)
            self._render_export(
                painter,
                scene_rect,
                width,
                height,
                title_text,
                include_legend,
                show_scale,
                show_grid,
            )
            painter.end()
            return True

        image = QImage(width, height, QImage.Format_ARGB32)
        image.fill(bg_color)
        dots_per_meter = int(dpi * 39.3701)
        image.setDotsPerMeterX(dots_per_meter)
        image.setDotsPerMeterY(dots_per_meter)

        painter = QPainter(image)
        self._render_export(
            painter,
            scene_rect,
            width,
            height,
            title_text,
            include_legend,
            show_scale,
            show_grid,
        )
        painter.end()

        return image.save(str(path), fmt)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def scene_dimensions(self) -> Tuple[int, int]:
        """Return the approximate width/height of the current scene."""

        rect = self._scene.sceneRect()
        if rect.isNull():
            rect = self._scene.itemsBoundingRect()
        if rect.isNull():
            return (0, 0)
        return max(int(rect.width()), 1), max(int(rect.height()), 1)

    def remove_all_layers(self) -> None:
        """Remove graphics items without altering view transforms."""

        for layer in self._layers:
            for item in layer.items:
                self._scene.removeItem(item)
        self._layers.clear()


    def _render_export(
        self,
        painter: QPainter,
        scene_rect: QRectF,
        width: int,
        height: int,
        title: str,
        include_legend: bool,
        include_scale: bool,
        include_grid: bool,
    ) -> None:
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)
        target = QRectF(0, 0, width, height)
        self._scene.render(painter, target=target, source=scene_rect)
        if include_grid and self._grid_spacing > 0:
            self._draw_export_grid(painter, scene_rect, width, height)
        if include_scale and self._scale_bar_length > 0:
            self._draw_export_scale_bar(painter, scene_rect, width, height)
        self._draw_overlays(painter, width, height, title, include_legend)

    def _draw_overlays(
        self,
        painter: QPainter,
        width: int,
        height: int,
        title: str,
        include_legend: bool,
    ) -> None:
        margin = 16
        painter.save()
        painter.setPen(QPen(Qt.black))
        font = self._font
        painter.setFont(font)
        metrics = QFontMetrics(font)
        y_offset = margin

        if title:
            painter.drawText(margin, y_offset + metrics.ascent(), title)
            y_offset += metrics.height() + 8

        if include_legend:
            legend_layers = [
                layer
                for layer in self._layers
                if any(item.isVisible() for item in layer.items)
            ]
            for layer in legend_layers:
                swatch_y = y_offset + metrics.height() / 2
                painter.setPen(QPen(layer.color, 3))
                painter.drawLine(margin, swatch_y, margin + 24, swatch_y)
                painter.setPen(QPen(Qt.black))
                painter.drawText(margin + 32, y_offset + metrics.ascent(), layer.name)
                y_offset += metrics.height() + 4

        painter.restore()

    def _draw_export_grid(
        self,
        painter: QPainter,
        scene_rect: QRectF,
        width: int,
        height: int,
    ) -> None:
        spacing = self._grid_spacing
        if spacing <= 0:
            return
        painter.save()
        painter.setPen(self._grid_pen)
        left = min(scene_rect.left(), scene_rect.right())
        right = max(scene_rect.left(), scene_rect.right())
        bottom = min(scene_rect.bottom(), scene_rect.top())
        top = max(scene_rect.bottom(), scene_rect.top())

        if right - left > spacing * 10_000:
            painter.restore()
            return

        scale_x = width / scene_rect.width() if scene_rect.width() else 1.0
        scale_y = height / scene_rect.height() if scene_rect.height() else 1.0

        start_x = spacing * int(left // spacing)
        if start_x > left:
            start_x -= spacing
        x = start_x
        count = 0
        while x <= right and count < 2000:
            px = (x - left) * scale_x
            painter.drawLine(px, 0, px, height)
            x += spacing
            count += 1

        start_y = spacing * int(bottom // spacing)
        if start_y > bottom:
            start_y -= spacing
        y = start_y
        count = 0
        while y <= top and count < 2000:
            py = height - (y - bottom) * scale_y
            painter.drawLine(0, py, width, py)
            y += spacing
            count += 1
        painter.restore()

    def _draw_export_scale_bar(
        self,
        painter: QPainter,
        scene_rect: QRectF,
        width: int,
        height: int,
    ) -> None:
        if self._scale_bar_length <= 0:
            return
        painter.save()
        margin = 40
        scale_x = width / scene_rect.width() if scene_rect.width() else 1.0
        pixel_per_unit = scale_x
        bar_pixels = self._scale_bar_length * pixel_per_unit
        max_pixels = width * 0.5
        if bar_pixels > max_pixels:
            bar_pixels = max_pixels
        actual_units = bar_pixels / pixel_per_unit if pixel_per_unit else self._scale_bar_length
        x_start = margin
        x_end = x_start + bar_pixels
        y = height - margin
        painter.setPen(self._scale_pen)
        painter.drawLine(int(x_start), int(y), int(x_end), int(y))
        painter.drawLine(int(x_start), int(y - 5), int(x_start), int(y + 5))
        painter.drawLine(int(x_end), int(y - 5), int(x_end), int(y + 5))
        text = f"{actual_units:.2f} {self._scale_bar_units}"
        painter.setFont(self._font)
        metrics = QFontMetrics(self._font)
        painter.drawText(int(x_start), int(y - 8), text)
        painter.restore()

    def _fit_scene(self, force: bool = False) -> None:
        if not self._layers:
            return
        scene_rect = self._scene.itemsBoundingRect()
        if scene_rect.isNull():
            return
        margin = max(scene_rect.width(), scene_rect.height()) * 0.05
        scene_rect = scene_rect.adjusted(-margin, -margin, margin, margin)
        self._scene.setSceneRect(scene_rect)
        if force or self._auto_fit_pending:
            self.resetTransform()
            self.fitInView(scene_rect, Qt.KeepAspectRatio)
            self._auto_fit_pending = False

    def _create_path(self, geometry: BaseGeometry) -> Optional[QPainterPath]:
        geom_type = geometry.geom_type
        if geom_type == "LineString":
            return self._path_from_linestring(geometry)
        if geom_type == "MultiLineString":
            path = QPainterPath()
            for part in geometry.geoms:  # type: ignore[attr-defined]
                sub = self._path_from_linestring(part)
                if sub is not None:
                    path.addPath(sub)
            return path
        return None

    def _path_from_linestring(self, linestring) -> Optional[QPainterPath]:
        coords = list(linestring.coords)
        if len(coords) < 2:
            return None
        first_x, first_y = coords[0][0], coords[0][1]
        path = QPainterPath(self._map_point(first_x, first_y))
        for coord in coords[1:]:
            x, y = coord[0], coord[1]
            path.lineTo(self._map_point(x, y))
        return path

    def _map_point(self, x: float, y: float) -> QPointF:
        return QPointF(x, -y)

    def _coerce_color(self, color: Optional[QColor]) -> QColor:
        if color is not None:
            return QColor(color)
        return self._next_color()

    def _next_color(self) -> QColor:
        if not self.DEFAULT_COLORS:
            return QColor(Qt.darkCyan)
        value = self.DEFAULT_COLORS[self._color_index % len(self.DEFAULT_COLORS)]
        self._color_index += 1
        return QColor(value)

    # ------------------------------------------------------------------
    # Interaction helpers
    # ------------------------------------------------------------------
    def zoom_in(self) -> None:
        self._apply_zoom(self._zoom_step)

    def zoom_out(self) -> None:
        self._apply_zoom(1.0 / self._zoom_step)

    def _apply_zoom(self, factor: float) -> None:
        if not self._layers:
            return
        current_scale = self.transform().m11()
        new_scale = current_scale * factor
        min_scale, max_scale = self._zoom_limits
        if new_scale < min_scale or new_scale > max_scale:
            return
        self.scale(factor, factor)

    # ------------------------------------------------------------------
    # Overlay configuration API
    # ------------------------------------------------------------------
    def set_scale_bar_visible(self, visible: bool) -> None:
        self._show_scale_bar = visible
        self.viewport().update()

    def scale_bar_visible(self) -> bool:
        return self._show_scale_bar

    def set_scale_bar_parameters(self, length: float, units: str) -> None:
        if length > 0:
            self._scale_bar_length = length
        self._scale_bar_units = units or self._scale_bar_units
        self.viewport().update()

    def scale_bar_parameters(self) -> Tuple[float, str]:
        return self._scale_bar_length, self._scale_bar_units

    def set_grid_visible(self, visible: bool) -> None:
        self._show_grid = visible
        self.viewport().update()

    def grid_visible(self) -> bool:
        return self._show_grid

    def set_grid_spacing(self, spacing: float) -> None:
        if spacing > 0:
            self._grid_spacing = spacing
        self.viewport().update()

    def grid_spacing(self) -> float:
        return self._grid_spacing

    # ------------------------------------------------------------------
    # Interaction overrides
    # ------------------------------------------------------------------
    def wheelEvent(self, event):  # type: ignore[override]
        if not self._layers:
            event.ignore()
            return
        delta = event.angleDelta().y()
        if delta == 0:
            event.ignore()
            return
        factor = self._zoom_step if delta > 0 else 1.0 / self._zoom_step
        current_scale = self.transform().m11()
        new_scale = current_scale * factor
        min_scale, max_scale = self._zoom_limits
        if new_scale < min_scale or new_scale > max_scale:
            event.accept()
            return
        self._apply_zoom(factor)
        event.accept()

    def mousePressEvent(self, event):  # type: ignore[override]
        if event.button() == Qt.LeftButton:
            self._is_panning = True
            self._pan_start = event.position()
            self.setCursor(QCursor(Qt.ClosedHandCursor))
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):  # type: ignore[override]
        if self._is_panning and self._pan_start is not None:
            delta = event.position() - self._pan_start
            self._pan_start = event.position()
            hbar = self.horizontalScrollBar()
            vbar = self.verticalScrollBar()
            if hbar.maximum() > 0 or vbar.maximum() > 0:
                hbar.setValue(hbar.value() - int(delta.x()))
                vbar.setValue(vbar.value() - int(delta.y()))
            else:
                self.translate(delta.x() * -1, delta.y() * -1)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):  # type: ignore[override]
        if event.button() == Qt.LeftButton and self._is_panning:
            self._is_panning = False
            self._pan_start = None
            self.setCursor(QCursor(Qt.OpenHandCursor))
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def drawForeground(self, painter: QPainter, rect: QRectF) -> None:  # type: ignore[override]
        super().drawForeground(painter, rect)
        if self._show_grid and self._grid_spacing > 0:
            self._draw_grid_scene(painter, rect)
        if self._show_scale_bar and self._scale_bar_length > 0:
            self._draw_scale_bar_view(painter)

    def _draw_grid_scene(self, painter: QPainter, rect: QRectF) -> None:
        spacing = self._grid_spacing
        if spacing <= 0:
            return
        painter.save()
        painter.setPen(self._grid_pen)
        left = min(rect.left(), rect.right())
        right = max(rect.left(), rect.right())
        bottom = min(rect.bottom(), rect.top())
        top = max(rect.bottom(), rect.top())

        if right - left > spacing * 10_000:
            painter.restore()
            return

        start_x = spacing * int(left // spacing)
        if start_x > left:
            start_x -= spacing
        x = start_x
        count = 0
        while x <= right and count < 2000:
            painter.drawLine(x, bottom, x, top)
            x += spacing
            count += 1

        start_y = spacing * int(bottom // spacing)
        if start_y > bottom:
            start_y -= spacing
        y = start_y
        count = 0
        while y <= top and count < 2000:
            painter.drawLine(left, y, right, y)
            y += spacing
            count += 1
        painter.restore()

    def _draw_scale_bar_view(self, painter: QPainter) -> None:
        scale = abs(self.transform().m11())
        if scale <= 0:
            return
        margin = 40
        bar_pixels = self._scale_bar_length * scale
        view_rect = self.viewport().rect()
        if bar_pixels > view_rect.width() * 0.5:
            bar_pixels = view_rect.width() * 0.5
        actual_units = bar_pixels / scale if scale else self._scale_bar_length

        painter.save()
        painter.resetTransform()
        painter.setRenderHint(QPainter.Antialiasing, True)
        y = view_rect.height() - margin
        x_start = margin
        x_end = x_start + bar_pixels
        painter.setPen(self._scale_pen)
        painter.drawLine(int(x_start), int(y), int(x_end), int(y))
        painter.drawLine(int(x_start), int(y - 5), int(x_start), int(y + 5))
        painter.drawLine(int(x_end), int(y - 5), int(x_end), int(y + 5))
        text = f"{actual_units:.2f} {self._scale_bar_units}"
        painter.setFont(self._font)
        painter.drawText(int(x_start), int(y - 8), text)
        painter.restore()

__all__ = ["NetworkCanvas", "CanvasLayer"]
