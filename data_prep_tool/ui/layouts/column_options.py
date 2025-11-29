from PyQt6.QtWidgets import QMainWindow, QFileDialog, QHBoxLayout, QWidget, QMenuBar, QLabel, QVBoxLayout, QLineEdit, QPushButton, QStackedLayout
from PyQt6.QtCore import pyqtSignal
from .column_rename import ColumnRename
from .column_encoding import ColumnEncoding

class ColumnPanel(QWidget):
    column_rename_request = pyqtSignal(int, str)
    column_encoding_request = pyqtSignal(int, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout()
        self.setLayout(layout)
        self.label=QLabel("Column Options")
        layout.addWidget(self.label)

        self.column_rename=ColumnRename()
        layout.addLayout(self.column_rename)

        self.encoder_options=ColumnEncoding()
        layout.addLayout(self.encoder_options)

        layout.addStretch()

        self.column_rename.column_rename_request.connect(self.column_rename_request.emit)
        self.encoder_options.column_encoding_request.connect(self.column_encoding_request.emit)