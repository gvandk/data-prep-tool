from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QCheckBox, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget


class ColumnMerge(QWidget):
    """Dedicated UI for merging multiple binary columns into one output column."""

    binary_merge_request = pyqtSignal(list, str, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.group = QGroupBox("Multi-Column Merge")
        group_layout = QVBoxLayout()
        group_layout.setContentsMargins(8, 8, 8, 8)
        self.group.setLayout(group_layout)

        self.info_label = QLabel("Use Ctrl+click on headers to select multiple columns.")
        self.info_label.setWordWrap(True)
        group_layout.addWidget(self.info_label)

        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Merged Column Name:"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("merged_binary")
        name_layout.addWidget(self.name_input)
        group_layout.addLayout(name_layout)

        self.delete_sources_checkbox = QCheckBox("Delete source columns after merge")
        self.delete_sources_checkbox.setChecked(True)
        group_layout.addWidget(self.delete_sources_checkbox)

        self.merge_button = QPushButton("Merge Selected Binary Columns")
        self.merge_button.clicked.connect(self._on_merge_clicked)
        group_layout.addWidget(self.merge_button)

        layout.addWidget(self.group)
        self.clear_selection()

    def set_selection(self, selected_uuids: list[str], selected_names: list[str], can_merge: bool):
        self._selected_uuids = list(selected_uuids or [])

        shown_names = ", ".join(selected_names[:4])
        if len(selected_names) > 4:
            shown_names += ", ..."

        self.info_label.setText(
            f"Selected columns ({len(selected_names)}): {shown_names}\n"
            "Rule:\n"
            "- Any True in selected columns -> merged value is True\n"
            "- All False -> merged value is False"
        )

        default_name = "merged_binary"
        if selected_names:
            default_name = f"{selected_names[0]}_merged"
        self.name_input.setText(default_name)

        self.name_input.setEnabled(can_merge)
        self.merge_button.setEnabled(can_merge)

        if can_merge:
            self.merge_button.setToolTip("")
        else:
            self.merge_button.setToolTip("Binary merge is available only when all selected columns are binary.")

    def clear_selection(self):
        self._selected_uuids = []
        self.info_label.setText(
            "Use Ctrl+click on headers to select multiple columns.\n"
            "Rule:\n"
            "- Any True in selected columns -> merged value is True\n"
            "- All False -> merged value is False"
        )
        self.name_input.clear()
        self.name_input.setEnabled(False)
        self.merge_button.setEnabled(False)
        self.merge_button.setToolTip("Select at least two binary columns.")
        self.delete_sources_checkbox.setChecked(True)

    def _on_merge_clicked(self):
        new_col_name = self.name_input.text().strip()
        if self._selected_uuids and new_col_name:
            self.binary_merge_request.emit(
                self._selected_uuids,
                new_col_name,
                self.delete_sources_checkbox.isChecked(),
            )
