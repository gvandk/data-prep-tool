from PyQt6.QtWidgets import (QHBoxLayout, QWidget, QLabel, QVBoxLayout, QPushButton,
                             QGroupBox)
from PyQt6.QtCore import pyqtSignal, Qt
from .column_rename import ColumnRename
from .column_encoding import ColumnEncoding
from .column_order import ColumnOrder
from .column_merge import ColumnMerge

class ColumnPanel(QWidget):
    column_rename_request = pyqtSignal(str, str)
    column_encoding_request = pyqtSignal(str, str)
    column_binning_request = pyqtSignal(str, str, int, list)
    child_rename_request = pyqtSignal(str, str)
    close_request = pyqtSignal()
    delete_col_requested = pyqtSignal(str)
    binary_merge_request = pyqtSignal(list, str, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        header_layout = QHBoxLayout()
        self.label = QLabel("Column Options")
        font = self.label.font()
        font.setBold(True)
        self.label.setFont(font)
        
        self.close_btn = QPushButton("X")
        self.close_btn.setFixedSize(24, 24)
        self.close_btn.clicked.connect(self.close_request.emit)
        
        header_layout.addWidget(self.label)
        header_layout.addStretch()
        header_layout.addWidget(self.close_btn)
        layout.addLayout(header_layout)

        self.stats_group = QGroupBox("Column Statistics")
        stats_layout = QVBoxLayout()
        
        self.stats_label = QLabel("Select a column to see details.")
        self.stats_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        stats_layout.addWidget(self.stats_label)
        self.stats_group.setLayout(stats_layout)
        layout.addWidget(self.stats_group)

        self.column_rename = ColumnRename()
        layout.addLayout(self.column_rename)

        self.column_reorder = ColumnOrder()
        layout.addLayout(self.column_reorder)

        self.encoder_options = ColumnEncoding()
        layout.addWidget(self.encoder_options)

        self.delete_btn = QPushButton("Delete Column")
        layout.addWidget(self.delete_btn)

        self.column_merge = ColumnMerge()
        self.column_merge.setVisible(False)
        layout.addWidget(self.column_merge)

        layout.addStretch()

        self.delete_btn.clicked.connect(self._on_delete)
        self.column_merge.binary_merge_request.connect(self.binary_merge_request.emit)
        self.column_rename.column_rename_request.connect(self.column_rename_request.emit)
        self.encoder_options.column_encoding_request.connect(self.column_encoding_request.emit)
        self.encoder_options.child_rename_request.connect(self.child_rename_request.emit)
        self.encoder_options.column_binning_request.connect(self.column_binning_request.emit)

        self._current_uuid = None

    def set_stats(self, text):
        """Update the statistics label."""
        self.stats_label.setText(text)
    
    def set_current_uuid(self, uuid: str):
        self._current_uuid = uuid

    def _on_delete(self):
        if self._current_uuid:
            self.delete_col_requested.emit(self._current_uuid)

    def _set_layout_visible(self, layout: QHBoxLayout, visible: bool):
        for i in range(layout.count()):
            item = layout.itemAt(i)
            widget = item.widget()
            if widget:
                widget.setVisible(visible)

    def set_single_column_mode(self):
        self._set_layout_visible(self.column_rename, True)
        self._set_layout_visible(self.column_reorder, True)
        self.encoder_options.setVisible(True)
        self.delete_btn.setVisible(True)
        self.column_merge.clear_selection()
        self.column_merge.setVisible(False)

    def set_multi_column_mode(self, selected_uuids: list[str], selected_names: list[str], can_merge: bool):
        self._current_uuid = None

        self._set_layout_visible(self.column_rename, False)
        self._set_layout_visible(self.column_reorder, False)
        self.encoder_options.setVisible(False)
        self.delete_btn.setVisible(False)
        self.column_merge.setVisible(True)
        self.column_merge.set_selection(selected_uuids, selected_names, can_merge)