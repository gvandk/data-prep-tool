from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QLineEdit, QHBoxLayout, QPushButton
from PyQt6.QtCore import pyqtSignal, Qt

class GeneralPanel(QWidget):
    binary_values_changed = pyqtSignal(str, str)
    add_row_requested = pyqtSignal(str)
    add_col_requested = pyqtSignal(str)

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

        # Binary config
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

        layout.addSpacing(20)

        self.add_config_label = QLabel("Add Row / Column:")
        self.add_config_label.setFont(font)
        layout.addWidget(self.add_config_label)

        layout.addWidget(QLabel("Default Value:"))
        self.default_value_input = QLineEdit("")
        layout.addWidget(self.default_value_input)

        layout.addWidget(QLabel("New Column Name:"))
        self.new_col_name_input = QLineEdit("new_column")
        layout.addWidget(self.new_col_name_input)

        btn_layout = QHBoxLayout()
        self.add_row_btn = QPushButton("Add Row")
        self.add_col_btn = QPushButton("Add Column")
        btn_layout.addWidget(self.add_row_btn)
        btn_layout.addWidget(self.add_col_btn)
        layout.addLayout(btn_layout)

        layout.addStretch()

        self.true_input.textChanged.connect(self.on_values_changed)
        self.false_input.textChanged.connect(self.on_values_changed)
        self.add_row_btn.clicked.connect(lambda: self.add_row_requested.emit(self.default_value_input.text()))
        self.add_col_btn.clicked.connect(lambda: self.add_col_requested.emit(self.default_value_input.text()))

    def on_values_changed(self):
        self.binary_values_changed.emit(self.true_input.text(), self.false_input.text())