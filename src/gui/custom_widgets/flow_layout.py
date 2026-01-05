import sys
from typing import List, Optional
from PySide6.QtWidgets import (QApplication, QWidget, QLayout, QLayoutItem,
                               QSizePolicy, QScrollArea, QStyle, QPushButton, QVBoxLayout)
from PySide6.QtCore import Qt, QRect, QSize, QPoint
class FlowLayout(QLayout):
    def __init__(self, parent: Optional[QWidget] = None, margin: int = 0, h_spacing: int = -1, v_spacing: int = -1):
        super().__init__(parent)
        self._item_list: List[QLayoutItem] = []
        self._h_space = h_spacing
        self._v_space = v_spacing
        self.setContentsMargins(margin, margin, margin, margin)

    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item: QLayoutItem):
        self._item_list.append(item)

    def count(self) -> int:
        return len(self._item_list)

    def itemAt(self, index: int) -> Optional[QLayoutItem]:
        if 0 <= index < len(self._item_list):
            return self._item_list[index]
        return None

    def takeAt(self, index: int) -> Optional[QLayoutItem]:
        if 0 <= index < len(self._item_list):
            return self._item_list.pop(index)
        return None

    def expandingDirections(self) -> Qt.Orientation:
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return self._do_layout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect: QRect):
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self) -> QSize:
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        size = QSize()
        for item in self._item_list:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def getWidgets(self) -> List[QWidget]:
        widgets = []
        for item in self._item_list:
            widget = item.widget()
            if widget:
                widgets.append(widget)
        return widgets

    def horizontalSpacing(self) -> int:
        if self._h_space >= 0: return self._h_space
        return self.smartSpacing(QStyle.PM_LayoutHorizontalSpacing)

    def verticalSpacing(self) -> int:
        if self._v_space >= 0: return self._v_space
        return self.smartSpacing(QStyle.PM_LayoutVerticalSpacing)

    def smartSpacing(self, pm: QStyle.PixelMetric) -> int:
        parent = self.parent()
        if not parent: return -1
        if parent.isWidgetType():
            return parent.style().pixelMetric(pm, None, parent)
        return QApplication.style().pixelMetric(pm, None, None)

    def _do_layout(self, rect: QRect, test_only: bool) -> int:
        left, top, right, bottom = self.getContentsMargins()
        effective_rect = rect.adjusted(+left, +top, -right, -bottom)
        x = effective_rect.x()
        y = effective_rect.y()
        line_height = 0
        spacing_x = self.horizontalSpacing()
        spacing_y = self.verticalSpacing()
        if spacing_x == -1: spacing_x = 10
        if spacing_y == -1: spacing_y = 10

        for item in self._item_list:
            next_x = x + item.sizeHint().width() + spacing_x
            if next_x - spacing_x > effective_rect.right() and line_height > 0:
                x = effective_rect.x()
                y = y + line_height + spacing_y
                next_x = x + item.sizeHint().width() + spacing_x
                line_height = 0
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))
            x = next_x
            line_height = max(line_height, item.sizeHint().height())
        return y + line_height - rect.y() + top + bottom
class FlowScrollArea(QScrollArea):
    """
    A QScrollArea that automatically contains a widget with a FlowLayout.
    It proxies the FlowLayout API methods.
    """
    def __init__(self, height: Optional[int] = 50, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._container = QWidget()
        self._container.setObjectName("flowContainer")
        self._flow_layout = FlowLayout(self._container)
        self.setWidget(self._container)
        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.NoFrame)
        if height is not None:
            self.setFixedHeight(height)

        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self.updateGeometry()

    def addWidget(self, widget: QWidget):
        """Adds a widget to the internal FlowLayout."""
        self._flow_layout.addWidget(widget)

    def getWidgets(self) -> List[QWidget]:
        """Returns the list of widgets in the internal FlowLayout."""
        return self._flow_layout.getWidgets()

    def removeWidget(self, widget: QWidget):
        """Removes a widget from the internal layout."""
        self._flow_layout.removeWidget(widget)
        widget.deleteLater()

    def clear(self):
        """Removes all widgets."""
        item = self._flow_layout.takeAt(0)
        while item:
            if item.widget():
                item.widget().deleteLater()
            item = self._flow_layout.takeAt(0)

    def setSpacing(self, h_spacing: int, v_spacing: int):
        """Sets horizontal and vertical spacing."""
        self._flow_layout._h_space = h_spacing
        self._flow_layout._v_space = v_spacing
        self._flow_layout.update()

    def setContentsMargins(self, left: int, top: int, right: int, bottom: int):
        """Sets margins on the INTERNAL layout, not the scroll area frame."""
        self._flow_layout.setContentsMargins(left, top, right, bottom)

    def sizeHint(self) -> QSize:
        """Tell the parent layout (left_menu) to respect the inner content height."""
        inner_size = self._container.sizeHint()
        height = inner_size.height() + self.frameWidth() * 2
        return QSize(super().sizeHint().width(), height)
