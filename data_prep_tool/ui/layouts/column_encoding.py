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

    _ONE_HOT_OPTIONS = ["None", "One-Hot"]
    _BINNING_OPTIONS = ["Equal Width", "Equal Frequency", "Ordinal", "Custom"]

    def __init__(self, parent=None):
        super().__init__(parent)

        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.header_layout = QHBoxLayout()
        self.header_label = QLabel("Encoding / Binning:")
        self.encoding_combo = QComboBox()
        self.encoding_combo.addItems(self._ONE_HOT_OPTIONS + self._BINNING_OPTIONS)
        self.header_layout.addWidget(self.header_label)
        self.header_layout.addWidget(self.encoding_combo)
        self.layout.addLayout(self.header_layout)

        self.binning_config_container = QWidget()
        self.bin_config_layout = QVBoxLayout(self.binning_config_container)
        self.bin_config_layout.setContentsMargins(0, 0, 0, 0)
        
        # Number of Bins
        self.bins_row = QHBoxLayout()
        self.bins_label = QLabel("Number of Bins:")
        self.bins_spin = QSpinBox()
        self.bins_spin.setRange(2, 20) 
        self.bins_spin.setValue(5)
        self.bins_row.addWidget(self.bins_label)
        self.bins_row.addWidget(self.bins_spin)
        self.bins_row.addStretch()
        self.bin_config_layout.addLayout(self.bins_row)

        # Custom Edges Area
        self.edges_label = QLabel("Cut-off Points (Edges):")
        self.bin_config_layout.addWidget(self.edges_label)
        
        self.edges_container = QWidget()
        self.edges_layout = QVBoxLayout(self.edges_container)
        self.edges_layout.setContentsMargins(0,0,0,0)
        self.bin_config_layout.addWidget(self.edges_container)

        # Apply Button
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

        self.intervals_title_label = QLabel("Ordinal Intervals:")
        self.intervals_title_label.setVisible(False)
        self.children_layout.addWidget(self.intervals_title_label)

        self.intervals_content_label = QLabel("")
        self.intervals_content_label.setWordWrap(True)
        self.intervals_content_label.setVisible(False)
        self.children_layout.addWidget(self.intervals_content_label)

        self.generated_columns_label = QLabel("Generated Columns:")
        self.children_layout.addWidget(self.generated_columns_label)

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

    def _set_available_operations(self, can_one_hot: bool, can_binning: bool):
        """Hide unsupported operations from the encoding combobox."""
        current = self.encoding_combo.currentText()

        options = ["None"]
        if can_one_hot:
            options.append("One-Hot")
        if can_binning:
            options.extend(self._BINNING_OPTIONS)

        self.encoding_combo.clear()
        self.encoding_combo.addItems(options)

        if current in options:
            self.encoding_combo.setCurrentText(current)
        else:
            self.encoding_combo.setCurrentText("None")

    def set_current_column(self, uuid: str, encoding: str = None, child_columns: dict = None, n_bins: int = 5, parent_name: str = "", min_val: float = 0, max_val: float = 100, can_one_hot: bool = True, can_binning: bool = True):
        """Set the current column context for the encoding panel."""
        self.uuid = uuid
        self.data_min = min_val
        self.data_max = max_val
        
        self.encoding_combo.blockSignals(True)
        self.bins_spin.blockSignals(True)

        self._set_available_operations(can_one_hot=can_one_hot, can_binning=can_binning)

        requested_encoding = encoding if encoding else "None"
        available_options = [self.encoding_combo.itemText(i) for i in range(self.encoding_combo.count())]
        effective_encoding = requested_encoding if requested_encoding in available_options else "None"

        self.encoding_combo.setCurrentText(effective_encoding)
        self.bins_spin.setValue(n_bins if n_bins else 5)

        is_binning = effective_encoding in self._BINNING_OPTIONS
        is_onehot = effective_encoding == "One-Hot"
        is_custom = effective_encoding == "Custom"

        self.binning_config_container.setVisible(is_binning)
        
        self.edges_label.setVisible(is_custom)
        self.edges_container.setVisible(is_custom)
        self.apply_custom_btn.setVisible(is_custom)
        
        if is_custom:
            self._generate_edge_inputs(n_bins)

        if (is_onehot or is_binning) and child_columns:
            self.children_container.setVisible(True)
            self.children_scroll_area.setVisible(True)
            self._populate_children(child_columns, parent_name, effective_encoding, n_bins)
        else:
            self.children_container.setVisible(False)
            self.children_scroll_area.setVisible(False)
            self._clear_children()
            self._clear_interval_summary()

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
            defaults = [i * 10 for i in range(n_bins + 1)]

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

    def _populate_children(self, child_columns: dict, parent_name: str, encoding: str = None, n_bins: int = 5):
        """Populate the child columns section with rename options for each generated column."""
        self._clear_children()
        
        if parent_name:
            self.parent_label.setText(f"Parent Column: {parent_name}")
            self.parent_label.setVisible(True)
        else:
            self.parent_label.setVisible(False)

        if encoding == "Ordinal":
            self._update_ordinal_interval_summary(child_columns, n_bins)
        else:
            self._clear_interval_summary()

        for child_uuid, child_name in child_columns.items():
            rename_layout = ColumnRename()
            rename_layout.set_current_column(child_uuid, child_name)
            rename_layout.column_rename_request.connect(self.child_rename_request.emit)
            rename_layout.uuid = child_uuid 
            self.children_layout.addLayout(rename_layout)

    def _clear_interval_summary(self):
        """Hide and clear ordinal interval information when not needed."""
        self.intervals_title_label.setVisible(False)
        self.intervals_content_label.setVisible(False)
        self.intervals_content_label.setText("")

    def _update_ordinal_interval_summary(self, child_columns: dict, n_bins: int):
        """Show cumulative value ranges represented by ordinal output columns."""
        try:
            n_bins = max(2, int(n_bins))
        except Exception:
            n_bins = 5

        child_items = list(child_columns.items())
        if not child_items:
            self._clear_interval_summary()
            return

        # Keep the summary aligned with the actual number of generated child columns.
        bin_count = min(n_bins, len(child_items))
        try:
            edges = np.linspace(float(self.data_min), float(self.data_max), bin_count + 1)
        except Exception:
            edges = np.linspace(0.0, float(bin_count), bin_count + 1)

        max_edge = edges[-1]
        summary_lines = []
        for idx, (_, child_name) in enumerate(child_items[:bin_count]):
            lower_edge = edges[idx]
            summary_lines.append(
                f"{child_name}: {lower_edge:.4f} to {max_edge:.4f} (cumulative)"
            )

        self.intervals_title_label.setVisible(True)
        self.intervals_content_label.setText("\n".join(summary_lines))
        self.intervals_content_label.setVisible(True)
    
    def _clear_children(self):
        """Remove all child column widgets from the layout."""
        while self.children_layout.count() > 4:
            item = self.children_layout.takeAt(4)
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
        """Validate custom edges and emit binning request if valid."""
        try:
            edges = [w.value() for w in self._edge_widgets]
            for i in range(len(edges)-1):
                if edges[i] >= edges[i+1]:
                    raise ValueError(f"Cut-off point {edges[i]} is not smaller than {edges[i+1]}.")
            
            self.column_binning_request.emit(self.uuid, "Custom", self.bins_spin.value(), edges)
            
        except ValueError as e:
            QMessageBox.warning(self, "Invalid Cut-offs", str(e))

    def on_combo_changed(self, text):
        """Handle changes in encoding selection and show/hide relevant options."""
        if not self.uuid: return
        
        is_binning = text in ["Equal Width", "Equal Frequency", "Ordinal", "Custom"]
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
        """Handle changes in number of bins and update edge inputs if in Custom mode."""
        if not self.uuid: return
        text = self.encoding_combo.currentText()
        
        if text == "Custom":
            self._generate_edge_inputs(value)
        elif text in ["Equal Width", "Equal Frequency", "Ordinal"]:
            self.column_binning_request.emit(self.uuid, text, value, [])