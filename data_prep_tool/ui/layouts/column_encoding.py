from PyQt6.QtWidgets import (QHBoxLayout, QWidget, QLabel, QVBoxLayout, QComboBox, 
                             QFrame, QSpinBox, QDoubleSpinBox, QPushButton, QMessageBox, QScrollArea)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont
import numpy as np

from .column_rename import ColumnRename

class ColumnEncoding(QWidget):
    column_encoding_request = pyqtSignal(str, str)
    column_binning_request = pyqtSignal(str, str, int, list)
    child_rename_request = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.header_layout = QHBoxLayout()
        self.header_label = QLabel("Encoding / Binning:")
        self.encoding_combo = QComboBox()
        self.encoding_combo.addItems([
            "None", "One-Hot", 
            "Equal Width", "Equal Frequency", 
            "Intraordinal", "Custom"
        ])
        self.header_layout.addWidget(self.header_label)
        self.header_layout.addWidget(self.encoding_combo)
        self.layout.addLayout(self.header_layout)

        self.binning_config_container = QWidget()
        self.bin_config_layout = QVBoxLayout(self.binning_config_container)
        self.bin_config_layout.setContentsMargins(0, 0, 0, 0)
        
        # 1. Number of Bins
        self.bins_row = QHBoxLayout()
        self.bins_label = QLabel("Number of Bins:")
        self.bins_spin = QSpinBox()
        self.bins_spin.setRange(2, 20) 
        self.bins_spin.setValue(5)
        self.bins_row.addWidget(self.bins_label)
        self.bins_row.addWidget(self.bins_spin)
        self.bins_row.addStretch()
        self.bin_config_layout.addLayout(self.bins_row)

        # 2. Custom Edges Area
        self.edges_label = QLabel("Cut-off Points (Edges):")
        self.bin_config_layout.addWidget(self.edges_label)
        
        self.edges_container = QWidget()
        self.edges_layout = QVBoxLayout(self.edges_container)
        self.edges_layout.setContentsMargins(0,0,0,0)
        self.bin_config_layout.addWidget(self.edges_container)

        # 3. Apply Button
        self.apply_custom_btn = QPushButton("Apply Custom Bins")
        self.apply_custom_btn.clicked.connect(self.on_apply_custom_clicked)
        self.bin_config_layout.addWidget(self.apply_custom_btn)
        
        self.layout.addWidget(self.binning_config_container)
        self.binning_config_container.setVisible(False)

        self.children_container = QFrame()
        self.children_container.setFrameShape(QFrame.Shape.StyledPanel)
        self.children_layout = QVBoxLayout(self.children_container)
        
        self.parent_label = QLabel("")
        font = QFont()
        font.setBold(True)
        self.parent_label.setFont(font)
        self.children_layout.addWidget(self.parent_label)
        self.children_layout.addWidget(QLabel("Generated Columns:"))

        self.children_scroll_area = QScrollArea()
        self.children_scroll_area.setWidgetResizable(True)
        self.children_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.children_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.children_scroll_area.setMinimumHeight(140)
        self.children_scroll_area.setMaximumHeight(260)
        self.children_scroll_area.setWidget(self.children_container)
        
        self.layout.addWidget(self.children_scroll_area)
        self.children_container.setVisible(False)
        self.children_scroll_area.setVisible(False)

        self.uuid = None
        self._edge_widgets = [] 
        
        # Store data bounds for calculating defaults
        self.data_min = 0
        self.data_max = 100

        self.encoding_combo.currentTextChanged.connect(self.on_combo_changed)
        self.bins_spin.valueChanged.connect(self.on_bins_changed)

    def set_current_column(self, uuid: str, encoding: str = None, child_columns: dict = None, n_bins: int = 5, parent_name: str = "", min_val: float = 0, max_val: float = 100):
        self.uuid = uuid
        self.data_min = min_val
        self.data_max = max_val
        
        self.encoding_combo.blockSignals(True)
        self.bins_spin.blockSignals(True)

        self.encoding_combo.setCurrentText(encoding if encoding else "None")
        self.bins_spin.setValue(n_bins if n_bins else 5)

        is_binning = encoding in ["Equal Width", "Equal Frequency", "Intraordinal", "Custom"]
        is_onehot = encoding == "One-Hot"
        is_custom = encoding == "Custom"

        self.binning_config_container.setVisible(is_binning)
        
        self.edges_label.setVisible(is_custom)
        self.edges_container.setVisible(is_custom)
        self.apply_custom_btn.setVisible(is_custom)
        
        if is_custom:
            self._generate_edge_inputs(n_bins)

        if (is_onehot or is_binning) and child_columns:
            self.children_container.setVisible(True)
            self.children_scroll_area.setVisible(True)
            self._populate_children(child_columns, parent_name)
        else:
            self.children_container.setVisible(False)
            self.children_scroll_area.setVisible(False)
            self._clear_children()

        self.encoding_combo.blockSignals(False)
        self.bins_spin.blockSignals(False)

    def _generate_edge_inputs(self, n_bins):
        """Creates N+1 spinboxes with equidistant default values."""
        # Clear existing
        while self.edges_layout.count():
            item = self.edges_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
            elif item.layout(): item.layout().deleteLater()
        self._edge_widgets = []

        # Calculate default equal-width edges based on data range
        try:
            defaults = np.linspace(self.data_min, self.data_max, n_bins + 1)
        except Exception:
            defaults = [i * 10 for i in range(n_bins + 1)] # Fallback

        # Create N+1 inputs
        for i in range(n_bins + 1):
            row = QHBoxLayout()
            label_text = "Min:" if i == 0 else "Max:" if i == n_bins else f"Cut {i}:"
            row.addWidget(QLabel(label_text))
            
            spin = QDoubleSpinBox()
            spin.setRange(-999999999, 999999999) 
            spin.setDecimals(2)
            spin.setValue(float(defaults[i]))
            
            row.addWidget(spin)
            container = QWidget()
            container.setLayout(row)
            self.edges_layout.addWidget(container)
            self._edge_widgets.append(spin)

    def _populate_children(self, child_columns: dict, parent_name: str):
        self._clear_children()
        
        if parent_name:
            self.parent_label.setText(f"Parent Column: {parent_name}")
            self.parent_label.setVisible(True)
        else:
            self.parent_label.setVisible(False)

        for child_uuid, child_name in child_columns.items():
            rename_layout = ColumnRename()
            rename_layout.set_current_column(child_uuid, child_name)
            rename_layout.column_rename_request.connect(self.child_rename_request.emit)
            rename_layout.uuid = child_uuid 
            self.children_layout.addLayout(rename_layout)
    
    def _clear_children(self):
        while self.children_layout.count() > 2:
            item = self.children_layout.takeAt(2)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            elif item.layout():
                child_layout = item.layout()
                while child_layout.count():
                    child_item = child_layout.takeAt(0)
                    if child_item.widget():
                        child_item.widget().deleteLater()
                child_layout.deleteLater()

    def on_apply_custom_clicked(self):
        try:
            edges = [w.value() for w in self._edge_widgets]
            for i in range(len(edges)-1):
                if edges[i] >= edges[i+1]:
                    raise ValueError(f"Cut-off point {edges[i]} is not smaller than {edges[i+1]}.")
            
            self.column_binning_request.emit(self.uuid, "Custom", self.bins_spin.value(), edges)
            
        except ValueError as e:
            QMessageBox.warning(self, "Invalid Cut-offs", str(e))

    def on_combo_changed(self, text):
        if not self.uuid: return
        
        is_binning = text in ["Equal Width", "Equal Frequency", "Intraordinal", "Custom"]
        self.binning_config_container.setVisible(is_binning)
        
        is_custom = (text == "Custom")
        self.edges_label.setVisible(is_custom)
        self.edges_container.setVisible(is_custom)
        self.apply_custom_btn.setVisible(is_custom)
        
        if is_custom:
            self._generate_edge_inputs(self.bins_spin.value())
        elif is_binning:
            self.column_binning_request.emit(self.uuid, text, self.bins_spin.value(), [])
        else:
            self.column_encoding_request.emit(self.uuid, text)

    def on_bins_changed(self, value):
        if not self.uuid: return
        text = self.encoding_combo.currentText()
        
        if text == "Custom":
            self._generate_edge_inputs(value)
        elif text in ["Equal Width", "Equal Frequency", "Intraordinal"]:
            self.column_binning_request.emit(self.uuid, text, value, [])