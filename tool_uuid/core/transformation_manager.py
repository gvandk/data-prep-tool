from core.dataframe_wrapper import DataFrameWrapper
from transformation.col_rename_transformation import ColumnRenameTransformation
from transformation.one_hot_encode import oneHotEncodeTransformation
from transformation.col_reorder_transformation import ColumnReorderTransformation

from typing import List
import pandas as pd
from PyQt6.QtWidgets import QApplication

class TransformationManager:
    def __init__(self, df_wrapper: DataFrameWrapper):
        self.df_wrapper = df_wrapper
        self.history = []
        self.redo = []
    
    def get_current_dataframe(self) -> pd.DataFrame:
        return self.df_wrapper.df
    
    def add_rename(self, col_index, new_name):
        self.history.append(ColumnRenameTransformation(col_index, new_name))
        self.df_wrapper = self.history[-1].apply(self.df_wrapper)
        self.redo.clear()
    
    def add_onehot(self, col_index):
        self.history.append(oneHotEncodeTransformation(col_index))
        self.df_wrapper = self.history[-1].apply(self.df_wrapper)
        self.redo.clear()

    def add_column_reorder(self):
        self.history.append(ColumnReorderTransformation(new_order=List[str]))
        self.df_wrapper = self.history[-1].apply(self.df_wrapper)
        self.redo.clear()

    def undo_transformation(self):
        if not self.history:
            QApplication.beep()
            return

        self.df_wrapper = self.history[-1].undo(self.df_wrapper)
        self.redo.append(self.history.pop())


    def redo_transformation(self):
        if not self.redo:
            QApplication.beep()
            return
        
        transformation = self.redo.pop()
        self.df_wrapper = transformation.apply(self.df_wrapper)
        self.history.append(transformation)