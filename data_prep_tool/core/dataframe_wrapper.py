from .col_uuid_manager import ColUUIDManager
from typing import List, Optional
import pandas as pd

class DataFrameWrapper:
    def __init__(self, df=None):
        self.df = df.copy() if df is not None else None
        self.uuid_manager = ColUUIDManager()
        if df is not None:
            self.uuid_manager.initialize_from_df(df)
    
    def get_col_name_by_uuid(self, uuid: str) -> str:
        """Get column name by UUID."""
        return self.uuid_manager.get_name_by_uuid(uuid)
    
    def get_col_data_by_uuid(self, uuid: str) -> Optional[pd.Series]:
        """Get column data by UUID."""
        col_name = self.uuid_manager.get_name_by_uuid(uuid)
        return self.df[col_name] if col_name and col_name in self.df.columns else None
    
    def get_uuid_by_index(self, index: int) -> str:
        """Get UUID by column index."""
        return self.uuid_manager.get_uuid_by_index(self.df, index)
    
    def get_uuid_by_name(self, name: str) -> str:
        """Get UUID by column name."""
        return self.uuid_manager.get_uuid_by_name(name)
    
    def rename_column(self, uuid: str, new_name: str):
        """Rename a column given its UUID."""
        old_name = self.uuid_manager.get_name_by_uuid(uuid)
        if old_name:
            self.df.rename(columns={old_name: new_name}, inplace=True)
            self.uuid_manager.rename_column(old_name, new_name)

    def add_columns(self, col_dict: dict):
        """Add new column(s) to the DataFrame and UUID manager.
        
        Args:
            col_dict: Dictionary of column names to column data
            
        Raises:
            ValueError: If any column name already exists in the DataFrame
        """
        # Check if any column name already exists
        existing_columns = [name for name in col_dict.keys() if name in self.df.columns]
        if existing_columns:
            raise ValueError(f"Column(s) {existing_columns} already exist. Cannot add columns with duplicate names.")
        
        for col_name, col_data in col_dict.items():
            # Make a copy to ensure each column has independent data
            if hasattr(col_data, 'copy'):
                self.df[col_name] = col_data.copy()
            else:
                self.df[col_name] = col_data
        self.uuid_manager.add_columns(list(col_dict.keys()))

    def remove_column(self, uuid: str):
        """Remove a column by its UUID."""
        col_name = self.get_col_name_by_uuid(uuid)
        if col_name and col_name in self.df.columns:
            self.df.drop(columns=[col_name], inplace=True)
            self.uuid_manager.remove_column(uuid)
    
    def add_child_columns(self, parent_uuid: str, new_dict: dict):
        """Add child columns to a parent column.
        
        Args:
            parent_uuid: UUID of the parent column
            new_dict: Dictionary of child column names to column data
            
        Raises:
            ValueError: If any column name already exists in the DataFrame
        """
        parent_name = self.get_col_name_by_uuid(parent_uuid)
        if parent_name:
            # Check if any child column name already exists
            existing_columns = [name for name in new_dict.keys() if name in self.df.columns]
            if existing_columns:
                raise ValueError(f"Column(s) {existing_columns} already exist. Cannot add child columns with duplicate names.")
            
            for col_name, col_data in new_dict.items():
                # Make a copy to ensure each column has independent data
                if hasattr(col_data, 'copy'):
                    self.df[col_name] = col_data.copy()
                else:
                    self.df[col_name] = col_data
            self.uuid_manager.add_child_columns(parent_name, list(new_dict.keys()))

    def get_children_uuids(self, parent_uuid: str) -> Optional[List[str]]:
        """Get list of child UUIDs for a given parent UUID."""
        if self.uuid_manager.is_parent(parent_uuid):
            return self.uuid_manager.get_children_uuids(parent_uuid)
    
    def get_parent_uuid(self, child_uuid: str) -> Optional[str]:
        """Get parent UUID for a given UUID."""
        if self.uuid_manager.is_child(child_uuid):
            return self.uuid_manager.get_parent_uuid(child_uuid)
        
    def restore_parent(self, parent_uuid: str, parent_name: str, parent_data: pd.Series):
        """Restore parent column and remove children (for undo one-hot)."""
        self.df[parent_name] = parent_data
        child_names = self.uuid_manager.get_children_names(parent_uuid)
        existing_child_names = [name for name in child_names if name in self.df.columns]
        if existing_child_names:
            self.df.drop(columns=existing_child_names, inplace=True)
        self.uuid_manager.restore_parent(parent_uuid, parent_name)

    def get_cell_value(self, uuid: str, row_index: int):
        """Get the value of a cell given column UUID and row index."""
        col_name = self.get_col_name_by_uuid(uuid)
        if col_name and col_name in self.df.columns:
            return self.df.at[row_index, col_name]    
    
    def set_cell_value(self, uuid: str, row_index: int, value):
        """Set the value of a cell given column UUID and row index."""
        col_name = self.get_col_name_by_uuid(uuid)
        if col_name and col_name in self.df.columns:
            
            # --- 1. Prevent Crash: Float -> Integer Column ---
            # If we try to put 2.5 into an 'int64' column, pandas crashes.
            # We must upgrade the column to float first.
            if pd.api.types.is_integer_dtype(self.df[col_name]):
                # Check if value is a float AND has decimals (e.g. 2.5, not 2.0)
                if isinstance(value, float) and not value.is_integer() and not pd.isna(value):
                     self.df[col_name] = self.df[col_name].astype(float)

            # --- 2. Prevent FutureWarning: Non-Numeric -> Numeric Column ---
            # If we try to put "abc" into a numeric column, we must upgrade to object first.
            is_numeric_col = pd.api.types.is_numeric_dtype(self.df[col_name])
            is_value_numeric = isinstance(value, (int, float, complex))
            is_value_null = pd.isna(value) or value is None

            if is_numeric_col and not is_value_numeric and not is_value_null:
                self.df[col_name] = self.df[col_name].astype(object)

            # --- 3. Perform the Assignment ---
            self.df.at[row_index, col_name] = value

            # --- 4. Self-Healing Types (User Request) ---
            
            # A) Recover Numeric from Object (e.g. fixed "abc" back to 123)
            if self.df[col_name].dtype == 'object':
                try:
                    self.df[col_name] = pd.to_numeric(self.df[col_name], errors='raise')
                except (ValueError, TypeError):
                    pass # Keep as object if it still has text
            
            # B) Recover Integer from Float (e.g. 1.0, 2.0, NaN -> Int64)
            # This handles the "Integers with NaNs" case nicely.
            if pd.api.types.is_float_dtype(self.df[col_name]):
                valid_data = self.df[col_name].dropna()
                if not valid_data.empty:
                    # Check if all valid numbers are integers (e.g. 1.0, 5.0)
                    if (valid_data % 1 == 0).all():
                        try:
                            # Convert to Nullable Integer (Int64) to allow NaNs
                            self.df[col_name] = self.df[col_name].astype("Int64")
                        except TypeError:
                            pass
        
    def get_all_uuids(self) -> List[str]:
        """Get all UUIDs in order of DataFrame columns."""
        return [self.uuid_manager.get_uuid_by_name(col) for col in self.df.columns]
    
    def reorder_columns(self, uuid_order: List[str]):
        """Reorder DataFrame columns to match the given UUID order."""
        col_order = []
        seen = set()
        for uuid in uuid_order:
            col_name = self.uuid_manager.get_name_by_uuid(uuid)
            if col_name and col_name in self.df.columns and col_name not in seen:
                col_order.append(col_name)
                seen.add(col_name)

        # Preserve any existing columns not present in uuid_order.
        # This prevents accidental column loss when uuid_order is stale/partial
        # (e.g. history replay after one-hot/binning regeneration).
        for col_name in self.df.columns:
            if col_name not in seen:
                col_order.append(col_name)
                seen.add(col_name)
        
        self.df = self.df[col_order]
        
