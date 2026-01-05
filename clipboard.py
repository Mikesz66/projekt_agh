import sys
import pprint
import json
import os
import time
from typing import List, Optional

# --- Watchdog Imports ---
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from PySide6.QtCore import Qt, QRect, QSize, QPoint, QTimer, Signal, QObject
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLayout,
    QLayoutItem,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStyle,
    QVBoxLayout,
    QWidget,
)

# --- Mocking paths.py for this standalone example ---
# In your real code, remove this block and use: from paths import RECIPES_FOUND
RECIPES_FOUND = "recipes_found.json"
# Ensure the file exists for the observer to start correctly
if not os.path.exists(RECIPES_FOUND):
    with open(RECIPES_FOUND, "w") as f:
        json.dump([], f)

# --- Layout Classes (FlowLayout & FlowScrollArea) ---
# (Kept identical to your original code, collapsed for brevity)
class FlowLayout(QLayout):
    def __init__(self, parent: Optional[QWidget] = None, margin: int = 0, h_spacing: int = -1, v_spacing: int = -1):
        super().__init__(parent)
        self._item_list: List[QLayoutItem] = []
        self._h_space = h_spacing
        self._v_space = v_spacing
        self.setContentsMargins(margin, margin, margin, margin)
    def __del__(self):
        item = self.takeAt(0)
        while item: item = self.takeAt(0)
    def addItem(self, item: QLayoutItem): self._item_list.append(item)
    def count(self) -> int: return len(self._item_list)
    def itemAt(self, index: int) -> Optional[QLayoutItem]:
        if 0 <= index < len(self._item_list): return self._item_list[index]
        return None
    def takeAt(self, index: int) -> Optional[QLayoutItem]:
        if 0 <= index < len(self._item_list): return self._item_list.pop(index)
        return None
    def expandingDirections(self) -> Qt.Orientation: return Qt.Orientation(0)
    def hasHeightForWidth(self) -> bool: return True
    def heightForWidth(self, width: int) -> int: return self._do_layout(QRect(0, 0, width, 0), True)
    def setGeometry(self, rect: QRect):
        super().setGeometry(rect)
        self._do_layout(rect, False)
    def sizeHint(self) -> QSize: return self.minimumSize()
    def minimumSize(self) -> QSize:
        size = QSize()
        for item in self._item_list: size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size
    def getWidgets(self) -> List[QWidget]:
        widgets = []
        for item in self._item_list:
            if item.widget(): widgets.append(item.widget())
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
        if parent.isWidgetType(): return parent.style().pixelMetric(pm, None, parent)
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
            if not test_only: item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))
            x = next_x
            line_height = max(line_height, item.sizeHint().height())
        return y + line_height - rect.y() + top + bottom

class FlowScrollArea(QScrollArea):
    def __init__(self, height: Optional[int] = 50, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._container = QWidget()
        self._container.setObjectName("flowContainer")
        self._flow_layout = FlowLayout(self._container)
        self.setWidget(self._container)
        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.NoFrame)
        if height is not None: self.setFixedHeight(height)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self.updateGeometry()
    def addWidget(self, widget: QWidget): self._flow_layout.addWidget(widget)
    def getWidgets(self) -> List[QWidget]: return self._flow_layout.getWidgets()
    def removeWidget(self, widget: QWidget):
        self._flow_layout.removeWidget(widget)
        widget.deleteLater()
    def clear(self):
        item = self._flow_layout.takeAt(0)
        while item:
            if item.widget(): item.widget().deleteLater()
            item = self._flow_layout.takeAt(0)
    def setSpacing(self, h_spacing: int, v_spacing: int):
        self._flow_layout._h_space = h_spacing
        self._flow_layout._v_space = v_spacing
        self._flow_layout.update()
    def setContentsMargins(self, left: int, top: int, right: int, bottom: int):
        self._flow_layout.setContentsMargins(left, top, right, bottom)
    def sizeHint(self) -> QSize:
        inner_size = self._container.sizeHint()
        height = inner_size.height() + self.frameWidth() * 2
        return QSize(super().sizeHint().width(), height)

# --- Storage Class ---
class Storage:
    def __init__(self) -> None:
        self._subscribers: list[tuple[str, object]] = []

    def add(self, key_name:str, object_instance:object):
        new_entry: tuple[str, object] = (key_name, object_instance)
        self._subscribers.append(new_entry)

    def _objects_to_dict(self) -> dict[str, str | list[str]]:
        def _object_to_data(object_instance: object) -> str | list[str]:
            if hasattr(object_instance, "text"):
                return object_instance.text() # type: ignore
            match object_instance:
                case str(): return object_instance
                case int(): return str(object_instance)
                case FlowScrollArea():
                    items = []
                    widgets = object_instance.getWidgets()
                    for widget in widgets:
                        item = _object_to_data(widget)
                        if not item or item == "": continue
                        items.append(item)
                    return items
                case _: return ""

        output:dict[str, str | list[str]] = {}
        for pair in self._subscribers:
            key_name, object_instance = pair
            widget_contents = _object_to_data(object_instance)
            if not widget_contents or widget_contents == "" or widget_contents == []: continue
            output[key_name] = widget_contents
        return output

    def get_data(self) -> dict[str, str | list[str]]:
        return self._objects_to_dict()

storage = Storage()

# --- Watchdog Logic ---

class WatchdogSignaler(QObject):
    """
    Bridge class to emit Qt signals from the Watchdog thread.
    We need this because Watchdog runs in a separate thread,
    but we want to modify UI elements which requires the Main Thread.
    """
    file_changed = Signal()

class RecipeFileHandler(FileSystemEventHandler):
    """
    Handles file system events from Watchdog.
    """
    def __init__(self, target_file, signaler):
        self.target_file = os.path.abspath(target_file)
        self.signaler = signaler

    def on_modified(self, event):
        # We only care if the specific file was modified
        if os.path.abspath(event.src_path) == self.target_file:
            self.signaler.file_changed.emit()

# --- Main Window ---

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyQt6 + Watchdog Example")
        self.setGeometry(100, 100, 800, 500)
        self.setObjectName("mainWindow")

        # 1. Setup UI
        self._ui()

        # 2. Setup Debounce Timer (to handle nvim double-writes)
        self.debounce_timer = QTimer()
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.setInterval(200) # 200ms debounce
        self.debounce_timer.timeout.connect(self._reload_recipes_from_file)

        # 3. Setup Watchdog
        self._setup_file_watcher()

    def _setup_file_watcher(self):
        """Starts the background thread to monitor RECIPES_FOUND"""
        self.signaler = WatchdogSignaler()
        # When file changes, just start/restart the timer (debouncing)
        self.signaler.file_changed.connect(self.debounce_timer.start)

        self.observer = Observer()
        # Monitor the directory containing the file
        directory = os.path.dirname(os.path.abspath(RECIPES_FOUND))
        if not directory: directory = "."
        
        event_handler = RecipeFileHandler(RECIPES_FOUND, self.signaler)
        self.observer.schedule(event_handler, directory, recursive=False)
        self.observer.start()

    def closeEvent(self, event):
        """Clean up the observer on app exit"""
        if self.observer:
            self.observer.stop()
            self.observer.join()
        event.accept()

    def _ui(self):
        layout = QHBoxLayout()

        # Left
        left_menu = QVBoxLayout()
        search_button = QPushButton("Manual Reload (Search)")
        search_button.clicked.connect(self.on_search_press)
        left_menu.addWidget(self._ui_app_title())
        left_menu.addWidget(self._ui_scrollable_menu())
        left_menu.addWidget(search_button)

        # Right
        right_decoration = QWidget()
        self.right_menu_layout = QVBoxLayout(right_decoration)
        self.right_menu_layout.addStretch()

        # Center
        layout.addLayout(left_menu)
        layout.addWidget(right_decoration)
        layout.setStretch(0, 1)
        layout.setStretch(1, 2)
        
        self.setLayout(layout)

    def _ui_app_title(self) -> QWidget:
        app_title_widget = QWidget()
        app_title = QVBoxLayout(app_title_widget)
        app_title.addWidget(QLabel("Wyszukiwarka"))
        app_title.addWidget(QLabel("Przepisów"))
        app_title_widget.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        return app_title_widget

    def _ui_scrollable_menu(self) -> QScrollArea:
        content_widget = QWidget()
        filter_menu = QVBoxLayout(content_widget)
        filter_menu.addWidget(self._ui_recipe_name())
        filter_menu.addWidget(self._ui_liked_box())
        filter_menu.addWidget(self._ui_disliked_box())
        filter_menu.addStretch()
        scrollable_menu = QScrollArea()
        scrollable_menu.setWidget(content_widget)
        scrollable_menu.setWidgetResizable(True)
        return scrollable_menu

    def _ui_recipe_name(self) -> QWidget:
        output_widget = QWidget()
        layout = QVBoxLayout(output_widget)
        label = QLabel("Nazwa Przepisu")
        line_edit = QLineEdit()
        storage.add("recipe_name",line_edit)
        layout.addWidget(label)
        layout.addWidget(line_edit)
        return output_widget

    def _ui_liked_box(self) -> QWidget:
        output_widget = QWidget()
        layout = QVBoxLayout(output_widget)
        label = QLabel("Składniki Lubiane")
        line_edit = QLineEdit()
        flexbox = FlowScrollArea()
        storage.add("liked_recipes",flexbox)
        layout.addWidget(label)
        layout.addWidget(line_edit)
        layout.addWidget(flexbox)
        return output_widget

    def _ui_disliked_box(self) -> QWidget:
        output_widget = QWidget()
        layout = QVBoxLayout(output_widget)
        label = QLabel("Składniki Nielubiane")
        line_edit = QLineEdit()
        flexbox = FlowScrollArea()
        storage.add("disiked_recipes",flexbox)
        layout.addWidget(label)
        layout.addWidget(line_edit)
        layout.addWidget(flexbox)
        return output_widget

    def on_search_press(self):
        """Manual trigger (optional)"""
        pprint.pprint(storage.get_data())
        self._reload_recipes_from_file()

    def _reload_recipes_from_file(self):
        """
        Reads the JSON file and updates the right menu.
        This is called after the debounce timer finishes.
        """
        print(f"Loading data from {RECIPES_FOUND}...")
        
        try:
            with open(RECIPES_FOUND, "r") as f:
                # Handle empty file race condition if caught mid-write
                content = f.read()
                if not content:
                    return
                data = json.loads(content)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"Error reading file: {e}")
            return

        # Clear existing widgets
        while self.right_menu_layout.count():
            item = self.right_menu_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        # Generate new widgets
        if isinstance(data, list):
            for recipe in data:
                widget = self._create_result_widget(recipe)
                self.right_menu_layout.addWidget(widget)
        
        self.right_menu_layout.addStretch()

    def _create_result_widget(self, data: dict) -> QWidget:
        card = QWidget()
        card.setObjectName("resultCard")
        card.setStyleSheet("""
            QWidget#resultCard {
                background-color: #f0f0f0; 
                border: 1px solid #c0c0c0; 
                border-radius: 8px;
            }
            QLabel { font-size: 14px; }
        """)
        layout = QVBoxLayout(card)
        r_id = data.get("id", "Unknown")
        acc_raw = data.get("accuracy", 0.0)
        acc_percent = f"{acc_raw * 100:.1f}%"

        id_label = QLabel(f"<b>Recipe ID:</b> {r_id}")
        acc_label = QLabel(f"Match: {acc_percent}")
        
        if acc_raw > 0.9:
            acc_label.setStyleSheet("color: green; font-weight: bold;")
        elif acc_raw > 0.6:
            acc_label.setStyleSheet("color: orange;")
        else:
            acc_label.setStyleSheet("color: red;")

        layout.addWidget(id_label)
        layout.addWidget(acc_label)
        return card

def get_stylesheet() -> str:
    # (Simplified for example)
    return ""

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
