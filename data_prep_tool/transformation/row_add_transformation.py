from .base_transformation import BaseTransformation
from data_prep_tool.core.dataframe_wrapper import DataFrameWrapper
import pandas as pd

class RowAddTransformation(BaseTransformation):
    """Transformation for adding a new row."""
    def __init__(self, default_value):
        self.default_value = default_value

    def apply(self, df_wrapper: DataFrameWrapper):
        new_row = {col: self.default_value for col in df_wrapper.df.columns}
        df_wrapper.df = pd.concat(
            [df_wrapper.df, pd.DataFrame([new_row])], ignore_index=True
        ).reset_index(drop=True)
        return df_wrapper

    def undo(self, df_wrapper: DataFrameWrapper):
        df_wrapper.df = df_wrapper.df.iloc[:-1].reset_index(drop=True)
        return df_wrapper