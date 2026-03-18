from .base_transformation import BaseTransformation
from data_prep_tool.core.dataframe_wrapper import DataFrameWrapper

class ColumnRenameTransformation(BaseTransformation):
    """Transformation for renaming a column."""
    def __init__(self, col_uuid: str, new_name: str):
        self.col_uuid = col_uuid
        self.new_name = new_name
        self.old_name = None

    def apply(self, df_wrapper: DataFrameWrapper):
        self.old_name = df_wrapper.get_col_name_by_uuid(self.col_uuid)
        df_wrapper.rename_column(self.col_uuid, self.new_name)
        return df_wrapper
    
    def undo(self, df_wrapper: DataFrameWrapper):
        df_wrapper.rename_column(self.col_uuid, self.old_name)
        return df_wrapper