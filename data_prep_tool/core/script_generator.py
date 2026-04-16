from typing import Dict, List, Set
import pandas as pd
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
                if child.operation in ("ONE_HOT", "BINNING", "BINARY_MERGE", "ROW_FILTER") and not child.is_deleted:
                    transform_relevance_cache[uuid] = True
                    return True
                if has_effective_transform_descendants(child.uuid):
                    transform_relevance_cache[uuid] = True
                    return True

            transform_relevance_cache[uuid] = False
            return False

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

        needs_binary_merge_helper = False
        needs_binary_flag_helper = False
        for node in sorted_steps:
            if needs_binary_merge_helper and needs_binary_flag_helper:
                break

            if node.operation == "BINARY_MERGE":
                source_nodes = [self.graph.get_node(parent_uuid) for parent_uuid in node.parents]
                source_names = [
                    source.current_name
                    for source in source_nodes
                    if source is not None and source.current_name
                ]
                if len(source_names) >= 2:
                    needs_binary_merge_helper = True
                    needs_binary_flag_helper = True
            elif node.operation == "ROW_FILTER":
                target_uuid = node.params.get("target_col_uuid")
                target_node = self.graph.get_node(target_uuid)
                if target_node is not None and node.params.get("binary_flag") is not None:
                    needs_binary_flag_helper = True

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
            "def _print_stdout_table(df):",
            "    # Render a simple readable table when writing to standard output.",
            "    print(df.to_string(index=False, na_rep=''))",
            "",
        ]

        if needs_binary_flag_helper:
            lines.extend(
                [
                    "def _to_binary_flag(value, true_label, false_label):",
                    "    if pd.isna(value):",
                    "        return None",
                    "    if isinstance(value, bool):",
                    "        return value",
                    "    if isinstance(value, (int, float)):",
                    "        if value == 1:",
                    "            return True",
                    "        if value == 0:",
                    "            return False",
                    "    if isinstance(value, str):",
                    "        token = value.strip()",
                    "        lowered = token.casefold()",
                    "        true_norm = str(true_label).strip().casefold()",
                    "        false_norm = str(false_label).strip().casefold()",
                    "        if lowered in {'true', '1', true_norm}:",
                    "            return True",
                    "        if lowered in {'false', '0', false_norm}:",
                    "            return False",
                    "    return None",
                    "",
                ]
            )

        if needs_binary_merge_helper:
            lines.extend(
                [
                    "def _merge_binary_columns(df, source_cols, output_col, true_label, false_label, delete_sources=True):",
                    "    normalized = pd.DataFrame(index=df.index)",
                    "    for col in source_cols:",
                    "        normalized[col] = df[col].map(lambda value: _to_binary_flag(value, true_label, false_label))",
                    "        invalid_values = normalized[col].isna() & df[col].notna()",
                    "        if invalid_values.any():",
                    "            raise ValueError(f\"Column '{col}' is not binary and cannot be merged.\")",
                    "    df[output_col] = normalized.fillna(False).any(axis=1).map({True: true_label, False: false_label})",
                    "    if delete_sources:",
                    "        df.drop(columns=source_cols, inplace=True)",
                    "",
                ]
            )

        lines.extend(
            [
                "if len(sys.argv) > 3:",
                "    print(\"Usage: python script.py [input_csv] [output_csv]\")",
                "    print(\"Use '-' or omit input_csv to read from standard input.\")",
                "    print(\"Use '-' or omit output_csv to write to standard output.\")",
                "    sys.exit(1)",
                "",
                "input_arg = sys.argv[1] if len(sys.argv) >= 2 else '-'",
                "output_arg = sys.argv[2] if len(sys.argv) >= 3 else '-'",
                "",
                "if input_arg != '-' and not os.path.exists(input_arg):",
                "    print(f\"Error: Input file '{input_arg}' not found.\")",
                "    sys.exit(1)",
                "",
            ]
        )

        self._append_guarded_step(
            lines,
            "Load input CSV",
            [
                "if input_arg == '-':",
                "    df = pd.read_csv(sys.stdin)",
                "else:",
                "    df = pd.read_csv(input_arg)",
            ],
            "# Load Data",
        )

        # If no optimized steps remain, just save the loaded CSV.
        if not sorted_steps:
            self._append_guarded_step(
                lines,
                "Write output CSV",
                [
                    "if output_arg == '-':",
                    "    _print_stdout_table(df)",
                    "else:",
                    "    df.to_csv(output_arg, index=False)",
                ],
            )
            lines.extend(
                [
                    "if output_arg != '-':",
                    "    source_desc = input_arg if input_arg != '-' else '<stdin>'",
                    "    print(f\"Successfully processed '{source_desc}' and saved to '{output_arg}'.\")",
                ]
            )
            return "\n".join(lines)

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

            elif node.operation == "ROW_FILTER":
                target_uuid = node.params.get('target_col_uuid')
                target_node = self.graph.get_node(target_uuid)
                if target_node is None:
                    continue

                col_name = target_node.current_name
                value = node.params.get('value')
                binary_flag = node.params.get('binary_flag')
                missing_value_error = f"Value {value!r} is not present in column '{col_name}'."

                if binary_flag is None:
                    if pd.isna(value):
                        filter_lines = [
                            f"mask = df[{self._s(col_name)}].isna()",
                            "if not mask.any():",
                            f"    raise ValueError({self._s(missing_value_error)})",
                            "df = df.loc[~mask].reset_index(drop=True)",
                        ]
                    else:
                        filter_lines = [
                            f"mask = df[{self._s(col_name)}] == {repr(value)}",
                            "if not mask.any():",
                            f"    raise ValueError({self._s(missing_value_error)})",
                            "df = df.loc[~mask].reset_index(drop=True)",
                        ]
                else:
                    true_label = node.params.get('true_label', 'True')
                    false_label = node.params.get('false_label', 'False')
                    filter_lines = [
                        (
                            f"mask = df[{self._s(col_name)}].map(lambda value: "
                            f"_to_binary_flag(value, {self._s(true_label)}, {self._s(false_label)})) == {repr(bool(binary_flag))}"
                        ),
                        "if not mask.any():",
                        f"    raise ValueError({self._s(missing_value_error)})",
                        "df = df.loc[~mask].reset_index(drop=True)",
                    ]

                self._append_guarded_step(
                    lines,
                    f"Filter rows where '{col_name}' equals {value!r}",
                    filter_lines,
                    f"# Filter rows where {col_name} == {value!r}",
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

            elif node.operation == "BINARY_MERGE":
                source_nodes = [self.graph.get_node(parent_uuid) for parent_uuid in node.parents]
                source_names = [source.current_name for source in source_nodes if source is not None and source.current_name]
                if len(source_names) < 2:
                    continue

                true_label = node.params.get('true_label', 'True')
                false_label = node.params.get('false_label', 'False')
                delete_source_columns = bool(node.params.get('delete_source_columns', True))
                source_cols_str = ", ".join(self._s(col) for col in source_names)
                merge_lines = [
                    (
                        f"_merge_binary_columns(df, [{source_cols_str}], {self._s(node.current_name)}, "
                        f"{self._s(true_label)}, {self._s(false_label)}, delete_sources={repr(delete_source_columns)})"
                    ),
                ]
                source_names_text = ", ".join(source_names)

                self._append_guarded_step(
                    lines,
                    f"Merge binary columns [{source_names_text}] into '{node.current_name}'",
                    merge_lines,
                    f"# Merge binary columns [{source_names_text}] into: {node.current_name}",
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
                if node and not node.is_deleted and node.operation not in ("ROW_DELETE", "ROW_FILTER", "ROW_ADD", "CELL_EDIT"):
                    selected_final_nodes.append(node)

        # Final column order and selection
        if final_col_uuids:
            final_cols = [n.current_name for n in selected_final_nodes if n.current_name]
        else:
            final_cols = [
                n.current_name
                for n in active_nodes
                if n.operation not in ("ROW_DELETE", "ROW_FILTER", "ROW_ADD", "CELL_EDIT") and n.current_name
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
            [
                "if output_arg == '-':",
                "    _print_stdout_table(df)",
                "else:",
                "    df.to_csv(output_arg, index=False)",
            ],
        )
        lines.extend(
            [
                "if output_arg != '-':",
                "    source_desc = input_arg if input_arg != '-' else '<stdin>'",
                "    print(f\"Successfully processed '{source_desc}' and saved to '{output_arg}'.\")",
            ]
        )

        return "\n".join(lines)