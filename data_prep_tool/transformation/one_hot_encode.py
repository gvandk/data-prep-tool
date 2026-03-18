from .base_transformation import BaseTransformation
from data_prep_tool.core.dataframe_wrapper import DataFrameWrapper
import pandas as pd

class oneHotEncodeTransformation(BaseTransformation):
    """Transformation for one-hot encoding a categorical column."""
    def __init__(self, col_index: int, true_label=1, false_label=0):
        self.col_index = col_index
        self.col_uuid = None
        self.column = None
        self.dummies = None
        self.values = None
        self.child_uuids = []
        self.created_names = []
        self._post_apply_order = []
        self._parent_insert_index = 0
        
        self.true_label = true_label
        self.false_label = false_label

    def apply(self, df_wrapper: DataFrameWrapper):
        if self.col_uuid is None:
            self.col_uuid = df_wrapper.get_uuid_by_index(self.col_index)
            
        self.column = df_wrapper.get_col_name_by_uuid(self.col_uuid)
        self.values = df_wrapper.get_col_data_by_uuid(self.col_uuid).copy()

        unique_vals = list(pd.unique(self.values))
        dummies_raw = pd.get_dummies(pd.Categorical(self.values, categories=unique_vals), prefix=self.column)
        
        # Map binary flags to labels
        mapping = {True: self.true_label, False: self.false_label}
        self.dummies = pd.DataFrame(index=dummies_raw.index)
        for col_name in dummies_raw.columns:
            self.dummies[col_name] = dummies_raw[col_name].map(mapping)
        
        self.created_names = list(self.dummies.columns)

        col_order = df_wrapper.get_all_uuids()
        parent_index = col_order.index(self.col_uuid)
        self._parent_insert_index = parent_index

        current_child_names = list(self.dummies.columns)
        child_uuids_to_use = None
        
        # If we have stored UUIDs and the count matches, assume order is preserved (get_dummies is deterministic for same data)
        if self.child_uuids and len(self.child_uuids) == len(current_child_names):
             child_uuids_to_use = self.child_uuids

        df_wrapper.add_child_columns(self.col_uuid, {col: self.dummies[col] for col in self.dummies.columns}, child_uuids_to_use)
        self.child_uuids = df_wrapper.get_children_uuids(self.col_uuid)
        
        df_wrapper.remove_column(self.col_uuid)

        new_order = (
            col_order[:parent_index] +
            df_wrapper.get_children_uuids(self.col_uuid) +
            col_order[parent_index + 1:]
        )

        df_wrapper.reorder_columns(new_order)
        # Store the post-apply order so undo can reconstruct position accurately
        self._post_apply_order = df_wrapper.get_all_uuids()
        return df_wrapper

    def undo(self, df_wrapper: DataFrameWrapper):
        col_order = df_wrapper.get_all_uuids()
        child_uuids = df_wrapper.get_children_uuids(self.col_uuid)
        if not child_uuids:
            child_uuids = self.child_uuids or []
        child_uuid_set = set(child_uuids)

        # Find where children sit in current order (if they still exist)
        visible_child_positions = [i for i, uuid in enumerate(col_order) if uuid in child_uuid_set]
        insert_index = visible_child_positions[0] if visible_child_positions else None

        if insert_index is None:
            # Prefer stored post-apply position, then initial parent index
            stored_child_set = set(self.child_uuids or [])
            stored_index = next(
                (i for i, x in enumerate(self._post_apply_order) if x in stored_child_set),
                None
            )
            insert_index = stored_index if stored_index is not None else self._parent_insert_index

        # Remove all children, insert parent at insert_index for correct order
        non_child_order = [u for u in col_order if u not in child_uuid_set]
        insert_index = min(insert_index, len(non_child_order))
        new_order = (
            non_child_order[:insert_index] +
            [self.col_uuid] +
            non_child_order[insert_index:]
        )

        # Remove children using known UUIDs
        for child_uuid in (child_uuids or []):
             df_wrapper.remove_column(child_uuid)

        # Remove columns by name (Fix for broken UUID chains)
        if self.created_names:
            for name in self.created_names:
                if name in df_wrapper.df.columns:
                     current_uuid = df_wrapper.get_uuid_by_name(name)
                     if current_uuid:
                         df_wrapper.remove_column(current_uuid)
                     else:
                         df_wrapper.df.drop(columns=[name], inplace=True)

        df_wrapper.restore_parent(self.col_uuid, self.column, self.values)
        df_wrapper.reorder_columns(new_order)
        return df_wrapper