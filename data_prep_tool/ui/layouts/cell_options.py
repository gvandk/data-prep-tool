from PyQt6.QtWidgets import QMainWindow, QFileDialog, QHBoxLayout, QWidget, QMenuBar, QLabel, QVBoxLayout, QLineEdit, QPushButton, QStackedLayout
from PyQt6.QtCore import pyqtSignal
from .column_rename import ColumnRename

class CellPanel(QWidget):
    column_rename_request = pyqtSignal(int, str)

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout()
        self.setLayout(layout)
        self.label=QLabel("Cell Options")
        layout.addWidget(self.label)
        self.column_rename=ColumnRename()
        layout.addLayout(self.column_rename)

        layout.addStretch()

        self.column_rename.column_rename_request.connect(self.column_rename_request.emit)