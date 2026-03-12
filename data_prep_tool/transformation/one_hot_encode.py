from .base_transformation import BaseTransformation
from data_prep_tool.core.dataframe_wrapper import DataFrameWrapper
import pandas as pd

class oneHotEncodeTransformation(BaseTransformation):
    def __init__(self, col_index: int, true_label: str = "True", false_label: str = "False"):
        self.col_index = col_index
        self.col_uuid = None
        self.column = None
        self.dummies = None
        self.values = None
        self.child_uuids = []
        self.created_names = []
        
        self.true_label = true_label
        self.false_label = false_label

    def apply(self, df_wrapper: DataFrameWrapper):
        if self.col_uuid is None:
            self.col_uuid = df_wrapper.get_uuid_by_index(self.col_index)
            
        self.column = df_wrapper.get_col_name_by_uuid(self.col_uuid)
        self.values = df_wrapper.get_col_data_by_uuid(self.col_uuid).copy()

        unique_vals = list(pd.unique(self.values))
        dummies_raw = pd.get_dummies(pd.Categorical(self.values, categories=unique_vals), prefix=self.column)
        
        self.dummies = dummies_raw.replace({True: self.true_label, 1: self.true_label, 
                                            False: self.false_label, 0: self.false_label})
        
        self.created_names = list(self.dummies.columns)

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