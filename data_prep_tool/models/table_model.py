from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex, QVariant, pyqtSignal
from PyQt6.QtGui import QBrush, QPalette
from PyQt6.QtWidgets import QApplication
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
        """Marks specified column indices as having errors, which will be visually highlighted in the header."""
        self.error_columns = set(indices)
        self.headerDataChanged.emit(Qt.Orientation.Horizontal, 0, self.columnCount()-1)

    def set_view_settings(self, max_rows: int, float_precision: int):
        """Updates view settings for maximum rows displayed and float decimal precision, and refreshes the model to apply changes."""
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
        """Returns the item flags for the given index, enabling selection and editing."""
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        
        return (Qt.ItemFlag.ItemIsEnabled |
                Qt.ItemFlag.ItemIsSelectable)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        """Returns the data for the given index and role, with special formatting for floats and error highlighting in headers."""
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
        """Returns header data for the given section, orientation, and role, including column names, row numbers, and visual cues for error columns."""
        if self.df_wrapper is None or self.df_wrapper.df is None:
            return QVariant()
        
        # Bounds check for horizontal headers
        if orientation == Qt.Orientation.Horizontal and section >= self.columnCount():
            return QVariant()
        
        if role == Qt.ItemDataRole.UserRole and orientation == Qt.Orientation.Horizontal:
            return self.df_wrapper.get_uuid_by_index(section)
        
        elif role == Qt.ItemDataRole.BackgroundRole:
            if orientation == Qt.Orientation.Horizontal and section in self.error_columns:
                app = QApplication.instance()
                if app:
                    return QBrush(app.palette().color(QPalette.ColorRole.Highlight))

        elif role == Qt.ItemDataRole.ForegroundRole:
            if orientation == Qt.Orientation.Horizontal and section in self.error_columns:
                app = QApplication.instance()
                if app:
                    return QBrush(app.palette().color(QPalette.ColorRole.HighlightedText))
        
        elif role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return self.df_wrapper.df.columns[section]
            else:
                return str(section + 1)
        
        return QVariant()
    
    def get_column_uuid(self, col_index: int) -> str:
        return self.df_wrapper.get_uuid_by_index(col_index) if self.df_wrapper else None
