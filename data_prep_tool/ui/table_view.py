from PyQt6.QtWidgets import QTableView, QAbstractItemView
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QKeyEvent, QMouseEvent

class TableView(QTableView):
    """Custom QTableView that emits signals for column reordering and delete key presses."""
    column_reorder_requested = pyqtSignal(list)
    delete_pressed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.horizontalHeader().setSectionsClickable(True)

        header = self.horizontalHeader()
        header.setSectionsMovable(True)
        header.setHighlightSections(True)
        header.sectionMoved.connect(self.on_column_moved)

    def on_column_moved(self):
        """Emit the new column order as a list of UUIDs after a column has been moved."""
        model = self.model()
        if not model:
            return
        
        header = self.horizontalHeader()
        
        uuid_order = []
        for visual_index in range(header.count()):
            logical_index = header.logicalIndex(visual_index)
            column_uuid = model.headerData(logical_index, Qt.Orientation.Horizontal, role=Qt.ItemDataRole.UserRole)
            uuid_order.append(column_uuid)

        self.column_reorder_requested.emit(uuid_order)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Delete:
            self.delete_pressed.emit()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        # Ensure cell clicks are handled as item selection before Qt paints selection.
        if self.indexAt(event.pos()).isValid():
            self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        super().mousePressEvent(event)