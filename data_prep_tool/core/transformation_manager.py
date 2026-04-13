from .dataframe_wrapper import DataFrameWrapper
from data_prep_tool.transformation.col_rename_transformation import ColumnRenameTransformation
from data_prep_tool.transformation.one_hot_encode import oneHotEncodeTransformation
from data_prep_tool.transformation.col_reorder_transformation import ColumnReorderTransformation
from data_prep_tool.transformation.cell_edit_transformation import CellEditTransformation
from data_prep_tool.transformation.binning_transformation import BinningTransformation
from data_prep_tool.transformation.row_delete_transformation import RowDeleteTransformation
from data_prep_tool.transformation.row_add_transformation import RowAddTransformation
from data_prep_tool.transformation.col_delete_transformation import ColDeleteTransformation
from data_prep_tool.transformation.col_add_transformation import ColAddTransformation
from .dependency_graph import DependencyGraph

from typing import List, Tuple
import pandas as pd
from PyQt6.QtWidgets import QApplication

class TransformationManager:
    """Manages the application of transformations to the DataFrameWrapper, along with undo/redo functionality and dependency tracking."""
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
        """Update binary labels for one-hot/binning columns in place using UUID-targeted relabeling."""
        self.binary_true = true_val
        self.binary_false = false_val

        if self.df_wrapper.df is None:
            return

        for trans in self.history:
            if not isinstance(trans, (oneHotEncodeTransformation, BinningTransformation)):
                continue

            old_true = trans.true_label
            old_false = trans.false_label

            trans.true_label = true_val
            trans.false_label = false_val

            child_uuids = getattr(trans, "child_uuids", None) or []
            if not child_uuids:
                continue

            replace_map = {
                old_true: true_val,
                old_false: false_val,
                True: true_val,
                False: false_val,
                1: true_val,
                0: false_val,
            }

            for child_uuid in child_uuids:
                child_name = self.df_wrapper.get_col_name_by_uuid(child_uuid)
                if not child_name or child_name not in self.df_wrapper.df.columns:
                    continue
                self.df_wrapper.df[child_name] = self.df_wrapper.df[child_name].replace(replace_map)

        self.redo.clear()

    def add_rename(self, col_uuid, new_name):
        self.history.append(ColumnRenameTransformation(col_uuid, new_name))
        self.df_wrapper = self.history[-1].apply(self.df_wrapper)
        self.redo.clear()
    
    def add_onehot(self, col_index):
        self.history.append(oneHotEncodeTransformation(col_index, self.binary_true, self.binary_false))
        self.df_wrapper = self.history[-1].apply(self.df_wrapper)
        self.redo.clear()

    def add_binning(self, col_index: int, strategy: str, n_bins: int, cutoffs: list = None):
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

    def add_row_delete(self, row_index: int):
        self.history.append(RowDeleteTransformation(row_index))
        self.df_wrapper = self.history[-1].apply(self.df_wrapper)
        self.redo.clear()

    def add_row_add(self, default_value):
        self.history.append(RowAddTransformation(default_value))
        self.df_wrapper = self.history[-1].apply(self.df_wrapper)
        self.redo.clear()

    def add_col_delete(self, col_uuid: str):
        self.history.append(ColDeleteTransformation(col_uuid))
        self.df_wrapper = self.history[-1].apply(self.df_wrapper)
        self.redo.clear()

    def add_col_add(self, col_name: str, default_value):
        self.history.append(ColAddTransformation(col_name, default_value))
        self.df_wrapper = self.history[-1].apply(self.df_wrapper)
        self.redo.clear()

    def undo_transformation(self):
        """Undoes the last transformation, if possible."""
        if not self.history:
            QApplication.beep()
            return
        self.df_wrapper = self.history[-1].undo(self.df_wrapper)
        self.redo.append(self.history.pop())

    def redo_transformation(self):
        """Redoes the last undone transformation, if possible."""
        if not self.redo:
            QApplication.beep()
            return
        transformation = self.redo.pop()
        self.df_wrapper = transformation.apply(self.df_wrapper)
        self.history.append(transformation)

    def build_dependency_graph(self) -> DependencyGraph:
            """Constructs a dependency graph based on the initial state and the history of transformations applied."""
            graph = DependencyGraph()
            for uuid, original_name in self.initial_state:
                graph.register_load(uuid, original_name)

            for transformation in self.history:
                if isinstance(transformation, ColumnRenameTransformation):
                    graph.register_rename(transformation.col_uuid, transformation.new_name)

                elif isinstance(transformation, oneHotEncodeTransformation):
                    parent_uuid = transformation.col_uuid
                    child_uuids = transformation.child_uuids or []
                    if not child_uuids:
                        continue
                    
                    orig_names = getattr(transformation, 'created_names', [])
                    if not orig_names and getattr(transformation, 'dummies', None) is not None:
                        orig_names = list(transformation.dummies.columns)

                    child_names = []
                    for i, child_uuid in enumerate(child_uuids):
                        child_name = self.df_wrapper.get_col_name_by_uuid(child_uuid)
                        if not child_name and i < len(orig_names):
                            child_name = orig_names[i]
                        if not child_name:
                            child_name = f"unnamed_child_{i}"
                        child_names.append(child_name)
                    
                    if not orig_names:
                        orig_names = child_names

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
                    child_uuids = transformation.child_uuids or []
                    if not child_uuids:
                        continue
                    
                    orig_names = getattr(transformation, 'created_names', [])
                    if not orig_names and getattr(transformation, 'dummies', None) is not None:
                        orig_names = list(transformation.dummies.columns)

                    child_names = []
                    for i, child_uuid in enumerate(child_uuids):
                        child_name = self.df_wrapper.get_col_name_by_uuid(child_uuid)
                        if not child_name and i < len(orig_names):
                            child_name = orig_names[i]
                        if not child_name:
                            child_name = f"unnamed_child_{i}"
                        child_names.append(child_name)
                    
                    if not orig_names:
                        orig_names = child_names

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
                
                elif isinstance(transformation, ColDeleteTransformation):
                    graph.mark_deleted(transformation.col_uuid)

                elif isinstance(transformation, ColAddTransformation):
                    graph.register_col_add(
                        transformation.col_uuid,
                        transformation.col_name,
                        transformation.default_value
                    )

                elif isinstance(transformation, RowDeleteTransformation):
                    graph.register_row_delete(transformation.row_index)

                elif isinstance(transformation, RowAddTransformation):
                    graph.register_row_add(transformation.default_value)
                
            return graph