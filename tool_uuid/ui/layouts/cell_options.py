from PyQt6.QtWidgets import QMainWindow, QFileDialog, QHBoxLayout, QWidget, QMenuBar, QLabel, QVBoxLayout, QLineEdit, QPushButton, QStackedLayout
from PyQt6.QtCore import pyqtSignal
from .column_rename import ColumnRename
from .cell_edit import CellEdit

class CellPanel(QWidget):
    column_rename_request = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout()
        self.setLayout(layout)
        self.label=QLabel("Cell Options")
        layout.addWidget(self.label)
        self.column_rename=ColumnRename()
        layout.addLayout(self.column_rename)
        self.cell_edit=CellEdit()
        layout.addLayout(self.cell_edit)


        layout.addStretch()

        self.column_rename.column_rename_request.connect(self.column_rename_request.emit)