from .base_transformation import BaseTransformation
from data_prep_tool.core.dataframe_wrapper import DataFrameWrapper
from typing import List

class ColumnReorderTransformation(BaseTransformation):

    def __init__(self, new_order: List[str]):
        self.new_order = new_order
        self.old_order = None
    
    def apply(self, df_wrapper: DataFrameWrapper):
        self.old_order = df_wrapper.get_all_uuids()
        df_wrapper.reorder_columns(self.new_order)
        return df_wrapper

    def undo(self, df_wrapper: DataFrameWrapper):
        df_wrapper.reorder_columns(self.old_order)
        return df_wrapper
