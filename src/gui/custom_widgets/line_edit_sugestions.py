import sys
import os
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLineEdit, QLabel, QListWidget, QPushButton
from PySide6.QtCore import Qt, QEvent, QPoint

# Import the core logic (assuming it is saved as trie_core.py)
from src.utils.reverse_index_trie import TrieManager
from paths import CACHE_PATH, SEACRCH_CSV

CSV_PATH = SEACRCH_CSV
JSON_PATH = os.path.join(CACHE_PATH, 'ingredients_trie.json')

class FloatingList(QListWidget):
    """
    A custom list widget that floats, auto-scales height, 
    and scrolls if content exceeds MAX_HEIGHT.
    """
    MAX_HEIGHT = 200  # Max pixel height before scrollbar appears

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setStyleSheet("""
            QListWidget {
                background-color: white;
                border: 1px solid #ccc;
                font-size: 14px;
            }
            QListWidget::item {
                padding: 5px;
            }
            QListWidget::item:selected {
                background-color: #0078d7;
                color: white;
            }
        """)
        # Ensure the list is always on top of other widgets in the same window
        self.setWindowFlag(Qt.WindowType.ToolTip) 
        # Note: ToolTip flag makes it float over everything but can sometimes steal focus 
        # depending on OS. Alternatively, just parenting to the Window and raise_() works 
        # for MDI/Single window apps. 
        # For this implementation, standard parenting + raise_() is safer for focus.
        self.setWindowFlags(Qt.WindowType.SubWindow | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        
        self.hide()

    def update_items(self, items):
        self.clear()
        if not items:
            self.hide()
            return

        self.addItems(items)
        
        row_height = 30  
        total_content_height = len(items) * row_height + 5 
        final_height = min(total_content_height, self.MAX_HEIGHT)
        
        self.setFixedHeight(final_height)
        self.show()
        self.raise_()

class LineEditSuggestions(QWidget):
    """
    A universal controller that attaches a FloatingList to ANY QLineEdit
    and handles geometry tracking, searching, and selection automatically.
    """
    def __init__(self, line_edit_object: QLineEdit, trie_manager_object: TrieManager) -> None:
        # We initialize this widget as a child of the line_edit so it stays alive with it
        super().__init__(line_edit_object)
        
        self.target = line_edit_object
        self.manager = trie_manager_object
        
        # Determine the top-level window so the list can float over siblings
        parent_window = self.target.window()
        
        # Initialize the floating list, parented to the main window
        self.suggestion_list = FloatingList(parent_window)
        
        # Connect Signals
        self.target.textChanged.connect(self.on_text_changed)
        self.suggestion_list.itemClicked.connect(self.on_item_clicked)
        
        # Install Event Filter to track resizing/moving of the target input
        self.target.installEventFilter(self)

    def eventFilter(self, obj, event):
        """
        Monitors the target LineEdit. If it moves, resizes, or hides,
        we adjust the floating list accordingly.
        """
        if obj == self.target:
            if event.type() in (QEvent.Type.Resize, QEvent.Type.Move):
                # Update position if list is visible
                if not self.suggestion_list.isHidden():
                    self.update_list_geometry()
            elif event.type() == QEvent.Type.Hide:
                self.suggestion_list.hide()
                
        return super().eventFilter(obj, event)

    def on_text_changed(self, text):
        suggestions = self.manager.search(text)
        self.suggestion_list.update_items(suggestions)
        
        if not self.suggestion_list.isHidden():
            self.update_list_geometry()

    def update_list_geometry(self):
        """
        Calculates where the list should be relative to the input field
        regardless of where the input field is in the layout hierarchy.
        """
        # 1. Get the geometry of the input field
        rect = self.target.rect()
        
        # 2. Map the bottom-left corner of the input to Global Screen Coordinates
        bottom_left_global = self.target.mapToGlobal(rect.bottomLeft())
        
        # 3. Map Global Coordinates back to the Suggestion List's Parent (The Window)
        # This ensures it works even if the LineEdit is deeply nested in layouts
        target_pos = self.suggestion_list.parent().mapFromGlobal(bottom_left_global)
        
        # 4. Apply geometry
        self.suggestion_list.setGeometry(
            target_pos.x(), 
            target_pos.y(), 
            self.target.width(), 
            self.suggestion_list.height()
        )

    def on_item_clicked(self, item):
        self.target.setText(item.text())
        self.suggestion_list.hide()


class MainWindow(QWidget):
    def __init__(self, manager):
        super().__init__()
        self.manager = manager
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Universal Trie Autocomplete")
        self.setGeometry(100, 100, 400, 300)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        # 1. The Input Field
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Type 'beef'...")
        layout.addWidget(self.input_field)

        # --- ATTACH THE UNIVERSAL SUGGESTER ---
        # This is now the only line needed to add functionality to the input
        self.suggester = LineEditSuggestions(self.input_field, self.manager)
        # --------------------------------------

        # 2. Proof of overlay
        self.other_label = QLabel("I am a widget underneath.\nThe list should float over me.")
        self.other_label.setStyleSheet("background-color: lightgray; padding: 20px;")
        self.other_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.other_label)
        
        layout.addWidget(QPushButton("Useless Button"))
        layout.addStretch() 
        self.setLayout(layout)

        # Note: We no longer need resizeEvent or manual slot connections in MainWindow

if __name__ == "__main__":
    
    # Initialize Core
    # Ensure you have trie_core.py or similar available
    try:
        trie_manager = TrieManager(
            source_csv=CSV_PATH, 
            output_json=JSON_PATH, 
            id_col='id', 
            data_col='ingredients_serialized',
            separator=';'
        )
    except Exception as e:
        print(f"Error loading TrieManager: {e}")
        print("Mocking TrieManager for GUI demonstration...")
        class MockManager:
            def search(self, text):
                if not text: return []
                dummy_data = ["beef", "beef jerky", "beef wellington", "beer", "beetroot", "bell pepper"]
                return [w for w in dummy_data if w.startswith(text.lower())]
        trie_manager = MockManager()

    app = QApplication(sys.argv)
    window = MainWindow(trie_manager)
    window.show()
    sys.exit(app.exec())
