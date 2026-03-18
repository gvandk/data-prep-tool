from .base_transformation import BaseTransformation
from data_prep_tool.core.dataframe_wrapper import DataFrameWrapper

class ColAddTransformation(BaseTransformation):
    """Transformation for adding a new column with a default value."""
    def __init__(self, col_name: str, default_value):
        self.col_name = col_name
        self.default_value = default_value
        self.col_uuid = None

    def apply(self, df_wrapper: DataFrameWrapper):
        df_wrapper.add_columns({self.col_name: [self.default_value] * len(df_wrapper.df)})
        self.col_uuid = df_wrapper.get_uuid_by_name(self.col_name)
        return df_wrapper

    def undo(self, df_wrapper: DataFrameWrapper):
        df_wrapper.remove_column(self.col_uuid)
        return df_wrapper