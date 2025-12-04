from .base_transformation import BaseTransformation
from tool_uuid.core.dataframe_wrapper import DataFrameWrapper
import pandas as pd


class oneHotEncodeTransformation(BaseTransformation):
    def __init__(self, col_index: int):
        self.col_index = col_index
        self.col_uuid = None
        self.column = None
        self.dummies = None
        self.values = None
        self.child_uuids = []

    def apply(self, df_wrapper: DataFrameWrapper):
        self.col_uuid = df_wrapper.get_uuid_by_index(self.col_index)
        self.column = df_wrapper.get_col_name_by_uuid(self.col_uuid)
        self.values = df_wrapper.get_col_data_by_uuid(self.col_uuid).copy()

        #to ensure correct order of created dummies, we use the categorical dtype with categories in order of appearance
        self.dummies = pd.get_dummies(pd.Categorical(self.values, categories=list(pd.unique(self.values))), prefix=self.column)

        #handling parent index to insert dummies at correct position
        col_order = df_wrapper.get_all_uuids()
        parent_index = col_order.index(self.col_uuid)

        df_wrapper.add_child_columns(self.col_uuid, {col: self.dummies[col] for col in self.dummies.columns})
        self.child_uuids = df_wrapper.get_children_uuids(self.col_uuid)
        
        df_wrapper.remove_column(self.col_uuid)

        new_order = (
            col_order[:parent_index] +
            df_wrapper.get_children_uuids(self.col_uuid) +
            col_order[parent_index + 1:]
        )

        df_wrapper.reorder_columns(new_order)
        return df_wrapper

    def undo(self, df_wrapper: DataFrameWrapper):
        child_uuids = df_wrapper.get_children_uuids(self.col_uuid)
        col_order = df_wrapper.get_all_uuids()
        insert_index = next((i for i, x in enumerate(col_order) if x in child_uuids), None)

        new_order = (
            col_order[:insert_index] +
            [self.col_uuid] +
            col_order[insert_index + len(child_uuids):]
        )

        df_wrapper.restore_parent(self.col_uuid, self.column, self.values)
        df_wrapper.reorder_columns(new_order)
        return df_wrapper
