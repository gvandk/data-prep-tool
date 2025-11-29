from PyQt6.QtWidgets import QTableView
from PyQt6.QtCore import pyqtSignal


class TableView(QTableView):
    columnReorderRequested = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.setAlternatingRowColors(True)

        #self.horizontalHeader().setSectionsMovable(True)
        #self.horizontalHeader().setDragEnabled(True)
        #self.horizontalHeader().sectionMoved.connect(self.on_column_moved)

    def on_column_moved(self, logicalIndex, oldVisualIndex, newVisualIndex):
    # Use the indices to figure out the new column order
        new_order = [self.model()._df.columns[self.horizontalHeader().logicalIndex(i)]
                    for i in range(self.model().columnCount())]
        
        # Emit a signal or call the transformation manager
        self.columnReorderRequested.emit(new_order)




    
