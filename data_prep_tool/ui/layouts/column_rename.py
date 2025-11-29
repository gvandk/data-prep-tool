from PyQt6.QtWidgets import QMainWindow, QFileDialog, QHBoxLayout, QWidget, QMenuBar, QLabel, QVBoxLayout, QLineEdit, QPushButton, QStackedLayout
from PyQt6.QtCore import pyqtSignal

class ColumnRename(QHBoxLayout):
    column_rename_request = pyqtSignal(int, str)

    def __init__(self, parent=None):
        super().__init__(parent)

        
        self.index = -1

        self.rename_input = QLineEdit()
        self.addWidget(QLabel("Column Name:"))
        self.addWidget(self.rename_input)

        self.rename_input.textChanged.connect(self.on_text_edited)

    def set_current_column(self, index, name):
        self.index = index
        self.rename_input.blockSignals(True)
        self.rename_input.setText(name)
        self.rename_input.blockSignals(False)

    def on_text_edited(self, new_text):
        if self.index != -1:
            self.column_rename_request.emit(self.index, new_text)
