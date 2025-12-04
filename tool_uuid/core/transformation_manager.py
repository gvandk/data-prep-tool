from .dataframe_wrapper import DataFrameWrapper
from tool_uuid.transformation.col_rename_transformation import ColumnRenameTransformation
from tool_uuid.transformation.one_hot_encode import oneHotEncodeTransformation
from tool_uuid.transformation.col_reorder_transformation import ColumnReorderTransformation
from tool_uuid.transformation.cell_edit_transformation import CellEditTransformation
from .dependency_graph import DependencyGraph

from typing import List, Tuple
import pandas as pd
from PyQt6.QtWidgets import QApplication

class TransformationManager:
    def __init__(self, df_wrapper: DataFrameWrapper):
        self.df_wrapper = df_wrapper
        self.history = []
        self.redo = []

        self.initial_state: List[Tuple[str, str]] = []
        if self.df_wrapper.df is not None:
            for col_name in self.df_wrapper.df.columns:
                uuid = self.df_wrapper.get_uuid_by_name(col_name)
                if uuid:
                    self.initial_state.append((uuid, col_name))
    
    def get_current_dataframe(self) -> pd.DataFrame:
        return self.df_wrapper.df
    
    def add_rename(self, col_index, new_name):
        self.history.append(ColumnRenameTransformation(col_index, new_name))
        self.df_wrapper = self.history[-1].apply(self.df_wrapper)
        self.redo.clear()
    
    def add_onehot(self, col_index):
        self.history.append(oneHotEncodeTransformation(col_index))
        self.df_wrapper = self.history[-1].apply(self.df_wrapper)
        self.redo.clear()

    def add_column_reorder(self):
        self.history.append(ColumnReorderTransformation(new_order=List[str]))
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
            """
            Constructs the graph from scratch based on the current history.
            Call this ONLY when you are ready to export.
            """
            graph = DependencyGraph()

            # 1. Hydrate Initial State
            for uuid, original_name in self.initial_state:
                graph.register_load(uuid, original_name)

            # 2. Replay History
            for transformation in self.history:
                
                # CASE: RENAME
                if isinstance(transformation, ColumnRenameTransformation):
                    uuid = transformation.col_uuid 
                    new_name = transformation.new_name
                    graph.register_rename(uuid, new_name)

                # CASE: ONE HOT
                elif isinstance(transformation, oneHotEncodeTransformation):
                    parent_uuid = transformation.col_uuid
                    child_uuids = transformation.child_uuids
                    child_names = [self.df_wrapper.get_col_name_by_uuid(u) for u in child_uuids]
                    
                    graph.register_one_hot(
                        parent_uuid=parent_uuid, 
                        child_uuids=child_uuids, 
                        child_names=child_names, 
                        prefix="..." 
                    )
                    graph.mark_deleted(parent_uuid)

                # CASE: CELL EDIT
                elif isinstance(transformation, CellEditTransformation):
                    graph.register_cell_edit(
                        transformation.col_uuid, 
                        transformation.row_index, 
                        transformation.new_value
                    )


                # CASE: REORDER
                elif isinstance(transformation, ColumnReorderTransformation):
                    pass # Graph doesn't care about reordering steps, only final state

            return graph