from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex, QVariant, pyqtSignal
from PyQt6.QtGui import QColor
import numpy as np

from data_prep_tool.core.dataframe_wrapper import DataFrameWrapper


class DataFrameModel(QAbstractTableModel):
    """A Qt TableModel to wrap a pandas DataFrame."""
    cell_edit_request = pyqtSignal(int, str, object)

    def __init__(self, df_wrapper: DataFrameWrapper = None):
        super().__init__()
        self.df_wrapper = df_wrapper
        self.max_rows = 1000
        self.float_precision = 2
        self.error_columns = set()

    def set_error_columns(self, indices):
        self.error_columns = set(indices)
        self.headerDataChanged.emit(Qt.Orientation.Horizontal, 0, self.columnCount()-1)

    def set_view_settings(self, max_rows: int, float_precision: int):
        self.beginResetModel()
        self.max_rows = max(1, int(max_rows))
        self.float_precision = max(1, min(10, int(float_precision)))
        self.error_columns.clear()
        self.endResetModel()

    def update_wrapper(self, new_df_wrapper: DataFrameWrapper):
        self.beginResetModel()
        self.df_wrapper = new_df_wrapper
        self.error_columns.clear()
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        if self.df_wrapper.df is None:
            return 0

        return min(self.df_wrapper.df.shape[0], self.max_rows)

    def columnCount(self, parent=QModelIndex()):
        return 0 if self.df_wrapper.df is None else self.df_wrapper.df.shape[1]
    
    def flags(self, index):
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        
        return (Qt.ItemFlag.ItemIsEnabled |
                Qt.ItemFlag.ItemIsSelectable)

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        return False

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or self.df_wrapper.df is None:
            return QVariant()

        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            value = self.df_wrapper.df.iloc[index.row(), index.column()]
            if isinstance(value, (float, np.floating)):
                if role == Qt.ItemDataRole.EditRole:
                    return str(value)
                return f"{value:.{self.float_precision}f}"
            return str(value)
        
        return QVariant()

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if self.df_wrapper is None:
            return QVariant()
        
        if role == Qt.ItemDataRole.UserRole and orientation == Qt.Orientation.Horizontal:
            return self.df_wrapper.get_uuid_by_index(section)
        
        elif role == Qt.ItemDataRole.BackgroundRole:
            if orientation == Qt.Orientation.Horizontal and section in self.error_columns:
                return QColor(40, 0, 100) # Light red/pink
        
        elif role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return self.df_wrapper.df.columns[section]
            else:
                return str(section + 1)
        
        return QVariant()
    
    def get_column_uuid(self, col_index: int) -> str:
        return self.df_wrapper.get_uuid_by_index(col_index) if self.df_wrapper else None
