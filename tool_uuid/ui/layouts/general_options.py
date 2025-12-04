from PyQt6.QtWidgets import QMainWindow, QFileDialog, QHBoxLayout, QWidget, QMenuBar, QLabel, QVBoxLayout, QLineEdit, QPushButton, QStackedLayout
from PyQt6.QtCore import pyqtSignal

class GeneralPanel(QWidget):

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