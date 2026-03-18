from .base_transformation import BaseTransformation
from data_prep_tool.core.dataframe_wrapper import DataFrameWrapper
import pandas as pd

class RowDeleteTransformation(BaseTransformation):
    """Transformation for deleting a row."""
    def __init__(self, row_index: int):
        self.row_index = row_index
        self.deleted_row = None

    def apply(self, df_wrapper: DataFrameWrapper):
        self.deleted_row = df_wrapper.df.iloc[self.row_index].copy()
        df_wrapper.df = df_wrapper.df.drop(index=df_wrapper.df.index[self.row_index]).reset_index(drop=True)
        return df_wrapper

    def undo(self, df_wrapper: DataFrameWrapper):
        top = df_wrapper.df.iloc[:self.row_index]
        bottom = df_wrapper.df.iloc[self.row_index:]
        df_wrapper.df = pd.concat([top, self.deleted_row.to_frame().T, bottom]).reset_index(drop=True)
        return df_wrapper