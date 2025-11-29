from PyQt6.QtWidgets import QMainWindow, QFileDialog, QHBoxLayout, QWidget, QMenuBar, QLabel, QVBoxLayout, QLineEdit, QPushButton, QStackedLayout
from PyQt6.QtCore import pyqtSignal

class GeneralPanel(QWidget):
    #rename_request = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout()
        self.setLayout(layout)
        self.label=QLabel("General Information")
        layout.addWidget(self.label)

        self.row_count_label = QLabel("Number of rows:")
        self.column_count_label = QLabel("Number of columns:")

        layout.addWidget(self.row_count_label)
        layout.addWidget(self.column_count_label)

        layout.addStretch()

        #self.rename_input.textChanged.connect(self.on_text_edited)

    #def on_text_edited(self, new_text):
    #    self.rename_request.emit(new_text)