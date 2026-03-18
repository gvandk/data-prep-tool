from .base_transformation import BaseTransformation
from data_prep_tool.core.dataframe_wrapper import DataFrameWrapper
import pandas as pd

class BinningTransformation(BaseTransformation):
    """Transformation to bin numeric columns into categorical bins based on specified strategies, 
    with support for both ordinal and interval-based encoding."""
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

        try:
            numeric_values = pd.to_numeric(self.values, errors='coerce')

            def encode_binary_flags(frame: pd.DataFrame) -> pd.DataFrame:
                mapping = {True: self.true_label, False: self.false_label}
                encoded = pd.DataFrame(index=frame.index)
                for col_name in frame.columns:
                    encoded[col_name] = frame[col_name].map(mapping)
                return encoded
            
            # Helper to generate dummies from binned series
            def create_binned_dummies(binned_series, prefix):
                dummies = pd.get_dummies(binned_series, prefix=prefix)
                return encode_binary_flags(dummies)

            if self.strategy == "Ordinal":
                # Ordinal/Cumulative encoding: Create n_bins columns where column i is True if value falls in bin i or higher
                binned_codes = pd.cut(numeric_values, bins=self.n_bins, labels=False)
                
                dummies = pd.DataFrame(index=numeric_values.index)
                for i in range(self.n_bins):
                    col_name = f"{self.column}_{i}"
                    dummies[col_name] = (binned_codes >= i)
                
                dummies = encode_binary_flags(dummies)

            else:
                # Interval-based strategies: Create n_bins columns where column i is True if value falls in bin i
                if self.strategy == "Custom":
                    if not self.cutoffs:
                        raise ValueError("Cutoffs required")
                    binned = pd.cut(numeric_values, bins=self.cutoffs)

                elif self.strategy in ["Equal Width", "Equidistant"]:
                    binned = pd.cut(numeric_values, bins=self.n_bins)

                elif self.strategy in ["Equal Frequency", "Equinominal"]:
                    binned = pd.qcut(numeric_values, q=self.n_bins, duplicates='drop')

                else:
                    # Default fallback: treat as equal width
                    binned = pd.cut(numeric_values, bins=self.n_bins)
                
                dummies = create_binned_dummies(binned, self.column)

            final_cols = {col: dummies[col] for col in dummies.columns}
            self.created_names = list(dummies.columns)

            # Store current order to insert child column in same position
            col_order = df_wrapper.get_all_uuids()
            parent_index = col_order.index(self.col_uuid)

            current_child_names = list(final_cols.keys())
            child_uuids_to_use = None
            if self.child_uuids and len(self.child_uuids) == len(current_child_names):
                child_uuids_to_use = self.child_uuids

            df_wrapper.add_child_columns(self.col_uuid, final_cols, child_uuids_to_use)
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