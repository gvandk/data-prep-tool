from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Set

@dataclass
class GraphNode:
    uuid: str
    current_name: str
    operation: str  # 'LOAD', 'ONE_HOT', 'BINNING', etc.
    parents: List[str] = field(default_factory=list)
    params: Dict[str, Any] = field(default_factory=dict)
    is_deleted: bool = False

    # For topological sort state
    _visited: bool = False
    _processing: bool = False

class DependencyGraph:
    def __init__(self):
        self.nodes: Dict[str, GraphNode] = {}

    def register_load(self, uuid: str, name: str, source: str = "data.csv"):
        """Register a column that comes from the original file."""
        self.nodes[uuid] = GraphNode(
            uuid=uuid,
            current_name=name,
            operation="LOAD",
            params={"source_name": name, "source_path": source}
        )

    def register_rename(self, uuid: str, new_name: str):
        """
        Updates the name in place.
        If A -> B -> C, the node just remembers it is currently C.
        """
        if uuid in self.nodes:
            self.nodes[uuid].current_name = new_name

    def register_one_hot(self, parent_uuid: str, child_uuids: List[str], child_names: List[str], prefix: str):
        """Register the children of a One-Hot operation."""
        # Ensure we capture the parent's generic One-Hot parameters
        for c_uuid, c_name in zip(child_uuids, child_names):
            self.nodes[c_uuid] = GraphNode(
                uuid=c_uuid,
                current_name=c_name,
                operation="ONE_HOT",
                parents=[parent_uuid],
                params={"prefix": prefix}
            )

    def register_transformation(self, new_uuid: str, new_name: str, parent_uuids: List[str], op_type: str, params: dict):
        """Generic handler for future transformations (Binning, Math, etc)."""
        self.nodes[new_uuid] = GraphNode(
            uuid=new_uuid,
            current_name=new_name,
            operation=op_type,
            parents=parent_uuids,
            params=params
        )
    
    def register_cell_edit(self, uuid: str, row_index: int, new_value):
        """Register a cell edit operation."""
        if uuid in self.nodes:
            if "manual_edits" not in self.nodes[uuid].params:
                self.nodes[uuid].params["manual_edits"] = []

            self.nodes[uuid].params["manual_edits"].append({
                "row": row_index,
                "value": new_value
            })

    def mark_deleted(self, uuid: str):
        """Soft delete."""
        if uuid in self.nodes:
            self.nodes[uuid].is_deleted = True

    def get_active_nodes(self) -> List[GraphNode]:
        """Return columns that should be present in the final output."""
        return [n for n in self.nodes.values() if not n.is_deleted]
    
    def get_node(self, uuid: str) -> Optional[GraphNode]:
        return self.nodes.get(uuid)