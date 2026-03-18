from typing import List, Set
from .dependency_graph import DependencyGraph, GraphNode

class ScriptGenerator:
    def __init__(self, graph: DependencyGraph, history: list = None):
        self.graph = graph
        self.history = history or []

    def _s(self, value) -> str:
        return repr(str(value))

    def generate_script(self, final_col_uuids: List[str] = None) -> str:
        active_nodes = self.graph.get_active_nodes()

        selected_final_nodes: List[GraphNode] = []
        if final_col_uuids:
            for uuid in final_col_uuids:
                node = self.graph.get_node(uuid)
                if node and not node.is_deleted and node.operation not in ("ROW_DELETE", "ROW_ADD", "CELL_EDIT"):
                    selected_final_nodes.append(node)

        lines = [
            "import pandas as pd",
            "import numpy as np",
            "import sys",
            "import os",
            "",
            "if len(sys.argv) != 3:",
            "    print(\"Usage: python script.py <input_csv> <output_csv>\")",
            "    sys.exit(1)",
            "",
            "input_path = sys.argv[1]",
            "output_path = sys.argv[2]",
            "",
            "if not os.path.exists(input_path):",
            "    print(f\"Error: Input file '{input_path}' not found.\")",
            "    sys.exit(1)",
            "",
            "# Load Data",
            "df = pd.read_csv(input_path)",
            ""
        ]

        if not active_nodes:
            lines.append("df.to_csv(output_path, index=False)")
            return "\n".join(lines)

        # Build sorted steps via dependency trace
        sorted_steps: List[GraphNode] = []
        visited: Set[str] = set()

        def trace(uuid: str):
            if uuid in visited: return
            if uuid not in self.graph.nodes: return
            node = self.graph.nodes[uuid]
            visited.add(uuid)
            for parent_uuid in node.parents:
                trace(parent_uuid)
            sorted_steps.append(node)

        for node in active_nodes:
            trace(node.uuid)

        # Optimization: Coalesce consecutive CELL_EDIT operations on same cell
        optimized_steps = []
        for node in sorted_steps:
             if node.operation == "CELL_EDIT" and optimized_steps:
                last_node = optimized_steps[-1]
                if (last_node.operation == "CELL_EDIT" and 
                    last_node.params.get('target_col_uuid') == node.params.get('target_col_uuid') and
                    last_node.params.get('row_index') == node.params.get('row_index')):
                    # Replace the last edit with this newer one as it overwrites it
                    optimized_steps[-1] = node
                    continue
             optimized_steps.append(node)
        sorted_steps = optimized_steps

        processed_binning_parents: Set[str] = set()
        processed_one_hot_parents: Set[str] = set()

        processed_delete_offset = 0

        for node in sorted_steps:
            print(node.operation, flush=True)
            if node.operation == "LOAD":
                src = node.params.get('source_name')
                if src and src != node.current_name:
                    lines.append(f"df.rename(columns={{{self._s(src)}: {self._s(node.current_name)}}}, inplace=True)")
            
            elif node.operation == "CELL_EDIT":
                target_uuid = node.params.get('target_col_uuid')
                target_node = self.graph.get_node(target_uuid)
                col_name = target_node.current_name
                row = node.params.get('row_index')
                val = node.params.get('value')
                lines.append(f"df.at[{row}, {self._s(col_name)}] = {repr(val)}")
            
            elif node.operation == "ROW_DELETE":
                    adjusted = node.params.get('row_index') - processed_delete_offset
                    lines.append(f"df = df.drop(index={adjusted}).reset_index(drop=True)")
                    processed_delete_offset += 1

            elif node.operation == "ROW_ADD":
                default = node.params.get('default_value', '')
                lines.append(f"df = pd.concat([df, pd.DataFrame([{{col: {repr(default)} for col in df.columns}}])]).reset_index(drop=True)")

            elif node.operation == "COL_ADD":
                default = node.params.get('default_value', '')
                lines.append(f"# Add column: {node.current_name}")
                lines.append(f"df[{self._s(node.current_name)}] = {repr(default)}")

            elif node.operation == "ONE_HOT":
                parent_uuid = node.parents[0]
                if parent_uuid not in processed_one_hot_parents:
                    parent_node = self.graph.get_node(parent_uuid)
                    parent_name = parent_node.current_name
                    prefix = node.params.get('prefix', parent_name)
                    if prefix == "...": prefix = parent_name
                    t_val = node.params.get('true_label', 'True')
                    f_val = node.params.get('false_label', 'False')
                    lines.append(f"# One-Hot Encode: {parent_name}")
                    lines.append(f"dummies = pd.get_dummies(pd.Categorical(df[{self._s(parent_name)}], categories=list(pd.unique(df[{self._s(parent_name)}]))), prefix={self._s(prefix)})")
                    lines.append(f"dummies = dummies.replace({{True: {self._s(t_val)}, 1: {self._s(t_val)}, False: {self._s(f_val)}, 0: {self._s(f_val)}}})")
                    lines.append(f"df = pd.concat([df, dummies], axis=1)")
                    processed_one_hot_parents.add(parent_uuid)
                src = node.params.get('source_name')
                if src and src != node.current_name:
                    lines.append(f"df.rename(columns={{{self._s(src)}: {self._s(node.current_name)}}}, inplace=True)")

            elif node.operation == "BINNING":
                parent_uuid = node.parents[0]
                if parent_uuid not in processed_binning_parents:
                    parent_node = self.graph.get_node(parent_uuid)
                    base_name = node.params.get("pre_binning_name") or parent_node.current_name
                    #binned_name = node.current_name # We now generate multiple columns usually
                    
                    p_src = parent_node.params.get('source_name')
                    if p_src and p_src != base_name:
                        lines.append(f"df.rename(columns={{{self._s(p_src)}: {self._s(base_name)}}}, inplace=True)")
                    
                    strategy = node.params.get("strategy")
                    n = node.params.get("n_bins")
                    cutoffs = node.params.get("cutoffs")
                    t_val = node.params.get('true_label', 'True')
                    f_val = node.params.get('false_label', 'False')

                    lines.append(f"# Binning: {base_name} ({strategy})")
                    lines.append(f"numeric_vals = pd.to_numeric(df[{self._s(base_name)}], errors='coerce')")
                    
                    if strategy == "Ordinal":
                         lines.append(f"binned_codes = pd.cut(numeric_vals, bins={n}, labels=False)")
                         # Generated cumulative logic
                         lines.append(f"dummies = pd.DataFrame(index=df.index)")
                         lines.append(f"for i in range({n}):")
                         col_expr = f"{{'{base_name}'}}_{{i}}" # f-string inside f-string needs escaping
                         lines.append(f"    dummies[f{self._s(col_expr)}] = (binned_codes >= i)")
                    elif strategy == "Custom" and cutoffs:
                        lines.append(f"binned = pd.cut(numeric_vals, bins={cutoffs})")
                        lines.append(f"dummies = pd.get_dummies(binned, prefix={self._s(base_name)})")
                    elif strategy in ["Equal Frequency", "Equinominal"]:
                        lines.append(f"binned = pd.qcut(numeric_vals, q={n}, duplicates='drop')")
                        lines.append(f"dummies = pd.get_dummies(binned, prefix={self._s(base_name)})")
                    else: # Equal Width default
                        lines.append(f"binned = pd.cut(numeric_vals, bins={n})")
                        lines.append(f"dummies = pd.get_dummies(binned, prefix={self._s(base_name)})")
                    
                    lines.append(f"dummies = dummies.replace({{True: {self._s(t_val)}, 1: {self._s(t_val)}, False: {self._s(f_val)}, 0: {self._s(f_val)}}})")
                    lines.append(f"df = pd.concat([df, dummies], axis=1)")

                    lines.append(f"df.drop(columns=[{self._s(base_name)}], inplace=True)")
                    processed_binning_parents.add(parent_uuid)
                
                src = node.params.get('source_name')
                if src and src != node.current_name:
                    lines.append(f"df.rename(columns={{{self._s(src)}: {self._s(node.current_name)}}}, inplace=True)")

        # --- Column selection ---
        if final_col_uuids:
            final_cols = [n.current_name for n in selected_final_nodes]
        else:
            final_cols = [n.current_name for n in active_nodes if n.operation not in ("ROW_DELETE", "ROW_ADD", "CELL_EDIT")]
        final_cols_str = ", ".join(self._s(col) for col in final_cols)
        lines.append("")
        lines.append(f"# Select and order final columns")
        lines.append(f"df = df[[{final_cols_str}]]")
        lines.append("df = df.reset_index(drop=True)")
        lines.append("")

        lines.append("df.to_csv(output_path, index=False)")
        lines.append("print(f\"Successfully processed '{input_path}' and saved to '{output_path}'.\")")

        return "\n".join(lines)