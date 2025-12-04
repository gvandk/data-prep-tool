from PyQt6.QtWidgets import QMainWindow, QFileDialog, QHBoxLayout, QWidget, QMenuBar, QLabel, QVBoxLayout, QLineEdit, QPushButton, QStackedLayout
from PyQt6.QtCore import pyqtSignal

class ColumnOrder(QHBoxLayout):
    column_reorder_request = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.uuid = None
        self.reorder_input = QLineEdit()
        self.addWidget(QLabel("Column Index:"))
        self.addWidget(self.reorder_input)

        self.reorder_input.textChanged.connect(self.on_text_edited)

    def set_current_index(self, uuid: str, index: str):
        self.index = uuid
        self.reorder_input.blockSignals(True)
        self.reorder_input.setText(index)
        self.reorder_input.blockSignals(False)
        self.reorder_input.setFocus()

    def on_text_edited(self, new_index):
        if self.uuid:
            self.column_reorder_request.emit(self.uuid, new_index)
