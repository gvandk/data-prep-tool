import uuid
from typing import Dict, List, Optional
import pandas as pd

class ColUUIDManager:
    def __init__(self):
        self.uuid_to_name: Dict[str, str] = {}  # UUID -> current column name
        self.name_to_uuid: Dict[str, str] = {}  # column name -> UUID
        self.parent_map: Dict[str, str] = {}    # child UUID -> parent UUID
        self.children_map: Dict[str, List[str]] = {}  # parent UUID -> list of child UUIDs
        self.ghost_parent_names: Dict[str, str] = {}  # parent UUID -> original parent name

    def initialize_from_df(self, df: pd.DataFrame):
        """Initialize UUID mappings from a DataFrame's columns."""

        # Reset existing mappings
        self.uuid_to_name.clear()
        self.name_to_uuid.clear()
        self.parent_map.clear()
        self.children_map.clear()
        self.ghost_parent_names.clear()

        # Fill mapping dictionaries
        for col in df.columns:
            col_uuid = str(uuid.uuid4())
            self.uuid_to_name[col_uuid] = col
            self.name_to_uuid[col] = col_uuid
    
    def get_uuid_by_name(self, col_name: str) -> Optional[str]:
        """Get UUID for a given column name."""
        return self.name_to_uuid.get(col_name)
    
    def get_name_by_uuid(self, col_uuid: str) -> Optional[str]:
        """Get column name for a given UUID."""
        return self.uuid_to_name.get(col_uuid)
    
    def get_uuid_by_index(self, df: pd.DataFrame, col_index: int) -> Optional[str]:
        """Get UUID for a column by its index in the DataFrame."""
        if col_index < 0 or col_index >= len(df.columns):
            return None
        col_name = df.columns[col_index]
        return self.get_uuid_by_name(col_name)
    
    def rename_column(self, old_name: str, new_name: str):
        """Update mappings when a column is renamed."""
        if old_name in self.name_to_uuid:
            col_uuid = self.name_to_uuid[old_name]
            del self.name_to_uuid[old_name]
            self.name_to_uuid[new_name] = col_uuid
            self.uuid_to_name[col_uuid] = new_name
    
    def add_columns(self, cols: List[str]):
        """Add mapping(s) for new column(s)."""
        for col_name in cols:
            col_uuid = str(uuid.uuid4())
            self.uuid_to_name[col_uuid] = col_name
            self.name_to_uuid[col_name] = col_uuid

    def add_child_columns(self, parent_name: str, child_names: List[str], child_uuids: Optional[List[str]] = None):
        """Add child columns to a parent column."""
        parent_uuid = self.get_uuid_by_name(parent_name)
        if parent_uuid is None:
            return
        
        if parent_uuid not in self.children_map:
            self.children_map[parent_uuid] = []
        
        for i, child_name in enumerate(child_names):
            if child_uuids and i < len(child_uuids):
                child_uuid = child_uuids[i]
            else:
                child_uuid = str(uuid.uuid4())
            self.uuid_to_name[child_uuid] = child_name
            self.name_to_uuid[child_name] = child_uuid
            self.parent_map[child_uuid] = parent_uuid
            self.children_map[parent_uuid].append(child_uuid)

    def get_children_uuids(self, parent_uuid: str) -> List[str]:
        """Get list of child UUIDs for a given parent UUID."""
        return list(self.children_map.get(parent_uuid, []))

    def get_children_names(self, parent_uuid: str) -> List[str]:
        """Get list of child column names for a given parent UUID."""
        if parent_uuid not in self.children_map:
            return []
        child_uuids = self.get_children_uuids(parent_uuid)
        return [self.uuid_to_name[child_uuid] for child_uuid in child_uuids]
    
    def get_parent_uuid(self, col_uuid: str) -> Optional[str]:
        """Get parent UUID for a given column UUID."""
        if col_uuid not in self.parent_map:
            return None
        return self.parent_map.get(col_uuid)
    
    def get_parent_name(self, col_uuid: str) -> Optional[str]:
        """Get parent column name for a given column UUID."""
        parent_uuid = self.get_parent_uuid(col_uuid)
        if parent_uuid is None:
            return None
        
        # When parent column is removed, check ghost map
        if parent_uuid in self.uuid_to_name:
            return self.uuid_to_name.get(parent_uuid)
        return self.ghost_parent_names.get(parent_uuid)
    
    def is_child(self, col_uuid: str) -> bool:
        """Check if column is a child of another column."""
        return col_uuid in self.parent_map

    def is_parent(self, col_uuid: str) -> bool:
        """Check if column has children."""
        return col_uuid in self.children_map
    
    def remove_column(self, col_uuid: str):
        """Remove a column and its mappings. Keep in mind that if a column is a parent, it will remain in relationship mappings."""
        
        # Remove from uuid/name mappings
        if col_uuid in self.uuid_to_name:
            col_name = self.uuid_to_name[col_uuid]

            # If parent, store name in ghost map
            if col_uuid in self.children_map:
                self.ghost_parent_names[col_uuid] = col_name
            
            del self.uuid_to_name[col_uuid]
            del self.name_to_uuid[col_name]
        else:
            return

        # Cleanup if this was a child
        if col_uuid in self.parent_map:
            parent_uuid = self.parent_map[col_uuid]
            if parent_uuid in self.children_map:
                self.children_map[parent_uuid].remove(col_uuid)
                #  Cleanup mapping if no more children
                if self.children_map[parent_uuid] == []:
                    del self.children_map[parent_uuid]
            del self.parent_map[col_uuid]

    def restore_parent(self, parent_uuid:str, parent_name: str):
        """Restore parent column and remove child column mappings."""
        self.uuid_to_name[parent_uuid] = parent_name
        self.name_to_uuid[parent_name] = parent_uuid

        # Cleanup ghost map
        if parent_uuid in self.ghost_parent_names:
            del self.ghost_parent_names[parent_uuid]

        # Remove child mappings
        children_uuids = self.get_children_uuids(parent_uuid).copy()
        for child_uuid in children_uuids:
            self.remove_column(child_uuid)