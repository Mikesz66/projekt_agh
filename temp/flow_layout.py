from __future__ import annotations

from typing import List, Optional, Tuple

from PyQt6.QtCore import Qt, QPoint, QRect, QSize, QEvent, QObject
from PyQt6.QtWidgets import (
    QWidget,
    QLayout,
    QScrollArea,
    QFrame,
    QLayoutItem,
    QSizePolicy,
)
from PyQt6.QtGui import QPainter, QPen, QColor, QPaintEvent


class FlowLayout(QLayout):
    """
    A custom QLayout that arranges child widgets from left to right, wrapping to
    new lines when necessary.

    Features:
    - Independent line heights (calculated based on tallest item in line).
    - 'base_point' property support for custom vertical alignment within lines.
    - 'force_new_line' property support to explicitly break lines.
    - Optional grid snapping for line baselines.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._item_list: List[QLayoutItem] = []
        self._line_debug_positions: List[Tuple[int, int]] = []

        self.grid_enabled: bool = False
        self.grid_size: int = 20
        self.grid_offset: int = 0
        self.show_debug_lines: bool = False

        self.setSpacing(10)

    def __del__(self) -> None:
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item: QLayoutItem) -> None:  # type: ignore[override]
        """Internal method called by addWidget(). Adds a QLayoutItem to the list."""
        self._item_list.append(item)

    def count(self) -> int:  # type: ignore[override]
        """Returns the number of items in the layout."""
        return len(self._item_list)

    def itemAt(self, index: int) -> Optional[QLayoutItem]:  # type: ignore[override]
        """Returns the item at the given index, or None if index is out of bounds."""
        if 0 <= index < len(self._item_list):
            return self._item_list[index]
        return None

    def takeAt(self, index: int) -> Optional[QLayoutItem]:  # type: ignore[override]
        """Removes and returns the item at the given index."""
        if 0 <= index < len(self._item_list):
            return self._item_list.pop(index)
        return None

    def expandingDirections(self) -> Qt.Orientation:  # type: ignore[override]
        """Defines the layout's expansion policy (Horizontal only)."""
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:  # type: ignore[override]
        """Indicates that this layout's height depends on its width."""
        return True

    def heightForWidth(self, width: int) -> int:  # type: ignore[override]
        """Calculates the required height for the given width."""
        return self._do_layout(QRect(0, 0, width, 0), apply_geometry=False)

    def setGeometry(self, rect: QRect) -> None:  # type: ignore[override]
        """Applies the layout to the given geometry, positioning all children."""
        super().setGeometry(rect)
        self._do_layout(rect, apply_geometry=True)

    def sizeHint(self) -> QSize:  # type: ignore[override]
        """Returns the preferred size of the layout."""
        return self.minimumSize()

    def minimumSize(self) -> QSize:  # type: ignore[override]
        """Returns the minimum size required by the layout (based on largest child)."""
        size = QSize()
        for item in self._item_list:
            size = size.expandedTo(item.minimumSize())
        return size

    def paint_debug_visuals(self, painter: QPainter) -> None:
        """
        Draws debug lines indicating the calculated baseline for every row.
        Called by the container widget's paintEvent.
        """
        if not self.show_debug_lines:
            return

        pen = QPen(QColor(255, 0, 0, 180))
        pen.setWidth(1)
        pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)

        for y_pos, line_width in self._line_debug_positions:
            painter.drawLine(0, y_pos, line_width, y_pos)

    def _get_alignment_point(self, item: QLayoutItem, item_height: int) -> int:
        """
        Determines the Y-offset (from top) to align the widget to.
        Checks for 'base_point' property; defaults to center.
        """
        widget = item.widget()
        if widget:
            base_point = widget.property("base_point")
            if base_point is not None and isinstance(base_point, int):
                return base_point
        return item_height // 2

    def _do_layout(self, rect: QRect, apply_geometry: bool = False) -> int:
        """
        The core layout engine.
        Iterates through items, forming lines, calculating baselines, and positioning widgets.
        Returns the total height used.
        """
        x = rect.x()
        y = rect.y()
        effective_width = rect.width()
        spacing = self.spacing()

        if apply_geometry:
            self._line_debug_positions.clear()

        line_items: List[QLayoutItem] = []

        def process_line(
            current_items: List[QLayoutItem], current_y: int, is_dry_run: bool
        ) -> int:
            if not current_items:
                return current_y

            # 1. Calculate Line Metrics
            max_ascent = 0
            max_descent = 0

            for item in current_items:
                size = item.sizeHint()
                ascent = self._get_alignment_point(item, size.height())
                descent = size.height() - ascent
                max_ascent = max(max_ascent, ascent)
                max_descent = max(max_descent, descent)

            # 2. Determine Baseline
            candidate_baseline_y = current_y + max_ascent

            if self.grid_enabled and self.grid_size > 0:
                rel_y = candidate_baseline_y - self.grid_offset
                if rel_y < 0:
                    rel_y = 0
                grid_index = (rel_y + self.grid_size - 1) // self.grid_size
                snapped_y = (grid_index * self.grid_size) + self.grid_offset

                final_baseline_y = snapped_y
                # Ensure we don't snap upwards into previous content
                while (final_baseline_y - max_ascent) < current_y:
                    final_baseline_y += self.grid_size
            else:
                final_baseline_y = candidate_baseline_y

            # 3. Position Items or Store Debug Info
            if not is_dry_run:
                self._line_debug_positions.append((final_baseline_y, effective_width))

                current_x_cursor = rect.x()
                for item in current_items:
                    size = item.sizeHint()
                    item_ascent = self._get_alignment_point(item, size.height())
                    item_y = final_baseline_y - item_ascent
                    item.setGeometry(QRect(QPoint(current_x_cursor, item_y), size))
                    current_x_cursor += size.width() + spacing

            return (final_baseline_y + max_descent) + spacing

        # --- Main Loop ---
        current_x = 0
        current_y_cursor = y

        for item in self._item_list:
            size = item.sizeHint()
            widget = item.widget()

            force_new_line = False
            if widget:
                prop = widget.property("force_new_line")
                if isinstance(prop, bool):
                    force_new_line = prop

            next_x = current_x + size.width()

            # Check if we need to wrap
            if len(line_items) > 0 and (next_x > effective_width or force_new_line):
                current_y_cursor = process_line(
                    line_items, current_y_cursor, not apply_geometry
                )
                line_items = []
                current_x = 0
                next_x = size.width()

            line_items.append(item)
            current_x = next_x + spacing

        # Process the last line
        if line_items:
            current_y_cursor = process_line(
                line_items, current_y_cursor, not apply_geometry
            )

        return current_y_cursor - rect.y()


class _FlowWidget(QWidget):
    """Internal widget used by FlowContainer to support custom debug painting."""

    def paintEvent(self, event: QPaintEvent) -> None:  # type: ignore[override]
        super().paintEvent(event)
        layout = self.layout()
        if isinstance(layout, FlowLayout):
            painter = QPainter(self)
            layout.paint_debug_visuals(painter)


class FlowContainer(QScrollArea):
    """
    A QScrollArea wrapper that manages a FlowLayout.

    It automatically handles:
    - Min/Max height constraints.
    - Vertical Scrollbar visibility.
    - Dynamic resizing of content (expanding/shrinking).
    """

    def __init__(
        self,
        min_height: Optional[int] = None,
        max_height: Optional[int] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)

        self._min_height: Optional[int] = min_height
        self._max_height: Optional[int] = max_height

        self.content_widget = _FlowWidget()
        self.flow_layout = FlowLayout(self.content_widget)
        self.setWidget(self.content_widget)

        # Install Event Filter to detect child resize requests
        self.content_widget.installEventFilter(self)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setStyleSheet("QScrollArea { background: transparent; border: none; }")

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # type: ignore[override]
        """Intercepts LayoutRequest events to trigger automatic height adjustment."""
        if obj == self.content_widget and event.type() == QEvent.Type.LayoutRequest:
            self.adjust_height()
        return super().eventFilter(obj, event)

    def add_widget(self, widget: QWidget) -> None:
        """
        Adds a widget to the flow layout.
        The container will automatically resize to fit the new content.
        """
        self.flow_layout.addWidget(widget)
        # updateGeometry triggers a LayoutRequest, handled by eventFilter
        self.content_widget.updateGeometry()

    def remove_widget(self, widget: QWidget) -> None:
        """
        Removes a widget, deletes it, and immediately shrinks the container.
        """
        self.flow_layout.removeWidget(widget)
        widget.setParent(None)  # type: ignore
        widget.deleteLater()
        self.adjust_height()

    def set_grid(self, enabled: bool, size: int = 20) -> None:
        """
        Enables or disables grid snapping for line alignment.
        :param size: Distance between grid lines (pixels).
        """
        self.flow_layout.grid_enabled = enabled
        self.flow_layout.grid_size = size
        self.flow_layout.invalidate()
        self.content_widget.update()

    def set_debug(self, enabled: bool) -> None:
        """
        Toggles the display of red dashed lines indicating text baselines/alignment.
        """
        self.flow_layout.show_debug_lines = enabled
        self.content_widget.update()

    def resizeEvent(self, event: QEvent) -> None:  # type: ignore[override]
        """Handles resizing of the container itself (e.g. window resize)."""
        super().resizeEvent(event)  # type: ignore
        self.adjust_height()

    def adjust_height(self) -> None:
        """
        Calculates the required height for the content and updates the container's
        Fixed Height, respecting min/max constraints.
        """
        viewport = self.viewport()
        if viewport is None:
            return

        content_width = viewport.width()
        ideal_height = self.flow_layout.heightForWidth(content_width)

        actual_height = ideal_height
        if self.flow_layout.count() == 0:
            actual_height = 0
        else:
            if self._min_height is not None:
                actual_height = max(actual_height, self._min_height)
            if self._max_height is not None:
                actual_height = min(actual_height, self._max_height)

        if self.height() != actual_height:
            self.setFixedHeight(actual_height)
