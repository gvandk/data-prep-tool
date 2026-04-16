from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget


class ColumnFilter(QWidget):
    """UI controls for removing rows by a specific column value."""

    filter_value_request = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._uuid = None

        layout = QVBoxLayout(self)
        self.header_label = QLabel("Filter Rows by Value:")
        layout.addWidget(self.header_label)

        controls = QHBoxLayout()
        self.value_input = QLineEdit()
        self.value_input.setPlaceholderText("Value to remove")
        controls.addWidget(self.value_input)

        self.filter_button = QPushButton("Filter Out Value")
        self.filter_button.clicked.connect(self._on_filter_clicked)
        controls.addWidget(self.filter_button)

        layout.addLayout(controls)

    def set_current_column(self, uuid: str, column_name: str):
        self._uuid = uuid
        self.header_label.setText(f"Filter Rows by Value ({column_name}):")
        self.value_input.clear()

    def _on_filter_clicked(self):
        if not self._uuid:
            return
        self.filter_value_request.emit(self._uuid, self.value_input.text())
