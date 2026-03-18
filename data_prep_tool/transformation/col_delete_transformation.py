from .base_transformation import BaseTransformation
from data_prep_tool.core.dataframe_wrapper import DataFrameWrapper
import pandas as pd

class ColDeleteTransformation(BaseTransformation):
    """Transformation for deleting a column."""
    def __init__(self, col_uuid: str):
        self.col_uuid = col_uuid
        self.col_name = None
        self.col_data = None
        self.col_index = None

    def apply(self, df_wrapper: DataFrameWrapper):
        self.col_name = df_wrapper.get_col_name_by_uuid(self.col_uuid)
        self.col_data = df_wrapper.df[self.col_name].copy()
        self.col_index = df_wrapper.df.columns.get_loc(self.col_name)
        df_wrapper.remove_column(self.col_uuid)
        return df_wrapper

    def undo(self, df_wrapper: DataFrameWrapper):
        df_wrapper.df.insert(self.col_index, self.col_name, self.col_data)
        df_wrapper.uuid_manager.uuid_to_name[self.col_uuid] = self.col_name
        df_wrapper.uuid_manager.name_to_uuid[self.col_name] = self.col_uuid
        return df_wrapper