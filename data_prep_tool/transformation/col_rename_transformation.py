from .base_transformation import BaseTransformation
from tool_uuid.core.dataframe_wrapper import DataFrameWrapper

class ColumnRenameTransformation(BaseTransformation):

    def __init__(self, col_index: int, new_name: str):
        self.col_index = col_index
        self.col_uuid = None
        self.new_name = new_name

    def apply(self, df_wrapper: DataFrameWrapper):
        self.col_uuid = df_wrapper.get_uuid_by_index(self.col_index)
        self.old_name =  df_wrapper.get_col_name_by_uuid(self.col_uuid)
        df_wrapper.rename_column(self.col_uuid, self.new_name)
        return df_wrapper
    
    def undo(self, df_wrapper: DataFrameWrapper):
        df_wrapper.rename_column(self.col_uuid, self.old_name)
        return df_wrapper