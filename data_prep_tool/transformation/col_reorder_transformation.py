from .base_transformation import BaseTransformation
from data_prep_tool.core.dataframe_wrapper import DataFrameWrapper
from typing import List

class ColumnReorderTransformation(BaseTransformation):
    """Transformation for reordering columns."""
    def __init__(self, new_order: List[str]):
        self.new_order = new_order
        self.old_order = None
        self.new_order_names = None
        self.old_order_names = None

    def _resolve_order_from_names(self, df_wrapper: DataFrameWrapper, names: List[str], fallback_order: List[str]):
        """Resolve a list of UUIDs based on column names, with a fallback to a provided order of UUIDs."""
        resolved_order = []
        seen = set()

        for name in names or []:
            uuid = df_wrapper.get_uuid_by_name(name)
            if uuid and uuid not in seen:
                resolved_order.append(uuid)
                seen.add(uuid)

        for uuid in fallback_order or []:
            col_name = df_wrapper.get_col_name_by_uuid(uuid)
            if col_name and col_name in df_wrapper.df.columns and uuid not in seen:
                resolved_order.append(uuid)
                seen.add(uuid)

        return resolved_order
    
    def apply(self, df_wrapper: DataFrameWrapper):
        self.old_order = df_wrapper.get_all_uuids()
        self.old_order_names = [df_wrapper.get_col_name_by_uuid(uuid) for uuid in self.old_order]

        if self.new_order_names is None:
            self.new_order_names = [df_wrapper.get_col_name_by_uuid(uuid) for uuid in self.new_order]

        effective_order = self._resolve_order_from_names(df_wrapper, self.new_order_names, self.new_order)
        df_wrapper.reorder_columns(effective_order)
        return df_wrapper

    def undo(self, df_wrapper: DataFrameWrapper):
        effective_old_order = self._resolve_order_from_names(df_wrapper, self.old_order_names, self.old_order)
        df_wrapper.reorder_columns(effective_old_order)
        return df_wrapper
