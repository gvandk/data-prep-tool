from typing import List, Set
from .dependency_graph import DependencyGraph, GraphNode

class ScriptGenerator:
    def __init__(self, graph: DependencyGraph):
        self.graph = graph

    def generate_script(self) -> str:
        # 1. Identify what we need to produce (The active columns)
        active_nodes = self.graph.get_active_nodes()
        if not active_nodes:
            return "import pandas as pd\ndf = pd.DataFrame() # No active columns"

        # 2. Backwards Trace / Topological Sort
        # We only visit nodes that are ancestors of our Active Nodes
        sorted_steps: List[GraphNode] = []
        visited: Set[str] = set()
        
        def trace(uuid: str):
            if uuid in visited:
                return
            if uuid not in self.graph.nodes:
                return # Should not happen

            node = self.graph.nodes[uuid]
            visited.add(uuid)

            # Dependencies first!
            for parent_uuid in node.parents:
                trace(parent_uuid)
            
            sorted_steps.append(node)

        # Start tracing from all active nodes
        for node in active_nodes:
            trace(node.uuid)

        # 3. Generate Code
        lines = [
            "import pandas as pd", 
            "", 
            "# Load Data", 
            "df = pd.read_csv('data.csv')", 
            ""
        ]
        
        # Track which One-Hot parents we have already processed
        # (Since one parent spawns multiple children, we don't want to run get_dummies 5 times)
        processed_one_hot_parents: Set[str] = set()

        for node in sorted_steps:
            if node.operation == "LOAD":
                # Check if it was renamed. 
                # Since we updated current_name in place, if it differs from source, we rename now.
                src = node.params.get('source_name')
                if src and src != node.current_name:
                    lines.append(f"# Rename {src} -> {node.current_name}")
                    lines.append(f"df.rename(columns={{'{src}': '{node.current_name}'}}, inplace=True)")
            
            elif node.operation == "ONE_HOT":
                parent_uuid = node.parents[0]
                
                # Only write the block once per parent
                if parent_uuid not in processed_one_hot_parents:
                    parent_node = self.graph.get_node(parent_uuid)
                    parent_name = parent_node.current_name # Use current name (it might have been renamed before OH)
                    prefix = node.params.get('prefix', parent_name)
                    
                    lines.append(f"# One-Hot Encode: {parent_name}")
                    lines.append(f"dummies = pd.get_dummies(pd.Categorical(df['{parent_name}'], categories=list(pd.unique(df['{parent_name}']))), prefix='{prefix}')")
                    lines.append(f"df = pd.concat([df, dummies], axis=1)")
                    
                    processed_one_hot_parents.add(parent_uuid)
                
            if "manual_edits" in node.params:
                curr_name = node.current_name
                for edit in node.params["manual_edits"]:
                    row_idx = edit['row']
                    val = edit['value']
                    
                    # Handle formatting (quotes for strings)
                    val_str = f"'{val}'" if isinstance(val, str) else str(val)
                    
                    lines.append(f"# Manual correction for {curr_name}")
                    lines.append(f"df.at[{row_idx}, '{curr_name}'] = {val_str}")

        # 4. Final Cleanup (Select only active columns)
        # This handles deletions and reordering implicitly
        final_cols = [n.current_name for n in active_nodes]
        lines.append("")
        lines.append("# Final Selection & Reordering")
        lines.append(f"df = df[{final_cols}]")

        return "\n".join(lines)