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
            
            # Helper to generate dummies from binned series
            def create_binned_dummies(binned_series, prefix):
                dummies = pd.get_dummies(binned_series, prefix=prefix)
                # Replace boolean values with user-defined labels
                # Note: get_dummies returns uint8 (0/1) or bool depending on version/args
                # We force replace
                return dummies.replace({
                    True: self.true_label, 1: self.true_label,
                    False: self.false_label, 0: self.false_label
                })

            if self.strategy == "Ordinal":
                # Ordinal/Cumulative encoding
                # 1. Get integer codes (0..N-1)
                binned_codes = pd.cut(numeric_values, bins=self.n_bins, labels=False)
                
                # 2. Create cumulative boolean columns
                dummies = pd.DataFrame(index=numeric_values.index)
                for i in range(self.n_bins):
                    # Column i is True if value falls in bin i or higher -> NO, user said:
                    # "if something has 3 stars, columns 1 star, 2 star, 3 star will be TRUE"
                    # If 0-indexed: 3 stars = index 2. So indices 0, 1, 2 are True.
                    # So col_i is True if code >= i.
                    col_name = f"{self.column}_{i}"
                    
                    # Logic: code >= i
                    # e.g. code=2 (3 stars).
                    # i=0: 2>=0 -> T
                    # i=1: 2>=1 -> T
                    # i=2: 2>=2 -> T
                    # i=3: 2>=3 -> F
                    dummies[col_name] = (binned_codes >= i)
                
                # Replace boolean with labels
                dummies = dummies.replace({True: self.true_label, False: self.false_label})

            else:
                # Interval-based strategies: Create one-hot encoded columns for each bin
                if self.strategy == "Custom":
                    if not self.cutoffs:
                        raise ValueError("Cutoffs required")
                    binned = pd.cut(numeric_values, bins=self.cutoffs)

                elif self.strategy in ["Equal Width", "Equidistant"]:
                    binned = pd.cut(numeric_values, bins=self.n_bins)

                elif self.strategy in ["Equal Frequency", "Equinominal"]:
                    # use qcut
                    binned = pd.qcut(numeric_values, q=self.n_bins, duplicates='drop')

                else:
                    # Default fallback
                    binned = pd.cut(numeric_values, bins=self.n_bins)
                
                # Convert categorical/interval series to dummies
                dummies = create_binned_dummies(binned, self.column)

            final_cols = {col: dummies[col] for col in dummies.columns}
            self.created_names = list(dummies.columns)

            # Store current order to insert child column in same position
            col_order = df_wrapper.get_all_uuids()
            parent_index = col_order.index(self.col_uuid)

            df_wrapper.add_child_columns(self.col_uuid, final_cols)
            self.child_uuids = df_wrapper.get_children_uuids(self.col_uuid)
            df_wrapper.remove_column(self.col_uuid)
            
            # Reorder to put child columns where parent was
            new_order = (
                col_order[:parent_index] +
                self.child_uuids +
                col_order[parent_index + 1:]
            )
            df_wrapper.reorder_columns(new_order)

        except Exception as e:
            raise RuntimeError(f"Binning failed: {e}")

        return df_wrapper

    def undo(self, df_wrapper: DataFrameWrapper):
        df_wrapper.restore_parent(self.col_uuid, self.column, self.values)
        return df_wrapper