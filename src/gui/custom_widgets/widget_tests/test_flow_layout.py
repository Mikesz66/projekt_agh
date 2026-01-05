import sys
from PySide6.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget

from src.gui.custom_widgets.flow_widget import FlowScrollArea

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.resize(400, 500)
        
        # Main layout for the window
        main_layout = QVBoxLayout(self)

        # Create the ScrollArea with a fixed height of 200px
        self.scroll_area = FlowScrollArea(height=200)
        
        # Add a bunch of buttons
        for i in range(20):
            btn = QPushButton(f"Item {i}")
            # Use the proxy method directly on the scroll area
            self.scroll_area.addWidget(btn)

        # Add the scroll area to the main layout
        main_layout.addWidget(self.scroll_area)
        
        # Add a button to print current widgets
        debug_btn = QPushButton("Print Widgets")
        debug_btn.clicked.connect(self.print_items)
        main_layout.addWidget(debug_btn)

    def print_items(self):
        widgets = self.scroll_area.getWidgets()
        print(f"Found {len(widgets)} widgets inside the ScrollArea.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
