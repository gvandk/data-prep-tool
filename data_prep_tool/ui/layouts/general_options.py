from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QLineEdit, QHBoxLayout, QPushButton, QComboBox
from PyQt6.QtCore import pyqtSignal, QTimer
from PyQt6.QtGui import QIntValidator

class GeneralPanel(QWidget):
    binary_values_changed = pyqtSignal(str, str)
    add_row_requested = pyqtSignal()
    add_col_requested = pyqtSignal()
    view_settings_changed = pyqtSignal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._binary_label_error_style = "border: 1px solid #d93025;"
        self._binary_label_emit_timer = QTimer(self)
        self._binary_label_emit_timer.setSingleShot(True)
        self._binary_label_emit_timer.setInterval(250)
        self._binary_label_emit_timer.timeout.connect(self._emit_binary_values_changed)

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
        self.missing_values_label = QLabel("Total missing values: 0")
        self.column_types_title_label = QLabel("Column data types:")
        self.column_types_title_label.setFont(font)
        self.column_types_label = QLabel("(none)")
        self.column_types_label.setWordWrap(True)
        layout.addWidget(self.row_count_label)
        layout.addWidget(self.column_count_label)
        layout.addWidget(self.missing_values_label)
        layout.addWidget(self.column_types_title_label)
        layout.addWidget(self.column_types_label)
        
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

        layout.addSpacing(20)

        # View config
        self.view_config_label = QLabel("View:")
        self.view_config_label.setFont(font)
        layout.addWidget(self.view_config_label)

        layout.addWidget(QLabel("Max Rows Shown:"))
        self.max_rows_input = QLineEdit("1000")
        self.max_rows_input.setValidator(QIntValidator(1, 1000000000, self))
        layout.addWidget(self.max_rows_input)

        layout.addWidget(QLabel("Float Decimal Places:"))
        self.float_decimal_select = QComboBox()
        self.float_decimal_select.addItems([str(i) for i in range(1, 11)])
        self.float_decimal_select.setCurrentText("2")
        layout.addWidget(self.float_decimal_select)

        layout.addSpacing(20)

        # Add row/column
        self.add_config_label = QLabel("Add Row / Column:")
        self.add_config_label.setFont(font)
        layout.addWidget(self.add_config_label)

        btn_layout = QHBoxLayout()
        self.add_row_btn = QPushButton("Add Row")
        self.add_col_btn = QPushButton("Add Column")
        btn_layout.addWidget(self.add_row_btn)
        btn_layout.addWidget(self.add_col_btn)
        layout.addLayout(btn_layout)

        layout.addStretch()

        self.true_input.textChanged.connect(self.on_values_changed)
        self.false_input.textChanged.connect(self.on_values_changed)
        self.max_rows_input.textChanged.connect(self.on_view_settings_changed)
        self.float_decimal_select.currentTextChanged.connect(self.on_view_settings_changed)
        self.add_row_btn.clicked.connect(self.add_row_requested.emit)
        self.add_col_btn.clicked.connect(self.add_col_requested.emit)

    def on_values_changed(self):
        """Handle changes in binary value labels and emit signal after a short debounce."""
        self._binary_label_emit_timer.start()

    def _emit_binary_values_changed(self):
        self.binary_values_changed.emit(self.true_input.text(), self.false_input.text())

    def set_binary_labels_error(self, has_error: bool):
        """Highlight binary label inputs when the labels are invalid."""
        style = self._binary_label_error_style if has_error else ""
        self.true_input.setStyleSheet(style)
        self.false_input.setStyleSheet(style)

    def on_view_settings_changed(self):
        """Handle changes in view settings and emit signal."""
        max_rows_text = self.max_rows_input.text().strip()
        if not max_rows_text:
            return

        self.view_settings_changed.emit(int(max_rows_text), int(self.float_decimal_select.currentText()))