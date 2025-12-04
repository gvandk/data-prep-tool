from PyQt6.QtWidgets import QMainWindow, QFileDialog, QHBoxLayout, QWidget, QMenuBar, QLabel, QVBoxLayout, QLineEdit, QPushButton, QStackedLayout
from PyQt6.QtCore import pyqtSignal

class RowPanel(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        self.label=QLabel("Row Options")
        layout.addWidget(self.label)

        self.row_index = QLabel("Row Index:")
        layout.addWidget(self.row_index)

        layout.addStretch()