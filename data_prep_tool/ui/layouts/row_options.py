from PyQt6.QtWidgets import QHBoxLayout, QWidget, QLabel, QVBoxLayout, QPushButton
from PyQt6.QtCore import pyqtSignal

class RowPanel(QWidget):
    close_request = pyqtSignal()
    delete_row_requested = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_row = -1
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        header_layout = QHBoxLayout()
        self.label = QLabel("Row Options")
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

        self.row_index = QLabel("Row Index:")
        layout.addWidget(self.row_index)

        self.delete_btn = QPushButton("Delete Row")
        layout.addWidget(self.delete_btn)
        self.delete_btn.clicked.connect(self._on_delete)

        layout.addStretch()

    def set_row(self, row_index: int):
        self._current_row = row_index
        self.row_index.setText(f"Row Index: {row_index}")

    def _on_delete(self):
        if self._current_row != -1:
            self.delete_row_requested.emit(self._current_row)