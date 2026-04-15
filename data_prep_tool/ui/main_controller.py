from PyQt6.QtWidgets import QFileDialog, QMessageBox, QApplication
import pandas as pd
import subprocess
import sys
import tempfile
from pathlib import Path

from data_prep_tool.models.table_model import DataFrameModel
from data_prep_tool.core.transformation_manager import TransformationManager
from data_prep_tool.core.script_generator import ScriptGenerator
from data_prep_tool.transformation.col_reorder_transformation import ColumnReorderTransformation
from data_prep_tool.transformation.binning_transformation import BinningTransformation
from data_prep_tool.transformation.one_hot_encode import oneHotEncodeTransformation
from data_prep_tool.core.data_loader import load_csv



class MainController:
    """Controller for the main application window, handling user interactions and coordinating between the UI and the TransformationManager."""
    ONE_HOT_WARN_UNIQUE_THRESHOLD = 2000
    ONE_HOT_WARN_MATRIX_CELLS_THRESHOLD = 10_000_000
    ONE_HOT_BLOCK_UNIQUE_THRESHOLD = 5000
    ONE_HOT_BLOCK_MATRIX_CELLS_THRESHOLD = 50_000_000

    def __init__(self, main_window, transformation_manager):
        self.main_window = main_window
        self.manager = transformation_manager
        self._active_row_index = -1
        self.current_input_csv_path = None
        
        self.model = DataFrameModel(self.manager.df_wrapper)
        self.main_window.table_view.setModel(self.model)
        # Connect UI signals to controller methods
        self.main_window.action_load.triggered.connect(self.open_csv)
        self.main_window.csv_dropped.connect(self.load_csv_from_path)
        self.main_window.action_exit.triggered.connect(self.main_window.close)
        self.main_window.action_export.triggered.connect(self.export_script)
        self.main_window.action_export_csv.triggered.connect(self.export_csv)
        self.main_window.action_undo.triggered.connect(self.undo)
        self.main_window.action_redo.triggered.connect(self.redo)
        self.main_window.action_delete.triggered.connect(self.on_delete_pressed)
        # Connect table interactions
        self.main_window.table_view.horizontalHeader().sectionClicked.connect(self.on_header_clicked)
        self.main_window.table_view.verticalHeader().sectionClicked.connect(self.on_row_clicked)
        self.main_window.table_view.clicked.connect(self.on_cell_clicked)
        self.main_window.table_view.column_reorder_requested.connect(self.on_column_reorder_drag)
        self.main_window.table_view.delete_pressed.connect(self.on_delete_pressed)
        # Connect general options panel signals
        self.main_window.general_options.binary_values_changed.connect(self.on_binary_values_changed)
        self.main_window.general_options.view_settings_changed.connect(self.on_view_settings_changed)
        self.main_window.general_options.add_row_requested.connect(self.on_add_row)
        self.main_window.general_options.add_col_requested.connect(self.on_add_col)
        # Connect column options panel signals
        col_panel = self.main_window.column_options
        col_panel.column_rename_request.connect(self.on_column_rename)
        col_panel.encoder_options.column_encoding_request.connect(self.on_encoding_change)
        col_panel.encoder_options.column_binning_request.connect(self.on_binning_change)
        col_panel.encoder_options.child_rename_request.connect(self.on_column_rename)
        col_panel.column_reorder.column_reorder_request.connect(self.on_manual_reorder)
        col_panel.delete_col_requested.connect(self.on_delete_col)
        col_panel.close_request.connect(self.on_panel_close)
        # Connect cell options panel signals
        cell_panel = self.main_window.cell_options
        cell_panel.cell_edit.cell_change_request.connect(self.on_cell_edit)
        cell_panel.column_rename.column_rename_request.connect(self.on_column_rename)
        cell_panel.close_request.connect(self.on_panel_close)
        # Connect row options panel signals
        self.main_window.row_options.delete_row_requested.connect(self.on_delete_row)
        self.main_window.row_options.close_request.connect(self.on_panel_close)

        self.refresh_view()

    def _set_type(self, input):
        """Helper method to convert string input into appropriate type (int, float, bool, or str)."""
        try:
            return int(input)
        except ValueError:
            pass
        try:
            return float(input)
        except ValueError:
            pass
        if input.lower() == "true" :
            return True
        elif input.lower() == "false":
            return False
        return input

    def _confirm_one_hot_encoding(self, uuid: str) -> bool:
        """Estimate one-hot size and ask for confirmation (or block) for very large transformations."""
        series = self.manager.df_wrapper.get_col_data_by_uuid(uuid)
        if series is None:
            return False

        row_count = len(series)
        unique_count = int(series.nunique(dropna=False))
        estimated_matrix_cells = row_count * unique_count

        if (
            unique_count > self.ONE_HOT_BLOCK_UNIQUE_THRESHOLD
            or estimated_matrix_cells > self.ONE_HOT_BLOCK_MATRIX_CELLS_THRESHOLD
        ):
            QMessageBox.warning(
                self.main_window,
                "Encoding Too Large",
                (
                    "One-Hot encoding was blocked because the estimated output is too large for interactive use.\n\n"
                    f"Rows: {row_count:,}\n"
                    f"Unique values: {unique_count:,}\n"
                    f"Estimated binary cells: {estimated_matrix_cells:,}\n\n"
                    "Reduce cardinality first (e.g. cell editing/grouping) and try again."
                ),
            )
            return False

        if (
            unique_count > self.ONE_HOT_WARN_UNIQUE_THRESHOLD
            or estimated_matrix_cells > self.ONE_HOT_WARN_MATRIX_CELLS_THRESHOLD
        ):
            answer = QMessageBox.question(
                self.main_window,
                "Large One-Hot Operation",
                (
                    "This one-hot transformation may be very slow and can make the app unresponsive.\n\n"
                    f"Rows: {row_count:,}\n"
                    f"Unique values: {unique_count:,}\n"
                    f"Estimated binary cells: {estimated_matrix_cells:,}\n\n"
                    "Do you want to continue?"
                ),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            return answer == QMessageBox.StandardButton.Yes

        return True

    def _supports_binning(self, series: pd.Series) -> bool:
        """Return True if a series can be interpreted as numeric for binning."""
        if series is None:
            return False

        sample = series.dropna()
        if sample.empty:
            return True

        if len(sample) > 100:
            sample = sample.head(100)

        try:
            pd.to_numeric(sample, errors='raise')
            return True
        except (ValueError, TypeError):
            return False

    def _update_menu_action_states(self):
        """Enable only the menu actions that are currently possible."""
        self.main_window.action_undo.setEnabled(bool(self.manager.history))
        self.main_window.action_redo.setEnabled(bool(self.manager.redo))

    def on_panel_close(self):
        self.main_window.set_panel("general")
        self.main_window.table_view.clearSelection()
        self._active_row_index = -1

    def on_binary_values_changed(self, true_val, false_val):
        try:
            self.manager.update_binary_labels(true_val, false_val)
            self.refresh_view()
        except Exception:
            QApplication.beep()

    def on_view_settings_changed(self, max_rows, decimal_places):
        self.model.set_view_settings(max_rows, decimal_places)
        self.refresh_view()

    def open_csv(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self.main_window, "Open CSV File", "", "CSV Files (*.csv)"
        )
        if file_path:
            self.load_csv_from_path(file_path)

    def load_csv_from_path(self, file_path: str):
        try:
            new_wrapper = load_csv(file_path)
            self.manager = TransformationManager(new_wrapper)

            # Preserve currently configured binary labels across loaded datasets.
            true_label = self.main_window.general_options.true_input.text()
            false_label = self.main_window.general_options.false_input.text()
            self.manager.update_binary_labels(true_label, false_label)

            self.current_input_csv_path = file_path
            self.model.update_wrapper(self.manager.df_wrapper)
            self.main_window.set_panel("general")
            self.refresh_view()
        except Exception:
            QMessageBox.warning(self.main_window, "Load Error", "Failed to load CSV file.\nPlease check the file format.")

    def export_script(self):
        """Generates a Python script representing the current transformations and allows the user to save it, 
with error handling for generation issues."""
        try:
            graph = self.manager.build_dependency_graph()
            generator = ScriptGenerator(graph, history=self.manager.history)
            visual_order = self.manager.df_wrapper.get_all_uuids()
            script = generator.generate_script(final_col_uuids=visual_order)
            
            path, _ = QFileDialog.getSaveFileName(self.main_window, "Save Script", "cleaning_script.py", "Python (*.py)")
            if path:
                with open(path, "w") as f: f.write(script)
                QMessageBox.information(self.main_window, "Success", f"Script exported to:\n{path}")
        except Exception:
            QMessageBox.warning(self.main_window, "Export Error", "Failed to generate script.\nPlease ensure all transformations are valid.")

    def export_csv(self):
        """Generates a Python script to apply transformations and runs it to export the current DataFrame state to a new CSV file, 
with error handling for generation and execution issues."""
        if not self.current_input_csv_path:
            QMessageBox.warning(self.main_window, "Export CSV Error", "Please load a CSV file first.")
            return

        if not Path(self.current_input_csv_path).exists():
            QMessageBox.warning(self.main_window, "Export CSV Error", "The original input CSV file was not found.")
            return

        default_name = f"{Path(self.current_input_csv_path).stem}_output.csv"
        output_path, _ = QFileDialog.getSaveFileName(
            self.main_window,
            "Save Output CSV",
            default_name,
            "CSV Files (*.csv)"
        )

        if not output_path:
            return

        temp_script_path = None
        try:
            graph = self.manager.build_dependency_graph()
            generator = ScriptGenerator(graph, history=self.manager.history)
            visual_order = self.manager.df_wrapper.get_all_uuids()
            script = generator.generate_script(final_col_uuids=visual_order)

            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as temp_script:
                temp_script.write(script)
                temp_script_path = temp_script.name

            result = subprocess.run(
                [sys.executable, temp_script_path, self.current_input_csv_path, output_path],
                capture_output=True,
                text=True,
                check=False
            )

            if result.returncode != 0:
                error_text = (result.stderr or result.stdout or "Unknown script execution error.").strip()
                QMessageBox.warning(
                    self.main_window,
                    "Export CSV Error",
                    f"Failed to export CSV.\n\n{error_text}"
                )
                return

            QMessageBox.information(self.main_window, "Success", f"CSV exported to:\n{output_path}")
        except Exception:
            QMessageBox.warning(self.main_window, "Export CSV Error", "Failed to generate or run export script.")
        finally:
            if temp_script_path and Path(temp_script_path).exists():
                try:
                    Path(temp_script_path).unlink()
                except OSError:
                    pass

    def _calculate_stats(self, series: pd.Series) -> str:
        """Helper method to calculate and format statistics for a given pandas Series, handling both numeric and categorical data,
 as well as empty or null series."""
        if series is None or series.empty: return "No data."
        total = len(series)
        nulls = series.isnull().sum()
        stats = f"Total Rows: {total}\nMissing: {nulls}\n"

        binary_counts = self._get_binary_counts(series)
        if binary_counts is not None:
            true_count, false_count = binary_counts
            stats += (
                "Type: Binary\n"
                f"{self.manager.binary_true}: {true_count}\n"
                f"{self.manager.binary_false}: {false_count}"
            )
            return stats

        if pd.api.types.is_numeric_dtype(series):
            try:
                d = series.describe()
                stats += f"Type: Numeric\nMean: {d['mean']:.4f}\nMin: {d['min']}\nMax: {d['max']}"
            except: stats += "Error calc stats"
        else:
            try:
                stats += f"Type: Categorical\nUnique: {series.nunique()}"
            except: stats += "Error calc stats"
        return stats

    def _get_binary_counts(self, series: pd.Series):
        """Return (true_count, false_count) when a series is binary-like, else None."""
        if series is None:
            return None

        true_label = self.manager.binary_true
        false_label = self.manager.binary_false

        true_count = 0
        false_count = 0
        saw_binary_value = False

        for value in series.dropna():
            if isinstance(value, bool):
                saw_binary_value = True
                if value:
                    true_count += 1
                else:
                    false_count += 1
                continue

            if isinstance(value, (int, float)) and value in (0, 1):
                saw_binary_value = True
                if value == 1:
                    true_count += 1
                else:
                    false_count += 1
                continue

            if isinstance(value, str):
                token = value.strip()
                lowered = token.casefold()

                if lowered in ("true", "1") or token == true_label:
                    saw_binary_value = True
                    true_count += 1
                    continue

                if lowered in ("false", "0") or token == false_label:
                    saw_binary_value = True
                    false_count += 1
                    continue

            return None

        if not saw_binary_value:
            return None
        return true_count, false_count

    def _build_child_column_stats(self, parent_name: str, parent_series: pd.Series, child_name: str, child_series: pd.Series) -> str:
        """Build combined stats text for expanded child columns (parent context + child binary details)."""
        parent_label = parent_name or "Parent"
        child_label = child_name or "Expanded Column"

        parent_stats = self._calculate_stats(parent_series)

        binary_counts = self._get_binary_counts(child_series)
        if binary_counts is not None:
            true_count, false_count = binary_counts
            child_stats = (
                "Type: Binary\n"
                f"{self.manager.binary_true}: {true_count}\n"
                f"{self.manager.binary_false}: {false_count}"
            )
        else:
            child_stats = self._calculate_stats(child_series)

        return (
            f"Parent Column ({parent_label})\n"
            f"{parent_stats}\n\n"
            f"Expanded Column ({child_label})\n"
            f"{child_stats}"
        )

    def on_header_clicked(self, logical_index):
        """Handle clicks on column headers to show column options, including encoding and binning settings, and update stats display."""
        uuid = self.model.get_column_uuid(logical_index)
        if not uuid: return

        self.main_window.set_panel("column")
        wrapper = self.manager.df_wrapper
        col_name = wrapper.get_col_name_by_uuid(uuid)
        
        self.main_window.column_options.column_rename.set_current_column(uuid, col_name)
        self.main_window.column_options.column_rename.uuid = uuid
        self.main_window.column_options.column_reorder.uuid = uuid
        self.main_window.column_options.column_reorder.set_current_index(uuid, str(logical_index))

        is_child = wrapper.uuid_manager.is_child(uuid)
        data_min = 0.0
        data_max = 100.0
        selected_series = wrapper.get_col_data_by_uuid(uuid)
        parent_series = selected_series

        if selected_series is not None and pd.api.types.is_numeric_dtype(selected_series):
             data_min = float(selected_series.min())
             data_max = float(selected_series.max())

        if is_child:
             parent_uuid = wrapper.get_parent_uuid(uuid)
             for trans in reversed(self.manager.history):
                 if getattr(trans, 'col_uuid', None) == parent_uuid:
                     if hasattr(trans, 'values') and trans.values is not None:
                         parent_series = trans.values
                         if pd.api.types.is_numeric_dtype(parent_series):
                             data_min = float(parent_series.min())
                             data_max = float(parent_series.max())
                     break

        if is_child:
            parent_name_for_stats = wrapper.uuid_manager.get_parent_name(uuid)
            stats_text = self._build_child_column_stats(parent_name_for_stats, parent_series, col_name, selected_series)
        else:
            stats_text = self._calculate_stats(selected_series)

        self.main_window.column_options.set_stats(stats_text)

        encoder_widget = self.main_window.column_options.encoder_options
        series_for_binning = parent_series if is_child else selected_series
        can_binning = self._supports_binning(series_for_binning)
        
        if is_child:
            parent_uuid = wrapper.get_parent_uuid(uuid)
            parent_name = wrapper.uuid_manager.get_parent_name(uuid) 
            children_names = {c: wrapper.get_col_name_by_uuid(c) for c in wrapper.uuid_manager.get_children_uuids(parent_uuid)}
            
            strategy = "One-Hot"
            n_bins = 5
            for trans in reversed(self.manager.history):
                if hasattr(trans, 'col_uuid') and trans.col_uuid == parent_uuid:
                    if isinstance(trans, BinningTransformation):
                        strategy = trans.strategy
                        n_bins = trans.n_bins
                        break
                    elif isinstance(trans, oneHotEncodeTransformation):
                        strategy = "One-Hot"
                        break
            
            encoder_widget.set_current_column(
                parent_uuid,
                strategy,
                children_names,
                n_bins,
                parent_name,
                data_min,
                data_max,
                can_one_hot=True,
                can_binning=can_binning,
            )
        else:
            encoder_widget.set_current_column(
                uuid,
                "None",
                min_val=data_min,
                max_val=data_max,
                can_one_hot=True,
                can_binning=can_binning,
            )

        self.main_window.column_options.set_current_uuid(uuid)

    def on_binning_change(self, uuid, strategy, n_bins, cutoffs):
        """Handle changes in binning strategy for a column, including validation of parameters and ensuring the column is numeric 
before applying binning transformations."""
        if strategy == "Custom":
            if not cutoffs: return
            if any(cutoffs[i] >= cutoffs[i+1] for i in range(len(cutoffs)-1)):
                QMessageBox.warning(self.main_window, "Invalid Cutoffs", "Values must be strictly increasing.")
                return

        try:
            if self.manager.history:
                last_trans = self.manager.history[-1]
                if isinstance(last_trans, (BinningTransformation, oneHotEncodeTransformation)):
                    if last_trans.col_uuid == uuid:
                        self.manager.undo_transformation()
            
            all_uuids = self.manager.df_wrapper.get_all_uuids()
            if uuid in all_uuids:
                col_index = all_uuids.index(uuid)
                
                # Validate that the column is numeric before binning
                target_series = self.manager.df_wrapper.get_col_data_by_uuid(uuid)
                try:
                     sample = target_series.dropna()
                     if len(sample) > 100: sample = sample.head(100)
                     if not sample.empty:
                         pd.to_numeric(sample, errors='raise')
                except ValueError:
                     QMessageBox.warning(self.main_window, "Binning Error", "Selected column contains non-numeric data.\nBinning can only be applied to numeric columns.")
                     return

                self.manager.add_binning(col_index, strategy, n_bins, cutoffs)
                self.refresh_view()
                children = self.manager.df_wrapper.get_children_uuids(uuid)
                if children and children[0] in self.manager.df_wrapper.get_all_uuids():
                    self.on_header_clicked(self.manager.df_wrapper.get_all_uuids().index(children[0]))
        except ValueError as e:
            QMessageBox.warning(self.main_window, "Binning Error", f"Invalid binning parameters:\n{str(e)}")
        except Exception:
            QApplication.beep()

    def on_encoding_change(self, uuid, encoding):
        """Handle changes in encoding strategy for a column, applying or undoing one-hot encoding transformations as needed, 
with error handling for invalid operations."""
        try:
            if self.manager.history:
                last_trans = self.manager.history[-1]
                if isinstance(last_trans, (BinningTransformation, oneHotEncodeTransformation)):
                    if last_trans.col_uuid == uuid:
                        self.manager.undo_transformation()
                        self.refresh_view()
                        if encoding == "None":
                            all_uuids = self.manager.df_wrapper.get_all_uuids()
                            if uuid in all_uuids:
                                self.on_header_clicked(all_uuids.index(uuid))
                            return

            if encoding == "One-Hot":
                all_uuids = self.manager.df_wrapper.get_all_uuids()
                if uuid in all_uuids:
                    col_index = all_uuids.index(uuid)

                    if not self._confirm_one_hot_encoding(uuid):
                        return
                    
                    self.manager.add_onehot(col_index)
                    self.refresh_view()
                    children = self.manager.df_wrapper.get_children_uuids(uuid)
                    if children and children[0] in self.manager.df_wrapper.get_all_uuids():
                        self.on_header_clicked(self.manager.df_wrapper.get_all_uuids().index(children[0]))
        except ValueError as e:
            QMessageBox.warning(self.main_window, "Encoding Error", str(e))
        except Exception:
            QApplication.beep()

    def on_row_clicked(self, logical_index):
        self.main_window.set_panel("row")
        self.main_window.row_options.set_row(logical_index)

    def on_cell_clicked(self, index):
        if not index.isValid(): return
        self.main_window.set_panel("cell")
        self._active_row_index = index.row()
        uuid = self.model.get_column_uuid(index.column())
        val = self.manager.df_wrapper.get_cell_value(uuid, self._active_row_index)
        col_name = self.manager.df_wrapper.get_col_name_by_uuid(uuid)
        self.main_window.cell_options.cell_edit.set_current_cell(uuid, str(val))
        self.main_window.cell_options.cell_edit.uuid = uuid
        self.main_window.cell_options.column_rename.set_current_column(uuid, col_name)
        self.main_window.cell_options.column_rename.uuid = uuid

    def on_column_rename(self, uuid, new_name):
        all_uuids = self.manager.df_wrapper.get_all_uuids()
        
        self.model.set_error_columns([])

        if uuid in all_uuids:
            try:
                self.manager.add_rename(uuid, new_name)
                self.refresh_view()
            except ValueError:
                # Beep and highlight duplicates
                QApplication.beep()
                
                error_indices = [all_uuids.index(uuid)]
                # Find index of existing column with same name
                try:
                    df_cols = self.manager.df_wrapper.df.columns
                    for i, col in enumerate(df_cols):
                        if col == new_name:
                            error_indices.append(i)
                except Exception:
                    pass
                
                self.model.set_error_columns(error_indices)
            except Exception:
                QApplication.beep()

    def on_cell_edit(self, uuid, new_value):
        if self._active_row_index != -1:
            try:
                self.manager.add_cell_edit(self._active_row_index, uuid, self._set_type(new_value))
                self.refresh_view()
            except Exception:
                QApplication.beep()

    def on_column_reorder_drag(self, new_uuid_order):
        try:
            self._apply_reorder(new_uuid_order)
        except Exception:
            QApplication.beep()

    def on_manual_reorder(self, uuid, new_index_str):
        try:
            new_index = int(new_index_str)
            all_uuids = self.manager.df_wrapper.get_all_uuids()
            if uuid in all_uuids:
                current_uuids = list(all_uuids)
                current_uuids.remove(uuid)
                new_index = max(0, min(new_index, len(current_uuids)))
                current_uuids.insert(new_index, uuid)
                self._apply_reorder(current_uuids)
        except ValueError:
            QApplication.beep()

    def on_add_row(self, default_value):
        try:
            self.manager.add_row_add(self._set_type(default_value))
            self.refresh_view()
        except Exception:
            QApplication.beep()

    def on_add_col(self, default_value):
        col_name = self.main_window.general_options.new_col_name_input.text().strip()
        if not col_name:
            QMessageBox.warning(self.main_window, "Input Error", "Please provide a name for the new column.")
            return
        try:
            self.manager.add_col_add(col_name, self._set_type(default_value))
            self.refresh_view()
        except ValueError as e:
            QMessageBox.warning(self.main_window, "Add Column Error", str(e))
        except Exception:
            QApplication.beep()

    def on_delete_row(self, row_index):
        try:
            self.manager.add_row_delete(row_index)
            self.main_window.set_panel("general")
            self.refresh_view()
        except Exception:
            QApplication.beep()

    def on_delete_col(self, uuid):
        try:
            self.manager.add_col_delete(uuid)
            self.main_window.set_panel("general")
            self.refresh_view()
        except Exception:
            QApplication.beep()

    def on_delete_pressed(self):
        panel = self.main_window.left_layout.currentWidget()
        if panel == self.main_window.column_options:
            uuid = self.main_window.column_options._current_uuid
            if uuid:
                self.on_delete_col(uuid)
            else:
                QApplication.beep()
        elif panel == self.main_window.row_options:
            row = self.main_window.row_options._current_row
            if row != -1:
                self.on_delete_row(row)
            else:
                QApplication.beep()
        else:
            QApplication.beep()

    def _apply_reorder(self, new_order):
        """Helper method to apply column reorder transformation and update the view accordingly."""
        transformation = ColumnReorderTransformation(new_order)
        self.manager.history.append(transformation)
        self.manager.df_wrapper = transformation.apply(self.manager.df_wrapper)
        self.manager.redo.clear()
        
        header = self.main_window.table_view.horizontalHeader()
        header.blockSignals(True)
        for logical_index in range(header.count()):
            visual_pos = header.visualIndex(logical_index)
            if visual_pos != logical_index:
                header.moveSection(visual_pos, logical_index)
        header.blockSignals(False)
        
        self.refresh_view()

    def undo(self):
        try:
            self.manager.undo_transformation()
            self.refresh_view()
        except Exception:
            QApplication.beep()

    def redo(self):
        try:
            self.manager.redo_transformation()
            self.refresh_view()
        except Exception:
            QApplication.beep()

    def refresh_view(self):
        """Refresh the table view and update stats display based on the current state of the DataFrame, 
ensuring that the UI reflects any changes from transformations or data edits."""
        self.model.update_wrapper(self.manager.df_wrapper)
        self._update_menu_action_states()
        has_loaded_df = self.manager.df_wrapper.df is not None
        self.main_window.show_table_placeholder(not has_loaded_df)
        row_count = 0 if not has_loaded_df else self.manager.df_wrapper.df.shape[0]
        col_count = self.model.columnCount()
        self.main_window.general_options.row_count_label.setText(f"Number of rows: {row_count}")
        self.main_window.general_options.column_count_label.setText(f"Number of columns: {col_count}")