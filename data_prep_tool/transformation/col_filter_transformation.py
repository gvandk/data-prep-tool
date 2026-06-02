from numbers import Real

import numpy as np
import pandas as pd

from .base_transformation import BaseTransformation
from data_prep_tool.core.dataframe_wrapper import DataFrameWrapper


class RowValueFilterTransformation(BaseTransformation):
    """Remove rows where the selected column equals a target value."""

    def __init__(
        self,
        col_uuid: str,
        filtered_value,
        true_label: str = "True",
        false_label: str = "False",
        binary_flag: bool | None = None,
    ):
        self.col_uuid = col_uuid
        self.filtered_value = filtered_value
        self.true_label = true_label
        self.false_label = false_label
        self.binary_flag = binary_flag

        self._column_name = None
        self._pre_apply_df = None

    def _coerce_binary_flag(self, value):
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

    def _build_drop_mask(self, series: pd.Series) -> pd.Series:
        if self.binary_flag is not None:
            normalized = series.map(self._coerce_binary_flag)
            return normalized == self.binary_flag

        if pd.isna(self.filtered_value):
            return series.isna()
            
        # Try exact type match first
        exact_mask = series == self.filtered_value
        
        # Fallback to string representation matching to handle mixed types 
        # (e.g., comparing pd.Interval objects with manually edited strings)
        str_mask = series.astype(str) == str(self.filtered_value)
        
        return exact_mask | str_mask

    def apply(self, df_wrapper: DataFrameWrapper):
        self._column_name = df_wrapper.get_col_name_by_uuid(self.col_uuid)
        if not self._column_name or self._column_name not in df_wrapper.df.columns:
            raise ValueError("The selected column does not exist anymore.")

        self._pre_apply_df = df_wrapper.df.copy()
        series = df_wrapper.df[self._column_name]
        drop_mask = self._build_drop_mask(series)
        print(drop_mask, flush=True)
        if not drop_mask.any():
            raise ValueError(
                f"Value '{self.filtered_value}' is not present in column '{self._column_name}'."
            )

        df_wrapper.df = df_wrapper.df.loc[~drop_mask].reset_index(drop=True)
        return df_wrapper

    def undo(self, df_wrapper: DataFrameWrapper):
        if self._pre_apply_df is not None:
            df_wrapper.df = self._pre_apply_df.copy()
        return df_wrapper
