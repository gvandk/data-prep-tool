from data_prep_tool.transformation.base_transformation import BaseTransformation
from data_prep_tool.core.dataframe_wrapper import DataFrameWrapper

class CellEditTransformation(BaseTransformation):
    def __init__(self, row_index: int, col_uuid: str, new_value):
        self.row_index = row_index
        self.col_uuid = col_uuid
        self.new_value = new_value
        self.old_value = None

    def apply(self, df_wrapper: DataFrameWrapper):
        col_name = df_wrapper.get_col_name_by_uuid(self.col_uuid)
        self.old_value = df_wrapper.get_cell_value(self.col_uuid, self.row_index)

        typed_value = self.new_value
        try:
            current_dtype = df_wrapper.df[col_name].dtype
            dtype_str = str(current_dtype)
            if "int" in dtype_str:
                typed_value = int(self.new_value)
            elif "float" in dtype_str:
                typed_value = float(self.new_value)
        except (ValueError, TypeError):
            typed_value = str(self.new_value)

        df_wrapper.set_cell_value(self.col_uuid, self.row_index, typed_value)
        return df_wrapper

    def undo(self, df_wrapper: DataFrameWrapper):
        df_wrapper.set_cell_value(self.col_uuid, self.row_index, self.old_value)
        return df_wrapper