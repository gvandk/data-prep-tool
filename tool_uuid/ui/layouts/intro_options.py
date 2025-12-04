from PyQt6.QtWidgets import QMainWindow, QFileDialog, QHBoxLayout, QWidget, QMenuBar, QLabel, QVBoxLayout, QLineEdit, QPushButton, QStackedLayout
from PyQt6.QtCore import pyqtSignal

class IntroPanel(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        self.label=QLabel("Welcome to the CSV Processor App!\n\nPlease open a CSV file to get started.")
        layout.addWidget(self.label)

        layout.addStretch()