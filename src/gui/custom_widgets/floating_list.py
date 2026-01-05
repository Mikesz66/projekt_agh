from PySide6.QtGui import Qt
from PySide6.QtWidgets import QListWidget

class FloatingList(QListWidget):
    """
    A custom list widget that floats, auto-scales height,
    and scrolls if content exceeds MAX_HEIGHT.
    """
    MAX_HEIGHT = 200

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.hide()

    def update_items(self, items: list[str]):
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
