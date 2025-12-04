from PyQt6.QtWidgets import QMainWindow, QFileDialog, QHBoxLayout, QWidget, QMenuBar, QLabel, QVBoxLayout, QLineEdit, QPushButton, QStackedLayout, QComboBox, QFrame
from PyQt6.QtCore import pyqtSignal, Qt

from .column_rename import ColumnRename

class ColumnEncoding(QWidget):
    column_encoding_request = pyqtSignal(str, str)
    child_rename_request = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        #header
        self.header_layout = QHBoxLayout()
        self.header_label = QLabel("Encoding:")
        self.encoding_combo = QComboBox()
        self.encoding_combo.addItems(["None", "One-Hot"])
        self.header_layout.addWidget(self.header_label)
        self.header_layout.addWidget(self.encoding_combo)
        self.layout.addLayout(self.header_layout)

        #expanded area
        self.children_container = QFrame()
        self.children_container.setFrameShape(QFrame.Shape.StyledPanel)
        self.children_layout = QVBoxLayout(self.children_container)
        self.children_layout.addWidget(QLabel("Generated Columns:"))
        self.layout.addWidget(self.children_container)
        self.children_container.setVisible(False)

        self.uuid = None
        self.encoding_combo.currentTextChanged.connect(self.on_encoding_changed)

    def set_current_column(self, uuid: str, encoding: str = None, child_columns: dict = None):
        self.uuid = uuid

        self.encoding_combo.blockSignals(True)
        self.encoding_combo.setCurrentText(encoding)
        self.encoding_combo.blockSignals(False)

        if encoding == "One-Hot" and child_columns:
            self.children_container.setVisible(True)
            self._populate_children(child_columns)
        else:
            self.children_container.setVisible(False)
            self._clear_children()

    def _populate_children(self, child_columns: dict):
        self._clear_children()

        for child_uuid, child_name in child_columns.items():
            rename_layout = ColumnRename()
            rename_layout.set_current_column(child_uuid, child_name)
            rename_layout.column_rename_request.connect(self.child_rename_request.emit)
            self.children_layout.addLayout(rename_layout)
    
    def _clear_children(self):
        while self.children_layout.count():
            item = self.children_layout.takeAt(0)
            widget = item.widget()
            if widget:
                    widget.deleteLater()

    def on_encoding_changed(self, text):
        if self.uuid:
            self.column_encoding_request.emit(self.uuid, text)

