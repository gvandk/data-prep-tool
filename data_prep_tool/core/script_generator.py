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
                if node and not node.is_deleted and node.operation not in ("ROW_DELETE", "ROW_ADD"):
                    selected_final_nodes.append(node)

        #col_active_nodes = [n for n in active_nodes if n.operation not in ("ROW_DELETE", "ROW_ADD")]

        lines = [
            "import pandas as pd",
            "import numpy as np",
            "import sys",
            "import os",
            "",
            "if len(sys.argv) != 3:",
            "    print('Usage: python cleaning_script.py <source_csv> <output_csv>')",
            "    sys.exit(1)",
            "",
            "source_path = sys.argv[1]",
            "output_path = sys.argv[2]",
            "",
            "if not os.path.exists(source_path):",
            "    print(f'Error: Source file {source_path} not found.')",
            "    sys.exit(1)",
            "",
            "# Load Data",
            "df = pd.read_csv(source_path)",
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

        processed_binning_parents: Set[str] = set()
        processed_one_hot_parents: Set[str] = set()

        processed_delete_offset = 0

        for node in sorted_steps:
            print(node.operation, flush=True)
            if node.operation == "LOAD":
                src = node.params.get('source_name')
                if src and src != node.current_name:
                    lines.append(f"# Rename {src} -> {node.current_name}")
                    lines.append(f"df.rename(columns={{{self._s(src)}: {self._s(node.current_name)}}}, inplace=True)")
            
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
                    p_src = parent_node.params.get('source_name')
                    if p_src and p_src != base_name:
                        lines.append(f"df.rename(columns={{{self._s(p_src)}: {self._s(base_name)}}}, inplace=True)")
                    strategy = node.params.get("strategy")
                    n = node.params.get("n_bins")
                    cutoffs = node.params.get("cutoffs")
                    t_val = node.params.get('true_label', 'True')
                    f_val = node.params.get('false_label', 'False')
                    lines.append(f"# Binning & Binarization: {base_name} ({strategy})")
                    lines.append(f"df[{self._s(base_name)}] = pd.to_numeric(df[{self._s(base_name)}], errors='coerce')")
                    if strategy == "Custom" and cutoffs:
                        lines.append(f"bins = pd.cut(df[{self._s(base_name)}], bins={cutoffs})")
                        lines.append(f"dummies = pd.get_dummies(bins, prefix={self._s(base_name)})")
                        lines.append(f"dummies = dummies.replace({{True: {self._s(t_val)}, 1: {self._s(t_val)}, False: {self._s(f_val)}, 0: {self._s(f_val)}}})")
                    elif strategy == "Intraordinal":
                        lines.append(f"codes = pd.cut(df[{self._s(base_name)}], bins={n}, labels=False)")
                        lines.append(f"dummies = pd.DataFrame(index=df.index)")
                        lines.append(f"for i in range({n}):")
                        lines.append(f"    dummies[f'{{{self._s(base_name)}}}_{{i}}+'] = np.where((codes >= i), {self._s(t_val)}, {self._s(f_val)})")
                    else:
                        if strategy in ["Equal Width", "Equidistant"]:
                            lines.append(f"bins = pd.cut(df[{self._s(base_name)}], bins={n})")
                        elif strategy in ["Equal Frequency", "Equinominal"]:
                            lines.append(f"bins = pd.qcut(df[{self._s(base_name)}], q={n}, duplicates='drop')")
                        else:
                            lines.append(f"bins = pd.cut(df[{self._s(base_name)}], bins={n})")
                        lines.append(f"dummies = pd.get_dummies(bins, prefix={self._s(base_name)})")
                        lines.append(f"dummies = dummies.replace({{True: {self._s(t_val)}, 1: {self._s(t_val)}, False: {self._s(f_val)}, 0: {self._s(f_val)}}})")
                    lines.append(f"df = pd.concat([df, dummies], axis=1)")
                    lines.append(f"df.drop(columns=[{self._s(base_name)}], inplace=True)")
                    processed_binning_parents.add(parent_uuid)

        # --- Column selection ---
        if final_col_uuids:
            final_cols = [n.current_name for n in selected_final_nodes]
        else:
            final_cols = [n.current_name for n in active_nodes if n.operation not in ("ROW_DELETE", "ROW_ADD")]
        final_cols_str = ", ".join(self._s(col) for col in final_cols)
        lines.append("")
        lines.append(f"# Select and order final columns")
        lines.append(f"df = df[[{final_cols_str}]]")
        lines.append("df = df.reset_index(drop=True)")
        lines.append("")

        lines.append("df.to_csv(output_path, index=False)")
        lines.append("print(f'Done. Saved to {output_path}')")

        return "\n".join(lines)