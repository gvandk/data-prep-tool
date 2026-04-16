import uuid
from numbers import Real

import numpy as np
import pandas as pd

from .base_transformation import BaseTransformation
from data_prep_tool.core.dataframe_wrapper import DataFrameWrapper


class BinaryColumnMergeTransformation(BaseTransformation):
    """Create a new binary column by OR-merging multiple binary source columns."""

    def __init__(self, source_col_uuids: list[str], new_col_name: str, true_label: str = "True", false_label: str = "False", delete_source_columns: bool = True):
        self.source_col_uuids = list(source_col_uuids or [])
        self.new_col_name = str(new_col_name or "").strip()
        self.true_label = true_label
        self.false_label = false_label
        self.delete_source_columns = bool(delete_source_columns)

        self.new_col_uuid = None
        self.insert_index = None
        self._deleted_sources = []
        self._pre_apply_order = []
        self._snapshot_df = None
        self._snapshot_uuid_to_name = None
        self._snapshot_name_to_uuid = None
        self._snapshot_parent_map = None
        self._snapshot_children_map = None
        self._snapshot_ghost_parent_names = None

    def _coerce_binary_flag(self, value):
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
            true_norm = str(self.true_label).strip().casefold()
            false_norm = str(self.false_label).strip().casefold()

            if lowered in {"true", "1", true_norm}:
                return True
            if lowered in {"false", "0", false_norm}:
                return False

        return None

    def _resolve_source_names(self, df_wrapper: DataFrameWrapper) -> list[str]:
        source_names = []
        for source_uuid in self.source_col_uuids:
            source_name = df_wrapper.get_col_name_by_uuid(source_uuid)
            if not source_name or source_name not in df_wrapper.df.columns:
                raise ValueError("Cannot merge columns because one or more selected columns no longer exist.")
            source_names.append(source_name)
        return source_names

    def apply(self, df_wrapper: DataFrameWrapper):
        if len(self.source_col_uuids) < 2:
            raise ValueError("Please select at least two columns for binary merge.")
        if not self.new_col_name:
            raise ValueError("Please provide a name for the merged column.")
        if self.new_col_name in df_wrapper.df.columns:
            raise ValueError(f"Column '{self.new_col_name}' already exists.")

        source_names = self._resolve_source_names(df_wrapper)

        # Keep an exact snapshot so undo can restore the previous state losslessly.
        self._snapshot_df = df_wrapper.df.copy()
        self._snapshot_uuid_to_name = dict(df_wrapper.uuid_manager.uuid_to_name)
        self._snapshot_name_to_uuid = dict(df_wrapper.uuid_manager.name_to_uuid)
        self._snapshot_parent_map = dict(df_wrapper.uuid_manager.parent_map)
        self._snapshot_children_map = {k: list(v) for k, v in df_wrapper.uuid_manager.children_map.items()}
        self._snapshot_ghost_parent_names = dict(df_wrapper.uuid_manager.ghost_parent_names)

        self._pre_apply_order = df_wrapper.get_all_uuids()
        self._deleted_sources = []

        normalized_sources = []
        for source_name in source_names:
            source_series = df_wrapper.df[source_name]
            normalized = source_series.map(self._coerce_binary_flag)
            invalid_mask = normalized.isna() & source_series.notna()
            if invalid_mask.any():
                raise ValueError(f"Column '{source_name}' is not binary and cannot be merged.")
            normalized_sources.append(normalized.fillna(False))

        merged_true_flags = pd.concat(normalized_sources, axis=1).any(axis=1)
        merged_series = merged_true_flags.map({True: self.true_label, False: self.false_label})

        if self.insert_index is None:
            source_indexes = [df_wrapper.df.columns.get_loc(name) for name in source_names]
            self.insert_index = max(source_indexes) + 1

        insert_at = min(self.insert_index, len(df_wrapper.df.columns))
        df_wrapper.df.insert(insert_at, self.new_col_name, merged_series)

        if self.new_col_uuid is None:
            self.new_col_uuid = str(uuid.uuid4())
        df_wrapper.uuid_manager.uuid_to_name[self.new_col_uuid] = self.new_col_name
        df_wrapper.uuid_manager.name_to_uuid[self.new_col_name] = self.new_col_uuid

        if self.delete_source_columns:
            # Cache full source metadata so undo can restore UUID identity and column order.
            for source_uuid, source_name in zip(self.source_col_uuids, source_names):
                if source_name not in df_wrapper.df.columns:
                    continue
                source_index = df_wrapper.df.columns.get_loc(source_name)
                self._deleted_sources.append(
                    {
                        "uuid": source_uuid,
                        "name": source_name,
                        "data": df_wrapper.df[source_name].copy(),
                        "index": source_index,
                    }
                )
                df_wrapper.remove_column(source_uuid)

        return df_wrapper

    def undo(self, df_wrapper: DataFrameWrapper):
        if self._snapshot_df is not None:
            df_wrapper.df = self._snapshot_df.copy()
            df_wrapper.uuid_manager.uuid_to_name = dict(self._snapshot_uuid_to_name or {})
            df_wrapper.uuid_manager.name_to_uuid = dict(self._snapshot_name_to_uuid or {})
            df_wrapper.uuid_manager.parent_map = dict(self._snapshot_parent_map or {})
            df_wrapper.uuid_manager.children_map = {
                parent_uuid: list(child_uuids)
                for parent_uuid, child_uuids in (self._snapshot_children_map or {}).items()
            }
            df_wrapper.uuid_manager.ghost_parent_names = dict(self._snapshot_ghost_parent_names or {})
            return df_wrapper

        if self.new_col_uuid and df_wrapper.get_col_name_by_uuid(self.new_col_uuid):
            df_wrapper.remove_column(self.new_col_uuid)
        elif self.new_col_name in df_wrapper.df.columns:
            df_wrapper.df.drop(columns=[self.new_col_name], inplace=True)
            stale_uuid = df_wrapper.uuid_manager.name_to_uuid.pop(self.new_col_name, None)
            if stale_uuid:
                df_wrapper.uuid_manager.uuid_to_name.pop(stale_uuid, None)

        if self.delete_source_columns and self._deleted_sources:
            for source in sorted(self._deleted_sources, key=lambda item: item["index"]):
                insert_at = min(source["index"], len(df_wrapper.df.columns))
                df_wrapper.df.insert(insert_at, source["name"], source["data"])
                df_wrapper.uuid_manager.uuid_to_name[source["uuid"]] = source["name"]
                df_wrapper.uuid_manager.name_to_uuid[source["name"]] = source["uuid"]

        if self._pre_apply_order:
            df_wrapper.reorder_columns(self._pre_apply_order)

        return df_wrapper
