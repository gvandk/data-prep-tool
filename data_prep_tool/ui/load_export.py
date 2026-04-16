from pathlib import Path

from PyQt6.QtWidgets import QFileDialog

from data_prep_tool.core.export_service import (
    load_manager_from_csv,
    generate_script_from_manager,
    write_script_file,
    validate_export_input_path,
    export_csv_with_script,
)


def choose_input_csv_path(main_window) -> str:
    """Show CSV open dialog and return selected file path or an empty string."""
    file_path, _ = QFileDialog.getOpenFileName(
        main_window,
        "Open CSV File",
        "",
        "CSV Files (*.csv)",
    )
    return file_path

def choose_script_export_path(main_window) -> str:
    """Show script save dialog and return selected file path or an empty string."""
    path, _ = QFileDialog.getSaveFileName(
        main_window,
        "Save Script",
        "cleaning_script.py",
        "Python (*.py)",
    )
    return path


def choose_output_csv_path(main_window, input_csv_path: str) -> str:
    """Show output CSV save dialog and return selected file path or an empty string."""
    default_name = f"{Path(input_csv_path).stem}_output.csv"
    output_path, _ = QFileDialog.getSaveFileName(
        main_window,
        "Save Output CSV",
        default_name,
        "CSV Files (*.csv)",
    )
    return output_path
