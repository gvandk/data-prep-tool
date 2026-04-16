from PyQt6.QtWidgets import QHBoxLayout, QWidget, QLabel, QVBoxLayout, QPushButton
from PyQt6.QtCore import pyqtSignal

class RowPanel(QWidget):
    close_request = pyqtSignal()
    delete_row_requested = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_row = -1
        self._current_rows = []
        
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

        self.row_index = QLabel("Selected rows:")
        layout.addWidget(self.row_index)

        self.delete_btn = QPushButton("Delete Selected Rows")
        layout.addWidget(self.delete_btn)
        self.delete_btn.clicked.connect(self._on_delete)
        self.delete_btn.setEnabled(False)

        layout.addStretch()

        self.set_rows([])

    def set_row(self, row_index: int):
        self.set_rows([row_index])

    def set_rows(self, row_indices: list[int]):
        cleaned = sorted(set(int(index) for index in row_indices if index is not None))
        self._current_rows = cleaned

        if not cleaned:
            self._current_row = -1
            self.row_index.setText("Selected rows: none")
            self.delete_btn.setText("Delete Selected Rows")
            self.delete_btn.setEnabled(False)
            return

        self._current_row = cleaned[0]
        rows_text = ", ".join(str(index) for index in cleaned)
        self.row_index.setText(f"Selected rows ({len(cleaned)}): {rows_text}")
        self.delete_btn.setText(f"Delete Selected Rows ({len(cleaned)})")
        self.delete_btn.setEnabled(True)

    def _on_delete(self):
        if self._current_rows:
            self.delete_row_requested.emit(list(self._current_rows))