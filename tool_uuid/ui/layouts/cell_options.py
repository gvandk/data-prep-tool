from PyQt6.QtWidgets import QHBoxLayout, QWidget, QLabel, QVBoxLayout, QPushButton
from PyQt6.QtCore import pyqtSignal
from .column_rename import ColumnRename
from .cell_edit import CellEdit

class CellPanel(QWidget):
    column_rename_request = pyqtSignal(str, str)
    close_request = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout()
        self.setLayout(layout)
        
        header_layout = QHBoxLayout()
        self.label = QLabel("Cell Options")
        font = self.label.font()
        font.setBold(True)
        self.label.setFont(font)
        
        self.close_btn = QPushButton("X")
        self.close_btn.setFixedSize(24, 24)
        self.close_btn.clicked.connect(self.close_request.emit)
        
        header_layout.addWidget(self.label)
        header_layout.addStretch()
        header_layout.addWidget(self.close_btn)
        layout.addLayout(header_layout)
        
        self.column_rename = ColumnRename()
        layout.addLayout(self.column_rename)
        self.cell_edit = CellEdit()
        layout.addLayout(self.cell_edit)

        layout.addStretch()

        self.column_rename.column_rename_request.connect(self.column_rename_request.emit)