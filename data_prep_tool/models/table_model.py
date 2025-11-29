from PyQt6.QtCore import Qt, QAbstractTableModel


class DataFrameModel(QAbstractTableModel):
    """A Qt TableModel to wrap a pandas DataFrame."""

    def __init__(self, df=None):
        super().__init__()
        self._df = df

    def setDataFrame(self, df):
        self.beginResetModel()
        self._df = df.copy()
        self.endResetModel()

    def rowCount(self, parent=None):
        return 0 if self._df is None else len(self._df.index)

    def columnCount(self, parent=None):
        return 0 if self._df is None else len(self._df.columns)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if index.isValid() and role == Qt.ItemDataRole.DisplayRole:
            return str(self._df.iloc[index.row(), index.column()])
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if self._df is None or role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return str(self._df.columns[section])
        else:
            return str(self._df.index[section])
        
    def setHeaderData(self, section, orientation, value, role=Qt.ItemDataRole.EditRole):
        if self._df is None or role != Qt.ItemDataRole.EditRole:
            return False
        if orientation == Qt.Orientation.Horizontal:
            self._df.columns.values[section] = value
        else:
            self._df.index.values[section] = value
        self.headerDataChanged.emit(orientation, section, section)
        return True
