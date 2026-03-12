from .dataframe_wrapper import DataFrameWrapper
from data_prep_tool.transformation.col_rename_transformation import ColumnRenameTransformation
from data_prep_tool.transformation.one_hot_encode import oneHotEncodeTransformation
from data_prep_tool.transformation.col_reorder_transformation import ColumnReorderTransformation
from data_prep_tool.transformation.cell_edit_transformation import CellEditTransformation
from data_prep_tool.transformation.binning_transformation import BinningTransformation
from .dependency_graph import DependencyGraph

from typing import List, Tuple
import pandas as pd
from PyQt6.QtWidgets import QApplication

class TransformationManager:
    def __init__(self, df_wrapper: DataFrameWrapper):
        self.df_wrapper = df_wrapper
        self.history = []
        self.redo = []
        self.binary_true = "True"
        self.binary_false = "False"

        self.initial_state: List[Tuple[str, str]] = []
        if self.df_wrapper.df is not None:
            for col_name in self.df_wrapper.df.columns:
                uuid = self.df_wrapper.get_uuid_by_name(col_name)
                if uuid:
                    self.initial_state.append((uuid, col_name))
    
    def get_current_dataframe(self) -> pd.DataFrame:
        return self.df_wrapper.df
    
    def update_binary_labels(self, true_val, false_val):
        self.binary_true = true_val
        self.binary_false = false_val
        
        # We need to re-apply history with new settings
        # Strategy: Undo everything, update objects, apply everything
        
        temp_history = []
        while self.history:
            # Pop and undo
            trans = self.history.pop()
            self.df_wrapper = trans.undo(self.df_wrapper)
            # Insert at beginning of temp list to preserve order (Stack logic)
            temp_history.insert(0, trans)
            
        # Update settings
        for trans in temp_history:
            if isinstance(trans, (oneHotEncodeTransformation, BinningTransformation)):
                trans.true_label = true_val
                trans.false_label = false_val
        
        # Re-apply
        for trans in temp_history:
            self.history.append(trans)
            self.df_wrapper = trans.apply(self.df_wrapper)
        
        self.redo.clear() 

    def add_rename(self, col_index, new_name):
        self.history.append(ColumnRenameTransformation(col_index, new_name))
        self.df_wrapper = self.history[-1].apply(self.df_wrapper)
        self.redo.clear()
    
    def add_onehot(self, col_index):
        # Pass current global settings
        self.history.append(oneHotEncodeTransformation(col_index, self.binary_true, self.binary_false))
        self.df_wrapper = self.history[-1].apply(self.df_wrapper)
        self.redo.clear()

    def add_binning(self, col_index: int, strategy: str, n_bins: int, cutoffs: list = None):
        # Pass current global settings
        self.history.append(BinningTransformation(col_index, strategy, n_bins, cutoffs, self.binary_true, self.binary_false))
        self.df_wrapper = self.history[-1].apply(self.df_wrapper)
        self.redo.clear()

    def add_column_reorder(self, new_order):
        self.history.append(ColumnReorderTransformation(new_order))
        self.df_wrapper = self.history[-1].apply(self.df_wrapper)
        self.redo.clear()
    
    def add_cell_edit(self, row_index: int, col_uuid: str, new_value):
        self.history.append(CellEditTransformation(row_index, col_uuid, new_value))
        self.df_wrapper = self.history[-1].apply(self.df_wrapper)
        self.redo.clear()

    def undo_transformation(self):
        if not self.history:
            QApplication.beep()
            return
        self.df_wrapper = self.history[-1].undo(self.df_wrapper)
        self.redo.append(self.history.pop())

    def redo_transformation(self):
        if not self.redo:
            QApplication.beep()
            return
        transformation = self.redo.pop()
        self.df_wrapper = transformation.apply(self.df_wrapper)
        self.history.append(transformation)

    def build_dependency_graph(self) -> DependencyGraph:
            graph = DependencyGraph()
            for uuid, original_name in self.initial_state:
                graph.register_load(uuid, original_name)

            for transformation in self.history:
                if isinstance(transformation, ColumnRenameTransformation):
                    graph.register_rename(transformation.col_uuid, transformation.new_name)

                elif isinstance(transformation, oneHotEncodeTransformation):
                    parent_uuid = transformation.col_uuid
                    child_uuids = transformation.child_uuids
                    child_names = [self.df_wrapper.get_col_name_by_uuid(u) for u in child_uuids]
                    orig_names = getattr(transformation, 'created_names', child_names)
                    
                    graph.register_one_hot(
                        parent_uuid=parent_uuid, 
                        child_uuids=child_uuids, 
                        child_names=child_names, 
                        prefix="...",
                        original_names=orig_names,
                        true_label=transformation.true_label,
                        false_label=transformation.false_label
                    )
                    graph.mark_deleted(parent_uuid)

                elif isinstance(transformation, BinningTransformation):
                    parent_uuid = transformation.col_uuid
                    child_uuids = transformation.child_uuids
                    child_names = [self.df_wrapper.get_col_name_by_uuid(u) for u in child_uuids]
                    orig_names = getattr(transformation, 'created_names', child_names)

                    graph.register_binning(
                        parent_uuid=parent_uuid, 
                        child_uuids=child_uuids,
                        child_names=child_names,
                        strategy=transformation.strategy, 
                        n_bins=transformation.n_bins,
                        original_names=orig_names,
                        cutoffs=transformation.cutoffs,
                        true_label=transformation.true_label,
                        false_label=transformation.false_label
                    )

                elif isinstance(transformation, CellEditTransformation):
                    graph.register_cell_edit(transformation.col_uuid, transformation.row_index, transformation.new_value)
                
            return graph