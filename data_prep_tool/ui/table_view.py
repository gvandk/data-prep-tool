from PyQt6.QtWidgets import QTableView, QAbstractItemView
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QKeyEvent

class TableView(QTableView):
    """Custom QTableView that emits signals for column reordering, header double-clicks, and delete key presses."""
    column_reorder_requested = pyqtSignal(list)
    header_double_clicked = pyqtSignal(int)
    delete_pressed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

        header = self.horizontalHeader()
        header.setSectionsMovable(True)
        header.setHighlightSections(True)
        header.sectionMoved.connect(self.on_column_moved)
        header.sectionDoubleClicked.connect(self.on_header_double_clicked)

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

    def on_header_double_clicked(self, logicalIndex):
        """Emit the UUID of the double-clicked header column."""
        model=self.model()
        if not model:
            return
        
        uuid = model.get_column_uuid(logicalIndex)
        self.header_double_clicked.emit(uuid)
    
    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Delete:
            self.delete_pressed.emit()
        else:
            super().keyPressEvent(event)