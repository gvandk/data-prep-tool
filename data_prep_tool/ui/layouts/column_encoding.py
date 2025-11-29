from PyQt6.QtWidgets import QMainWindow, QFileDialog, QHBoxLayout, QWidget, QMenuBar, QLabel, QVBoxLayout, QLineEdit, QPushButton, QStackedLayout, QComboBox
from PyQt6.QtCore import pyqtSignal

class ColumnEncoding(QHBoxLayout):
    column_encoding_request = pyqtSignal(int, str)

    def __init__(self, parent=None):

        super().__init__(parent)

        self.index = -1
        self.column_encoding_state = {}

        self.encoding_input = QComboBox()
        self.encoding_input.addItems(["None", "One-Hot"])
        self.addWidget(QLabel("Encoding:"))
        self.addWidget(self.encoding_input)

        self.encoding_input.currentTextChanged.connect(self.on_encoding_changed)

    def set_current_column(self, index, encoding):
        self.index = index
        self.encoding_input.blockSignals(True)
        self.encoding_input.setCurrentText(encoding)
        self.encoding_input.blockSignals(False)

    def on_encoding_changed(self):
        if self.index != -1:
            self.column_encoding_state[self.index] = self.encoding_input.currentText()
            self.column_encoding_request.emit(self.index, self.encoding_input.currentText())

