from data_prep_tool.transformation.base_transformation import BaseTransformation
from data_prep_tool.core.dataframe_wrapper import DataFrameWrapper
import numpy as np

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
        
        # Robust handling of input types
        if col_name and col_name in df_wrapper.df.columns:
            
            # Handle empty string or None -> NaN
            if self.new_value == "" or self.new_value is None:
                typed_value = np.nan
            else:
                # Try to preserve numeric type if possible
                try:
                    float_val = float(self.new_value)
                    if float_val.is_integer() and "." not in str(self.new_value):
                         typed_value = int(self.new_value)
                    else:
                         typed_value = float_val
                except (ValueError, TypeError):
                    # Keep as string for non-numeric input
                    typed_value = str(self.new_value)

        df_wrapper.set_cell_value(self.col_uuid, self.row_index, typed_value)
        return df_wrapper

    def undo(self, df_wrapper: DataFrameWrapper):
        df_wrapper.set_cell_value(self.col_uuid, self.row_index, self.old_value)
        return df_wrapper