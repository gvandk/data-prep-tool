from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex, QVariant, pyqtSignal

from tool_uuid.core.dataframe_wrapper import DataFrameWrapper


class DataFrameModel(QAbstractTableModel):
    """A Qt TableModel to wrap a pandas DataFrame."""
    cell_edit_request = pyqtSignal(int, str, object)

    def __init__(self, df_wrapper: DataFrameWrapper = None):
        super().__init__()
        self.df_wrapper = df_wrapper

    def update_wrapper(self, new_df_wrapper: DataFrameWrapper):
        self.beginResetModel()
        self.df_wrapper = new_df_wrapper
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return 0 if self.df_wrapper.df is None else self.df_wrapper.df.shape[0]

    def columnCount(self, parent=QModelIndex()):
        return 0 if self.df_wrapper.df is None else self.df_wrapper.df.shape[1]
    
    def flags(self, index):
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        
        return (Qt.ItemFlag.ItemIsEnabled | 
                Qt.ItemFlag.ItemIsSelectable | 
                Qt.ItemFlag.ItemIsEditable)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or self.df_wrapper.df is None:
            return QVariant()

        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            value = self.df_wrapper.df.iloc[index.row(), index.column()]
            if isinstance(value, float):
                return str(value) if role == Qt.ItemDataRole.EditRole else f"{value:.4f}"
            return str(value)
        
        return QVariant()
    
    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if role == Qt.ItemDataRole.EditRole:
            uuid = self.df_wrapper.get_uuid_by_index(index.column())
            
            self.cell_edit_request.emit(index.row(), uuid, value)

            return True
            
        return False

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if self.df_wrapper is None:
            return QVariant()
        
        if role == Qt.ItemDataRole.UserRole and orientation == Qt.Orientation.Horizontal:
            return self.df_wrapper.get_uuid_by_index(section)
        
        elif role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return self.df_wrapper.df.columns[section]
            else:
                return str(section + 1)
        
        return QVariant()
    
    def get_column_uuid(self, col_index: int) -> str:
        return self.df_wrapper.get_uuid_by_index(col_index) if self.df_wrapper else None
