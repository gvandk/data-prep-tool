from PyQt6.QtWidgets import QHBoxLayout, QLabel, QLineEdit
from PyQt6.QtCore import pyqtSignal

class ColumnRename(QHBoxLayout):
    column_rename_request = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.uuid = None
        self.rename_input = QLineEdit()
        self.addWidget(QLabel("Column Name:"))
        self.addWidget(self.rename_input)

        self.rename_input.textChanged.connect(self.on_text_edited)

    def set_current_column(self, uuid: str, name: str):
        self.uuid = uuid
        self.rename_input.blockSignals(True)
        self.rename_input.setText(name)
        self.rename_input.blockSignals(False)

    def on_text_edited(self, new_text):
        if self.uuid:
            self.column_rename_request.emit(self.uuid, new_text)
