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
        """Add new column(s) to the DataFrame and UUID manager."""
        for col_name, col_data in col_dict.items():
            self.df[col_name] = col_data
        self.uuid_manager.add_columns(list(col_dict.keys()))

    def remove_column(self, uuid: str):
        """Remove a column by its UUID."""
        col_name = self.get_col_name_by_uuid(uuid)
        if col_name and col_name in self.df.columns:
            self.df.drop(columns=[col_name], inplace=True)
            self.uuid_manager.remove_column(uuid)
    
    def add_child_columns(self, parent_uuid: str, new_dict: dict):
        """Add child columns to a parent column."""
        parent_name = self.get_col_name_by_uuid(parent_uuid)
        if parent_name:
            for col_name, col_data in new_dict.items():
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
        self.df.drop(columns=self.uuid_manager.get_children_names(parent_uuid), inplace=True)
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
            self.df.at[row_index, col_name] = value
        
    def get_all_uuids(self) -> List[str]:
        """Get all UUIDs in order of DataFrame columns."""
        return [self.uuid_manager.get_uuid_by_name(col) for col in self.df.columns]
    
    def reorder_columns(self, uuid_order: List[str]):
        """Reorder DataFrame columns to match the given UUID order."""

        col_order = []
        for uuid in uuid_order:
            col_name = self.uuid_manager.get_name_by_uuid(uuid)
            if col_name and col_name in self.df.columns:
                col_order.append(col_name)
        
        self.df = self.df[col_order]
        
