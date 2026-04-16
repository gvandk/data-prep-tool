from typing import Dict, List, Set
from .dependency_graph import DependencyGraph, GraphNode

class ScriptGenerator:
    def __init__(self, graph: DependencyGraph, history: list = None):
        self.graph = graph
        self.history = history or []

    def _s(self, value) -> str:
        return repr(str(value))

    def _append_guarded_step(self, lines: List[str], operation: str, body_lines: List[str], comment: str = None) -> None:
        """Append a guarded execution block to the generated script.

        Each step reports a readable operation label if runtime execution fails.
        """
        lines.append("")
        if comment:
            lines.append(comment)
        lines.append("try:")
        for body_line in body_lines:
            lines.append(f"    {body_line}")
        lines.append("except Exception as exc:")
        lines.append(f"    _handle_step_error({self._s(operation)}, exc)")

    def generate_script(self, final_col_uuids: List[str] = None) -> str:
        """Generate a Python script that reproduces the transformations represented in the dependency graph."""
        active_nodes = self.graph.get_active_nodes()
        children_by_parent: Dict[str, List[GraphNode]] = {}
        for node in self.graph.nodes.values():
            for parent_uuid in node.parents:
                children_by_parent.setdefault(parent_uuid, []).append(node)

        transform_relevance_cache: Dict[str, bool] = {}

        def has_effective_transform_descendants(uuid: str) -> bool:
            '''Check if a node has any non-deleted transform descendants that would require it to be included in the script.'''
            if uuid in transform_relevance_cache:
                return transform_relevance_cache[uuid]

            for child in children_by_parent.get(uuid, []):
                # Keep parent-side edits/renames only if a transform branch still has live outputs.
                if child.operation in ("ONE_HOT", "BINNING") and not child.is_deleted:
                    transform_relevance_cache[uuid] = True
                    return True
                if has_effective_transform_descendants(child.uuid):
                    transform_relevance_cache[uuid] = True
                    return True

            transform_relevance_cache[uuid] = False
            return False

        lines = [
            "import pandas as pd",
            "import sys",
            "import os",
            "",
            "def _format_error_reason(exc):",
            "    if isinstance(exc, KeyError):",
            "        missing_key = str(exc).strip().strip(\"'\").strip('\"')",
            "        if missing_key:",
            "            return f\"A required column or key named '{missing_key}' was not found. Check that the input CSV contains it and that earlier steps did not rename or remove it.\"",
            "        return \"A required column or key was not found. Check that the input CSV contains all expected columns.\"",
            "",
            "    if isinstance(exc, IndexError):",
            "        return \"A row index used by one of the operations is out of range for the current data.\"",
            "",
            "    if isinstance(exc, pd.errors.EmptyDataError):",
            "        return \"The input CSV appears to be empty. Provide a CSV file with headers and data rows.\"",
            "",
            "    if isinstance(exc, pd.errors.ParserError):",
            "        return \"The input CSV could not be parsed. Verify delimiters, quoting, and text encoding.\"",
            "",
            "    if isinstance(exc, PermissionError):",
            "        return \"The script does not have permission to read or write one of the files. Close open file handles and try again.\"",
            "",
            "    message = str(exc).strip()",
            "    if isinstance(exc, ValueError):",
            "        if message:",
            "            return f\"The data could not be transformed because of an invalid value or format: {message}\"",
            "        return \"The data could not be transformed because of an invalid value or format.\"",
            "",
            "    if message:",
            "        return f\"Unexpected error ({exc.__class__.__name__}): {message}. Full error: {repr(exc)}\"",
            "    return f\"Unexpected error ({exc.__class__.__name__}). Full error: {repr(exc)}\"",
            "",
            "def _handle_step_error(operation, exc):",
            "    print(f\"Error: Script failed during step: {operation}.\")",
            "    print(f\"Reason: {_format_error_reason(exc)}\")",
            "    sys.exit(1)",
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
            ""
        ]

        self._append_guarded_step(
            lines,
            "Load input CSV",
            ["df = pd.read_csv(input_path)"],
            "# Load Data",
        )

        # In case no edits happend, just save the csv
        if not active_nodes:
            self._append_guarded_step(
                lines,
                "Write output CSV",
                ["df.to_csv(output_path, index=False)"],
            )
            lines.append("print(f\"Successfully processed '{input_path}' and saved to '{output_path}'.\")")
            return "\n".join(lines)

        # Build sorted steps via dependency trace
        sorted_steps: List[GraphNode] = []
        visited: Set[str] = set()

        def trace(uuid: str):
            """Depth-first trace to ensure parents come before children in the script."""
            if uuid in visited: return
            if uuid not in self.graph.nodes: return
            node = self.graph.nodes[uuid]
            visited.add(uuid)
            for parent_uuid in node.parents:
                trace(parent_uuid)
            sorted_steps.append(node)

        for node in active_nodes:
            trace(node.uuid)

        def should_skip_node(node: GraphNode) -> bool:
            '''Determine if a node can be safely skipped because it is deleted and has no effective transform descendants.'''
            if node.operation == "LOAD":
                return node.is_deleted and not has_effective_transform_descendants(node.uuid)

            if node.operation == "CELL_EDIT":
                target_uuid = node.params.get('target_col_uuid')
                target_node = self.graph.get_node(target_uuid)
                if target_node is None:
                    return True
                return target_node.is_deleted and not has_effective_transform_descendants(target_uuid)

            return False

        # Remove nodes that are guaranteed to produce no script lines before any further optimization.
        filtered_steps = [node for node in sorted_steps if not should_skip_node(node)]

        # Coalesce contiguous CELL_EDIT blocks by keeping only the last edit per cell.
        # This removes redundant revisits
        optimized_steps: List[GraphNode] = []
        pending_cell_block: List[GraphNode] = []

        def flush_cell_block() -> None:
            if not pending_cell_block:
                return

            last_by_cell: Dict[tuple, GraphNode] = {
                (n.params.get('target_col_uuid'), n.params.get('row_index')): n
                for n in pending_cell_block
            }
            for n in pending_cell_block:
                key = (n.params.get('target_col_uuid'), n.params.get('row_index'))
                if last_by_cell[key] is n:
                    optimized_steps.append(n)
            pending_cell_block.clear()

        for node in filtered_steps:
            if node.operation == "CELL_EDIT":
                pending_cell_block.append(node)
            else:
                flush_cell_block()
                optimized_steps.append(node)
        flush_cell_block()

        sorted_steps = optimized_steps

        processed_binning_parents: Set[str] = set()
        processed_one_hot_parents: Set[str] = set()

        for node in sorted_steps:
            if node.operation == "LOAD":
                src = node.params.get('source_name')
                if src and src != node.current_name:
                    self._append_guarded_step(
                        lines,
                        f"Rename column: {src} to {node.current_name}",
                        [f"df.rename(columns={{{self._s(src)}: {self._s(node.current_name)}}}, inplace=True)"],
                        f"# Rename column: {src} to {node.current_name}",
                    )
            
            elif node.operation == "CELL_EDIT":
                target_uuid = node.params.get('target_col_uuid')
                target_node = self.graph.get_node(target_uuid)
                if target_node is None:
                    continue
                col_name = target_node.current_name
                row = node.params.get('row_index')
                val = node.params.get('value')
                self._append_guarded_step(
                    lines,
                    f"Edit cell in column '{col_name}' at row {row}",
                    [f"df.at[{row}, {self._s(col_name)}] = {repr(val)}"],
                    f"# Edit cell: {col_name} at row {row} to {repr(val)}",
                )
            
            elif node.operation == "ROW_DELETE":
                    row_index = node.params.get('row_index')
                    self._append_guarded_step(
                        lines,
                        f"Delete row at index {row_index}",
                        [f"df = df.drop(index={row_index}).reset_index(drop=True)"],
                        f"# Delete row at index {row_index}",
                    )

            elif node.operation == "ROW_ADD":
                default = node.params.get('default_value', '')
                self._append_guarded_step(
                    lines,
                    "Add row",
                    [f"df = pd.concat([df, pd.DataFrame([{{col: {repr(default)} for col in df.columns}}])], ignore_index=True).reset_index(drop=True)"],
                    f"# Add new row with {repr(default)}",
                )
                
            elif node.operation == "COL_ADD":
                default = node.params.get('default_value', '')
                self._append_guarded_step(
                    lines,
                    f"Add column '{node.current_name}'",
                    [f"df[{self._s(node.current_name)}] = {repr(default)}"],
                    f"# Add column: {node.current_name} with default value {repr(default)}",
                )

            elif node.operation == "ONE_HOT":
                parent_uuid = node.parents[0]
                if parent_uuid not in processed_one_hot_parents:
                    parent_node = self.graph.get_node(parent_uuid)
                    if parent_node is None:
                        continue
                    parent_name = parent_node.current_name
                    prefix = node.params.get('prefix', parent_name)
                    if prefix == "...": prefix = parent_name
                    t_val = node.params.get('true_label', 'True')
                    f_val = node.params.get('false_label', 'False')
                    one_hot_lines = [
                        f"dummies = pd.get_dummies(pd.Categorical(df[{self._s(parent_name)}], categories=list(pd.unique(df[{self._s(parent_name)}]))), prefix={self._s(prefix)})",
                        f"dummies = dummies.replace({{True: {self._s(t_val)}, 1: {self._s(t_val)}, False: {self._s(f_val)}, 0: {self._s(f_val)}}})",
                        "df = pd.concat([df, dummies], axis=1)",
                    ]
                    self._append_guarded_step(
                        lines,
                        f"One-hot encode column '{parent_name}'",
                        one_hot_lines,
                        f"# One-Hot Encode: {parent_name}",
                    )
                    processed_one_hot_parents.add(parent_uuid)
                src = node.params.get('source_name')
                if src and src != node.current_name:
                    self._append_guarded_step(
                        lines,
                        f"Rename one-hot column: {src} to {node.current_name}",
                        [f"df.rename(columns={{{self._s(src)}: {self._s(node.current_name)}}}, inplace=True)"],
                        f"# Rename one-hot column: {src} to {node.current_name}",
                    )

            elif node.operation == "BINNING":
                parent_uuid = node.parents[0]
                if parent_uuid not in processed_binning_parents:
                    parent_node = self.graph.get_node(parent_uuid)
                    if parent_node is None:
                        continue
                    base_name = node.params.get("pre_binning_name") or parent_node.current_name
                    
                    strategy = node.params.get("strategy")
                    n = node.params.get("n_bins")
                    cutoffs = node.params.get("cutoffs")
                    t_val = node.params.get('true_label', 'True')
                    f_val = node.params.get('false_label', 'False')

                    binning_lines = [
                        f"numeric_vals = pd.to_numeric(df[{self._s(base_name)}], errors='coerce')"
                    ]
                    
                    if strategy == "Ordinal":
                         binning_lines.append(f"binned_codes = pd.cut(numeric_vals, bins={n}, labels=False)")
                         binning_lines.append("dummies = pd.DataFrame(index=df.index)")
                         binning_lines.append(f"for i in range({n}):")
                         col_expr = f"{{'{base_name}'}}_{{i}}" # f-string inside f-string needs escaping
                         binning_lines.append(f"    dummies[f{self._s(col_expr)}] = (binned_codes >= i)")
                    elif strategy == "Custom" and cutoffs:
                        binning_lines.append(f"binned = pd.cut(numeric_vals, bins={cutoffs})")
                        binning_lines.append(f"dummies = pd.get_dummies(binned, prefix={self._s(base_name)})")
                    elif strategy in ["Equal Frequency", "Equinominal"]:
                        binning_lines.append(f"binned = pd.qcut(numeric_vals, q={n}, duplicates='drop')")
                        binning_lines.append(f"dummies = pd.get_dummies(binned, prefix={self._s(base_name)})")
                    else: # Equal Width as default
                        binning_lines.append(f"binned = pd.cut(numeric_vals, bins={n})")
                        binning_lines.append(f"dummies = pd.get_dummies(binned, prefix={self._s(base_name)})")
                    
                    binning_lines.append(f"dummies = dummies.replace({{True: {self._s(t_val)}, 1: {self._s(t_val)}, False: {self._s(f_val)}, 0: {self._s(f_val)}}})")
                    binning_lines.append("df = pd.concat([df, dummies], axis=1)")
                    binning_lines.append(f"df.drop(columns=[{self._s(base_name)}], inplace=True)")

                    self._append_guarded_step(
                        lines,
                        f"Apply binning on column '{base_name}' using strategy '{strategy}'",
                        binning_lines,
                        f"# Binning: {base_name} ({strategy})",
                    )
                    processed_binning_parents.add(parent_uuid)
                
                src = node.params.get('source_name')
                if src and src != node.current_name:
                    self._append_guarded_step(
                        lines,
                        f"Rename binned column: {src} to {node.current_name}",
                        [f"df.rename(columns={{{self._s(src)}: {self._s(node.current_name)}}}, inplace=True)"],
                        f"# Rename binned column: {src} to {node.current_name}",
                    )
                

        # determine final columns for final selection and ordering
        selected_final_nodes: List[GraphNode] = []
        if final_col_uuids:
            for uuid in final_col_uuids:
                node = self.graph.get_node(uuid)
                # Only include if the node is active and not a row/cell operation, since they do not have a column output to select
                if node and not node.is_deleted and node.operation not in ("ROW_DELETE", "ROW_ADD", "CELL_EDIT"):
                    selected_final_nodes.append(node)

        # Final column order and selection
        if final_col_uuids:
            final_cols = [n.current_name for n in selected_final_nodes if n.current_name]
        else:
            final_cols = [
                n.current_name
                for n in active_nodes
                if n.operation not in ("ROW_DELETE", "ROW_ADD", "CELL_EDIT") and n.current_name
            ]
        final_cols_str = ", ".join(self._s(col) for col in final_cols)
        self._append_guarded_step(
            lines,
            "Select and order final columns",
            [
                f"df = df[[{final_cols_str}]]",
                "df = df.reset_index(drop=True)",
            ],
            "# Select and order final columns",
        )

        self._append_guarded_step(
            lines,
            "Write output CSV",
            ["df.to_csv(output_path, index=False)"],
        )
        lines.append("print(f\"Successfully processed '{input_path}' and saved to '{output_path}'.\")")

        return "\n".join(lines)