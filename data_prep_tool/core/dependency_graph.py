from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

@dataclass
class GraphNode:
    """Represents a node in the dependency graph for transformations."""
    uuid: str
    current_name: str
    operation: str
    parents: List[str] = field(default_factory=list)
    params: Dict[str, Any] = field(default_factory=dict)
    is_deleted: bool = False

class DependencyGraph:
    """Manages the dependency graph of transformations applied to the DataFrame."""
    def __init__(self):
        self.nodes: Dict[str, GraphNode] = {}

    def register_load(self, uuid: str, name: str, source: str = "data.csv"):
        self.nodes[uuid] = GraphNode(
            uuid=uuid,
            current_name=name,
            operation="LOAD",
            params={"source_name": name, "source_path": source}
        )

    def register_rename(self, uuid: str, new_name: str):
        if uuid in self.nodes:
            self.nodes[uuid].current_name = new_name

    def register_one_hot(self, parent_uuid: str, child_uuids: List[str], child_names: List[str], prefix: str, original_names: List[str] = None, true_label="True", false_label="False"):
        for i, c_uuid in enumerate(child_uuids):
            source = original_names[i] if original_names and i < len(original_names) else child_names[i]
            
            self.nodes[c_uuid] = GraphNode(
                uuid=c_uuid,
                current_name=child_names[i],
                operation="ONE_HOT",
                parents=[parent_uuid],
                params={
                    "prefix": prefix, 
                    "source_name": source,
                    "true_label": true_label,
                    "false_label": false_label
                }
            )

    def register_binning(self, parent_uuid: str, child_uuids: List[str], child_names: List[str], strategy: str, n_bins: int, original_names: List[str] = None, cutoffs: List[float] = None, true_label="True", false_label="False"):
        
        self.mark_deleted(parent_uuid)
        
        for i, c_uuid in enumerate(child_uuids):
            source = original_names[i] if original_names and i < len(original_names) else child_names[i]
            
            # Store pre-binning name for rename check
            parent_node = self.nodes.get(parent_uuid)
            pre_bin_name = parent_node.current_name if parent_node else ""

            self.nodes[c_uuid] = GraphNode(
                uuid=c_uuid,
                current_name=child_names[i],
                operation="BINNING",
                parents=[parent_uuid],
                params={
                    "strategy": strategy, 
                    "n_bins": n_bins,
                    "source_name": source,
                    "cutoffs": cutoffs,
                    "pre_binning_name": pre_bin_name,
                    "true_label": true_label,
                    "false_label": false_label
                }
            )

    def register_cell_edit(self, uuid: str, row_index: int, new_value):
        node_id = f"cell_edit_{len(self.nodes)}"
        self.nodes[node_id] = GraphNode(
            uuid=node_id,
            current_name="",  # Cell edit doesn't create a column with a name
            operation="CELL_EDIT",
            parents=[uuid],
            params={
                "row_index": row_index,
                "value": new_value,
                "target_col_uuid": uuid
            }
        )

    def register_row_delete(self, row_index: int):
        self.nodes[f"row_delete_{len(self.nodes)}"] = GraphNode(
            uuid=f"row_delete_{len(self.nodes)}",
            current_name="",
            operation="ROW_DELETE",
            params={"row_index": row_index}
        )

    def register_row_filter(self, col_uuid: str, value, binary_flag: Optional[bool] = None, true_label: str = "True", false_label: str = "False"):
        node_id = f"row_filter_{len(self.nodes)}"
        self.nodes[node_id] = GraphNode(
            uuid=node_id,
            current_name="",
            operation="ROW_FILTER",
            parents=[col_uuid],
            params={
                "value": value,
                "target_col_uuid": col_uuid,
                "binary_flag": binary_flag,
                "true_label": true_label,
                "false_label": false_label,
            },
        )

    def register_row_add(self, default_value):
        self.nodes[f"row_add_{len(self.nodes)}"] = GraphNode(
            uuid=f"row_add_{len(self.nodes)}",
            current_name="",
            operation="ROW_ADD",
            params={"default_value": default_value}
        )

    def register_col_add(self, col_uuid: str, col_name: str, default_value):
        self.nodes[col_uuid] = GraphNode(
            uuid=col_uuid,
            current_name=col_name,
            operation="COL_ADD",
            params={"default_value": default_value, "source_name": col_name}
        )

    def register_binary_merge(self, new_col_uuid: str, new_col_name: str, source_col_uuids: List[str], true_label="True", false_label="False", delete_source_columns: bool = True):
        self.nodes[new_col_uuid] = GraphNode(
            uuid=new_col_uuid,
            current_name=new_col_name,
            operation="BINARY_MERGE",
            parents=list(source_col_uuids or []),
            params={
                "true_label": true_label,
                "false_label": false_label,
                "delete_source_columns": bool(delete_source_columns),
            },
        )

    def mark_deleted(self, uuid: str):
        if uuid in self.nodes:
            self.nodes[uuid].is_deleted = True

    def get_active_nodes(self) -> List[GraphNode]:
        return [n for n in self.nodes.values() if not n.is_deleted]
    
    def get_node(self, uuid: str) -> Optional[GraphNode]:
        return self.nodes.get(uuid)