from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt6.QtGui import QFont

class IntroPanel(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        self.title=QLabel("Welcome to the Data Preparation Tool!")
        font = QFont()
        font.setBold(True)
        font.setPointSize(14)
        self.title.setFont(font)
        layout.addWidget(self.title)

        self.label1=QLabel("""This tool allows you to prepare and transform your CSV data into a binary matrix form for easier formal analysis. 
Once you are done with your transformations, you can export your work into a new CSV file or as a python script, which you can run from the command line to execute your transformations anytime.""", 
        wordWrap=True)
        layout.addWidget(self.label1)

        self.label2=QLabel("To get started, load a CSV file using the File menu or drag and drop it.", wordWrap=True)
        bold_font = QFont()
        bold_font.setBold(True)
        self.label2.setFont(bold_font)
        layout.addWidget(self.label2)
        layout.addStretch()