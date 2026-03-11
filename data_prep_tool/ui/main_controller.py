from PyQt6.QtWidgets import QFileDialog, QMessageBox, QHeaderView
from PyQt6.QtCore import Qt
import pandas as pd
import numpy as np

from tool_uuid.models.table_model import DataFrameModel
from tool_uuid.core.transformation_manager import TransformationManager
from tool_uuid.core.script_generator import ScriptGenerator
from tool_uuid.transformation.col_reorder_transformation import ColumnReorderTransformation
from tool_uuid.core.data_loader import load_csv

# Import transformation types
from tool_uuid.transformation.binning_transformation import BinningTransformation
from tool_uuid.transformation.one_hot_encode import oneHotEncodeTransformation

class MainController:
    def __init__(self, main_window, transformation_manager):
        self.main_window = main_window
        self.manager = transformation_manager
        self._active_row_index = -1
        
        self.model = DataFrameModel(self.manager.df_wrapper)
        self.main_window.table_view.setModel(self.model)

        self.main_window.action_load.triggered.connect(self.open_csv)
        self.main_window.action_exit.triggered.connect(self.main_window.close)
        self.main_window.action_export.triggered.connect(self.export_script)
        self.main_window.action_undo.triggered.connect(self.undo)
        self.main_window.action_redo.triggered.connect(self.redo)

        self.main_window.table_view.horizontalHeader().sectionClicked.connect(self.on_header_clicked)
        self.main_window.table_view.verticalHeader().sectionClicked.connect(self.on_row_clicked)
        self.main_window.table_view.clicked.connect(self.on_cell_clicked)
        self.main_window.table_view.column_reorder_requested.connect(self.on_column_reorder_drag)

        self.main_window.general_options.binary_values_changed.connect(self.on_binary_values_changed)

        col_panel = self.main_window.column_options
        col_panel.column_rename_request.connect(self.on_column_rename)
        col_panel.encoder_options.column_encoding_request.connect(self.on_encoding_change)
        col_panel.encoder_options.column_binning_request.connect(self.on_binning_change)
        col_panel.encoder_options.child_rename_request.connect(self.on_column_rename)
        col_panel.column_reorder.column_reorder_request.connect(self.on_manual_reorder)
        col_panel.close_request.connect(self.on_panel_close)

        cell_panel = self.main_window.cell_options
        cell_panel.cell_edit.cell_change_request.connect(self.on_cell_edit)
        cell_panel.column_rename.column_rename_request.connect(self.on_column_rename)
        cell_panel.close_request.connect(self.on_panel_close)

        self.main_window.row_options.close_request.connect(self.on_panel_close)

        self.refresh_view()

    def on_panel_close(self):
        self.main_window.set_panel("general")
        self.main_window.table_view.clearSelection()
        self._active_row_index = -1

    def on_binary_values_changed(self, true_val, false_val):
        self.manager.update_binary_labels(true_val, false_val)
        self.refresh_view()

    def open_csv(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self.main_window, "Open CSV File", "", "CSV Files (*.csv)"
        )
        if file_path:
            try:
                new_wrapper = load_csv(file_path)
                self.manager = TransformationManager(new_wrapper)
                self.model.update_wrapper(self.manager.df_wrapper)
                self.main_window.set_panel("general")
                self.refresh_view()
            except Exception as e:
                QMessageBox.critical(self.main_window, "Error", f"Failed to load CSV:\n{str(e)}")

    def export_script(self):
        try:
            graph = self.manager.build_dependency_graph()
            generator = ScriptGenerator(graph)
            visual_order = self.manager.df_wrapper.get_all_uuids()
            script = generator.generate_script(final_col_uuids=visual_order)
            
            path, _ = QFileDialog.getSaveFileName(self.main_window, "Save Script", "cleaning_script.py", "Python (*.py)")
            if path:
                with open(path, "w") as f: f.write(script)
                QMessageBox.information(self.main_window, "Success", "Exported!")
        except Exception as e:
            QMessageBox.critical(self.main_window, "Error", str(e))

    def _calculate_stats(self, series: pd.Series) -> str:
        if series is None or series.empty: return "No data."
        total = len(series)
        nulls = series.isnull().sum()
        stats = f"Total Rows: {total}\nMissing: {nulls}\n"
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

    def on_header_clicked(self, logical_index):
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
        target_series = wrapper.get_col_data_by_uuid(uuid)

        if target_series is not None and pd.api.types.is_numeric_dtype(target_series):
             data_min = float(target_series.min())
             data_max = float(target_series.max())

        if is_child:
             parent_uuid = wrapper.get_parent_uuid(uuid)
             for trans in reversed(self.manager.history):
                 if getattr(trans, 'col_uuid', None) == parent_uuid:
                     if hasattr(trans, 'values') and trans.values is not None:
                         target_series = trans.values
                         if pd.api.types.is_numeric_dtype(target_series):
                             data_min = float(target_series.min())
                             data_max = float(target_series.max())
                     break

        self.main_window.column_options.set_stats(self._calculate_stats(target_series))

        encoder_widget = self.main_window.column_options.encoder_options
        
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
            
            encoder_widget.set_current_column(parent_uuid, strategy, children_names, n_bins, parent_name, data_min, data_max)
        else:
            encoder_widget.set_current_column(uuid, "None", min_val=data_min, max_val=data_max)

    def on_binning_change(self, uuid, strategy, n_bins, cutoffs):
        if strategy == "Custom":
            if not cutoffs: return
            if any(cutoffs[i] >= cutoffs[i+1] for i in range(len(cutoffs)-1)):
                QMessageBox.warning(self.main_window, "Invalid Cutoffs", "Values must be strictly increasing.")
                return

        if self.manager.history:
            last_trans = self.manager.history[-1]
            if isinstance(last_trans, (BinningTransformation, oneHotEncodeTransformation)):
                if last_trans.col_uuid == uuid:
                    self.manager.undo_transformation()
        
        all_uuids = self.manager.df_wrapper.get_all_uuids()
        if uuid in all_uuids:
            col_index = all_uuids.index(uuid)
            try:
                self.manager.add_binning(col_index, strategy, n_bins, cutoffs)
                self.refresh_view()
                children = self.manager.df_wrapper.get_children_uuids(uuid)
                if children and children[0] in self.manager.df_wrapper.get_all_uuids():
                    self.on_header_clicked(self.manager.df_wrapper.get_all_uuids().index(children[0]))
            except Exception as e:
                QMessageBox.critical(self.main_window, "Error", str(e))

    def on_encoding_change(self, uuid, encoding):
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
                self.manager.add_onehot(col_index)
                self.refresh_view()
                children = self.manager.df_wrapper.get_children_uuids(uuid)
                if children and children[0] in self.manager.df_wrapper.get_all_uuids():
                    self.on_header_clicked(self.manager.df_wrapper.get_all_uuids().index(children[0]))

    def on_row_clicked(self, logical_index):
        self.main_window.set_panel("row")
        if hasattr(self.main_window.row_options, 'row_index'):
            self.main_window.row_options.row_index.setText(f"Row Index: {logical_index}")

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
        if uuid in all_uuids:
            col_index = all_uuids.index(uuid)
            self.manager.add_rename(col_index, new_name)
            self.refresh_view()

    def on_cell_edit(self, uuid, new_value):
        if self._active_row_index != -1:
            self.manager.add_cell_edit(self._active_row_index, uuid, new_value)
            self.refresh_view()

    def on_column_reorder_drag(self, new_uuid_order):
        self._apply_reorder(new_uuid_order)

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
            pass

    def _apply_reorder(self, new_order):
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
        self.manager.undo_transformation()
        self.refresh_view()

    def redo(self):
        self.manager.redo_transformation()
        self.refresh_view()

    def refresh_view(self):
        self.model.update_wrapper(self.manager.df_wrapper)
        row_count = self.model.rowCount()
        col_count = self.model.columnCount()
        self.main_window.general_options.row_count_label.setText(f"Number of rows: {row_count}")
        self.main_window.general_options.column_count_label.setText(f"Number of columns: {col_count}")