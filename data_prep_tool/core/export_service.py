import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd

from data_prep_tool.core.dataframe_wrapper import DataFrameWrapper
from data_prep_tool.core.script_generator import ScriptGenerator
from data_prep_tool.core.transformation_manager import TransformationManager


def load_manager_from_csv(file_path: str, true_label: str, false_label: str) -> TransformationManager:
    """Load CSV into a fresh transformation manager and apply current binary labels."""
    try:
        new_wrapper = DataFrameWrapper(pd.read_csv(file_path))
    except Exception as e:
        raise RuntimeError(f"Failed to load CSV: {e}") from e

    manager = TransformationManager(new_wrapper)
    manager.update_binary_labels(true_label, false_label)
    return manager


def generate_script_from_manager(manager: TransformationManager) -> str:
    """Generate executable transformation script from current manager state."""
    graph = manager.build_dependency_graph()
    generator = ScriptGenerator(graph, history=manager.history)
    visual_order = manager.df_wrapper.get_all_uuids()
    return generator.generate_script(final_col_uuids=visual_order)


def write_script_file(path: str, script: str):
    """Persist a generated script to disk."""
    with open(path, "w") as script_file:
        script_file.write(script)


def validate_export_input_path(input_csv_path: str) -> str | None:
    """Return user-facing validation error for CSV export source path, or None when valid."""
    if not input_csv_path:
        return "Please load a CSV file first."

    if not Path(input_csv_path).exists():
        return "The original input CSV file was not found."

    return None


def export_csv_with_script(
    script: str,
    input_csv_path: str,
    output_path: str,
    python_executable: str | None = None,
) -> tuple[bool, str | None]:
    """Execute generated transformation script to export output CSV."""
    if python_executable is None:
        python_executable = sys.executable

    temp_script_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as temp_script:
            temp_script.write(script)
            temp_script_path = temp_script.name

        result = subprocess.run(
            [python_executable, temp_script_path, input_csv_path, output_path],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            error_text = (result.stderr or result.stdout or "Unknown script execution error.").strip()
            return False, error_text

        return True, None
    finally:
        if temp_script_path and Path(temp_script_path).exists():
            try:
                Path(temp_script_path).unlink()
            except OSError:
                pass