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
        
        dummies = pd.DataFrame(index=self.values.index)

        try:
            # 1. Custom Binning
            if self.strategy == "Custom":
                if not self.cutoffs: raise ValueError("Cutoffs required")
                binned = pd.cut(self.values, bins=self.cutoffs)
                dummies = pd.get_dummies(binned, prefix=self.column)
                # Apply labels via replace
                dummies = dummies.replace({True: self.true_label, 1: self.true_label, 
                                           False: self.false_label, 0: self.false_label})

            # 2. Intraordinal (Cumulative)
            elif self.strategy == "Intraordinal":
                codes = pd.cut(self.values, bins=self.n_bins, labels=False)
                for i in range(self.n_bins):
                    col_name = f"{self.column}_{i}+"
                    # Direct assignment of custom labels
                    dummies[col_name] = np.where((codes >= i), self.true_label, self.false_label)
            
            # 3. Standard Strategies
            else:
                if self.strategy in ["Equal Width", "Equidistant"]:
                    binned = pd.cut(self.values, bins=self.n_bins)
                elif self.strategy in ["Equal Frequency", "Equinominal"]:
                    binned = pd.qcut(self.values, q=self.n_bins, duplicates='drop')
                else:
                    binned = pd.cut(self.values, bins=self.n_bins)
                dummies = pd.get_dummies(binned, prefix=self.column)
                # Apply labels via replace
                dummies = dummies.replace({True: self.true_label, 1: self.true_label, 
                                           False: self.false_label, 0: self.false_label})

            self.created_names = list(dummies.columns)

            df_wrapper.add_child_columns(self.col_uuid, {col: dummies[col] for col in dummies.columns})
            self.child_uuids = df_wrapper.get_children_uuids(self.col_uuid)
            df_wrapper.remove_column(self.col_uuid)

        except Exception as e:
            raise RuntimeError(f"Binning failed: {e}")

        return df_wrapper

    def undo(self, df_wrapper: DataFrameWrapper):
        df_wrapper.restore_parent(self.col_uuid, self.column, self.values)
        return df_wrapper