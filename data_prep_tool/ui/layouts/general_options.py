from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QLineEdit, QHBoxLayout
from PyQt6.QtCore import pyqtSignal, Qt

class GeneralPanel(QWidget):
    binary_values_changed = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Header
        self.label = QLabel("General Information")
        font = self.label.font()
        font.setBold(True)
        font.setPointSize(12)
        self.label.setFont(font)
        layout.addWidget(self.label)

        # Stats
        self.row_count_label = QLabel("Number of rows: 0")
        self.column_count_label = QLabel("Number of columns: 0")
        layout.addWidget(self.row_count_label)
        layout.addWidget(self.column_count_label)
        
        layout.addSpacing(20)

        # Binary Configuration
        self.bin_config_label = QLabel("Binary Value Encoding:")
        self.bin_config_label.setFont(font)
        layout.addWidget(self.bin_config_label)
        
        form_layout = QHBoxLayout()
        
        self.true_input = QLineEdit("True")
        self.false_input = QLineEdit("False")
        
        form_layout.addWidget(QLabel("True Label:"))
        form_layout.addWidget(self.true_input)
        form_layout.addSpacing(10)
        form_layout.addWidget(QLabel("False Label:"))
        form_layout.addWidget(self.false_input)
        
        layout.addLayout(form_layout)
        layout.addWidget(QLabel("(Applies to One-Hot and Binning)"))

        layout.addStretch()

        self.true_input.textChanged.connect(self.on_values_changed)
        self.false_input.textChanged.connect(self.on_values_changed)

    def on_values_changed(self):
        self.binary_values_changed.emit(self.true_input.text(), self.false_input.text())