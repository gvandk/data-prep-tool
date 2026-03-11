from PyQt6.QtWidgets import QMainWindow, QFileDialog, QHBoxLayout, QWidget, QMenuBar, QLabel, QVBoxLayout, QLineEdit, QPushButton, QStackedLayout
from PyQt6.QtCore import pyqtSignal

class CellEdit(QHBoxLayout):
    cell_change_request = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.uuid = None
        self.cell_input = QLineEdit()
        self.addWidget(QLabel("Cell Value:"))
        self.addWidget(self.cell_input)

        self.cell_input.textChanged.connect(self.on_cell_edited)

    def set_current_cell(self, uuid: str, value):
        self.uuid = uuid
        self.cell_input.blockSignals(True)
        self.cell_input.setText(value)
        self.cell_input.blockSignals(False)
        self.cell_input.setFocus()

    def on_cell_edited(self, new_value):
        if self.uuid:
            self.cell_change_request.emit(self.uuid, new_value)
