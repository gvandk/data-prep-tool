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
from data_prep_tool.transformation.col_merge_transformation import BinaryColumnMergeTransformation
from data_prep_tool.transformation.col_filter_transformation import RowValueFilterTransformation
from .dependency_graph import DependencyGraph

from typing import List, Tuple
from numbers import Real
import pandas as pd
import numpy as np
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

    @staticmethod
    def _coerce_binary_flag(value, true_label: str, false_label: str, old_true: str, old_false: str):
        """Return True/False for recognized binary values, or None for unknown values."""
        if pd.isna(value):
            return None

        if isinstance(value, (bool, np.bool_)):
            return bool(value)

        if isinstance(value, Real):
            if value == 1:
                return True
            if value == 0:
                return False

        if isinstance(value, str):
            token = value.strip()
            lowered = token.casefold()
            true_label_norm = str(true_label).strip().casefold()
            false_label_norm = str(false_label).strip().casefold()
            old_true_norm = str(old_true).strip().casefold()
            old_false_norm = str(old_false).strip().casefold()

            if lowered in {"true", "1"}:
                return True
            if lowered in {"false", "0"}:
                return False

            if lowered in {true_label_norm, old_true_norm}:
                return True
            if lowered in {false_label_norm, old_false_norm}:
                return False

        return None

    @staticmethod
    def _build_binary_replace_map(true_val: str, false_val: str, old_true: str, old_false: str):
        """Build replacement map for common boolean/binary representations."""
        return {
            True: true_val,
            False: false_val,
            1: true_val,
            0: false_val,
            "1": true_val,
            "0": false_val,
            "true": true_val,
            "false": false_val,
            "True": true_val,
            "False": false_val,
            old_true: true_val,
            old_false: false_val,
        }

    def _is_binary_like_series(self, series: pd.Series, true_val: str, false_val: str, old_true: str, old_false: str) -> bool:
        """Detect if a series contains only boolean/binary-like values (plus nulls)."""
        non_null = series.dropna()
        if non_null.empty:
            return False

        has_known_binary_value = False
        for value in non_null.unique():
            flag = self._coerce_binary_flag(value, true_val, false_val, old_true, old_false)
            if flag is None:
                return False
            has_known_binary_value = True

        return has_known_binary_value

    def _relabel_binary_like_columns(self, true_val: str, false_val: str, old_true: str, old_false: str):
        """Relabel all binary-like columns, including native boolean columns loaded from CSV."""
        if self.df_wrapper.df is None:
            return

        replace_map = self._build_binary_replace_map(true_val, false_val, old_true, old_false)
        for col_name in self.df_wrapper.df.columns:
            series = self.df_wrapper.df[col_name]
            if self._is_binary_like_series(series, true_val, false_val, old_true, old_false):
                self.df_wrapper.df[col_name] = series.replace(replace_map)

    def _update_binary_filter_labels(self, transformation, true_val: str, false_val: str):
        """Keep value-based row filters aligned with updated binary labels."""
        if not isinstance(transformation, RowValueFilterTransformation):
            return

        transformation.true_label = true_val
        transformation.false_label = false_val

        if transformation.binary_flag is None:
            return

        transformation.filtered_value = true_val if transformation.binary_flag else false_val
    
    def update_binary_labels(self, true_val, false_val):
        """Update binary labels for one-hot/binning columns in place using UUID-targeted relabeling."""
        if str(true_val).strip().casefold() == str(false_val).strip().casefold():
            raise ValueError("True and False labels must be different.")

        old_global_true = self.binary_true
        old_global_false = self.binary_false

        self.binary_true = true_val
        self.binary_false = false_val

        if self.df_wrapper.df is None:
            return

        for trans in self.history:
            if not isinstance(trans, (oneHotEncodeTransformation, BinningTransformation)):
                self._update_binary_filter_labels(trans, true_val, false_val)
                continue

            old_true = trans.true_label
            old_false = trans.false_label

            trans.true_label = true_val
            trans.false_label = false_val

            child_uuids = getattr(trans, "child_uuids", None) or []
            if not child_uuids:
                continue

            replace_map = self._build_binary_replace_map(true_val, false_val, old_true, old_false)

            for child_uuid in child_uuids:
                child_name = self.df_wrapper.get_col_name_by_uuid(child_uuid)
                if not child_name or child_name not in self.df_wrapper.df.columns:
                    continue
                self.df_wrapper.df[child_name] = self.df_wrapper.df[child_name].replace(replace_map)

        for trans in self.redo:
            if isinstance(trans, (oneHotEncodeTransformation, BinningTransformation)):
                trans.true_label = true_val
                trans.false_label = false_val
            else:
                self._update_binary_filter_labels(trans, true_val, false_val)

        self._relabel_binary_like_columns(true_val, false_val, old_global_true, old_global_false)

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
        self.add_row_delete_many([row_index])

    def add_row_delete_many(self, row_indices: List[int]):
        normalized_indices = sorted(set(int(index) for index in row_indices))
        if not normalized_indices:
            raise ValueError("At least one row index must be provided for deletion.")

        self.history.append(RowDeleteTransformation(normalized_indices))
        self.df_wrapper = self.history[-1].apply(self.df_wrapper)
        self.redo.clear()

    def add_row_filter_by_value(self, col_uuid: str, filtered_value):
        series = self.df_wrapper.get_col_data_by_uuid(col_uuid)
        if series is None:
            raise ValueError("The selected column does not exist anymore.")

        binary_flag = None
        if self.is_binary_column(col_uuid):
            coerced = self._coerce_binary_flag(
                filtered_value,
                self.binary_true,
                self.binary_false,
                self.binary_true,
                self.binary_false,
            )
            if coerced is not None:
                binary_flag = bool(coerced)
                filtered_value = self.binary_true if binary_flag else self.binary_false

        transformation = RowValueFilterTransformation(
            col_uuid=col_uuid,
            filtered_value=filtered_value,
            true_label=self.binary_true,
            false_label=self.binary_false,
            binary_flag=binary_flag,
        )
        self.df_wrapper = transformation.apply(self.df_wrapper)
        self.history.append(transformation)
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

    def is_binary_column(self, col_uuid: str) -> bool:
        """Return True when the selected column contains only binary-like values and nulls."""
        series = self.df_wrapper.get_col_data_by_uuid(col_uuid)
        if series is None:
            return False
        return self._is_binary_like_series(
            series,
            self.binary_true,
            self.binary_false,
            self.binary_true,
            self.binary_false,
        )

    def add_binary_column_merge(self, source_col_uuids: list[str], new_col_name: str, delete_source_columns: bool = True):
        unique_source_uuids = list(dict.fromkeys(source_col_uuids or []))
        if len(unique_source_uuids) < 2:
            raise ValueError("Please select at least two columns for binary merge.")

        for source_uuid in unique_source_uuids:
            if not self.is_binary_column(source_uuid):
                source_name = self.df_wrapper.get_col_name_by_uuid(source_uuid) or source_uuid
                raise ValueError(f"Column '{source_name}' is not binary and cannot be merged.")

        transformation = BinaryColumnMergeTransformation(
            unique_source_uuids,
            new_col_name,
            true_label=self.binary_true,
            false_label=self.binary_false,
            delete_source_columns=delete_source_columns,
        )
        self.df_wrapper = transformation.apply(self.df_wrapper)
        self.history.append(transformation)
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
                    graph.mark_deleted(parent_uuid)

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

                elif isinstance(transformation, BinaryColumnMergeTransformation):
                    if not transformation.new_col_uuid:
                        continue
                    graph.register_binary_merge(
                        new_col_uuid=transformation.new_col_uuid,
                        new_col_name=transformation.new_col_name,
                        source_col_uuids=transformation.source_col_uuids,
                        true_label=transformation.true_label,
                        false_label=transformation.false_label,
                        delete_source_columns=transformation.delete_source_columns,
                    )
                    if transformation.delete_source_columns:
                        for source_uuid in transformation.source_col_uuids:
                            graph.mark_deleted(source_uuid)

                elif isinstance(transformation, RowDeleteTransformation):
                    row_indices = getattr(transformation, "row_indices", None)
                    if row_indices:
                        ordered_indices = row_indices
                        if len(row_indices) > 1:
                            ordered_indices = sorted(row_indices, reverse=True)
                        for row_index in ordered_indices:
                            graph.register_row_delete(row_index)
                    else:
                        graph.register_row_delete(transformation.row_index)

                elif isinstance(transformation, RowValueFilterTransformation):
                    graph.register_row_filter(
                        transformation.col_uuid,
                        transformation.filtered_value,
                        binary_flag=transformation.binary_flag,
                        true_label=transformation.true_label,
                        false_label=transformation.false_label,
                    )

                elif isinstance(transformation, RowAddTransformation):
                    graph.register_row_add(transformation.default_value)
                
            return graph