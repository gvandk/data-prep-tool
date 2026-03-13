from .base_transformation import BaseTransformation
from data_prep_tool.core.dataframe_wrapper import DataFrameWrapper
import pandas as pd
import numpy as np

class BinningTransformation(BaseTransformation):
    def __init__(self, col_index: int, strategy: str, n_bins: int, cutoffs: list = None, true_label: str = "True", false_label: str = "False"):
        self.col_index = col_index
        self.strategy = strategy
        self.n_bins = n_bins
        self.cutoffs = cutoffs
        
        self.true_label = true_label
        self.false_label = false_label
        
        self.col_uuid = None
        self.column = None
        self.values = None
        self.child_uuids = []
        self.created_names = [] 

    def apply(self, df_wrapper: DataFrameWrapper):
        if self.col_uuid is None:
            self.col_uuid = df_wrapper.get_uuid_by_index(self.col_index)
        
        self.column = df_wrapper.get_col_name_by_uuid(self.col_uuid)
        self.values = df_wrapper.get_col_data_by_uuid(self.col_uuid).copy()
        
        binned_col_name = f"{self.column}_binned"

        try:
            numeric_values = pd.to_numeric(self.values, errors='coerce')

            if self.strategy == "Custom":
                if not self.cutoffs:
                    raise ValueError("Cutoffs required")
                binned = pd.cut(numeric_values, bins=self.cutoffs).astype(str)

            elif self.strategy == "Intraordinal":
                binned = pd.cut(numeric_values, bins=self.n_bins, labels=False)

            elif self.strategy in ["Equal Width", "Equidistant"]:
                binned = pd.cut(numeric_values, bins=self.n_bins).astype(str)

            elif self.strategy in ["Equal Frequency", "Equinominal"]:
                binned = pd.qcut(numeric_values, q=self.n_bins, duplicates='drop').astype(str)

            else:
                binned = pd.cut(numeric_values, bins=self.n_bins).astype(str)

            self.created_names = [binned_col_name]

            df_wrapper.add_child_columns(self.col_uuid, {binned_col_name: binned})
            self.child_uuids = df_wrapper.get_children_uuids(self.col_uuid)
            df_wrapper.remove_column(self.col_uuid)

        except Exception as e:
            raise RuntimeError(f"Binning failed: {e}")

        return df_wrapper

    def undo(self, df_wrapper: DataFrameWrapper):
        df_wrapper.restore_parent(self.col_uuid, self.column, self.values)
        return df_wrapper