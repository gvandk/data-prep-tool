import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pandas as pd
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QItemSelectionModel

from data_prep_tool.core.dataframe_wrapper import DataFrameWrapper
from data_prep_tool.core.transformation_manager import TransformationManager
from data_prep_tool.ui.main_controller import MainController
from data_prep_tool.ui.main_window import MainWindow
from data_prep_tool.ui.layouts.column_encoding import ColumnEncoding


class TestColumnEncodingOptions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.widget = ColumnEncoding()

    def _combo_items(self):
        return [self.widget.encoding_combo.itemText(i) for i in range(self.widget.encoding_combo.count())]

    def test_binning_options_hidden_for_non_numeric_columns(self):
        self.widget.set_current_column(
            uuid="col-1",
            encoding="None",
            can_one_hot=True,
            can_binning=False,
        )

        self.assertEqual(self._combo_items(), ["None", "One-Hot"])

    def test_binning_options_visible_for_numeric_columns(self):
        self.widget.set_current_column(
            uuid="col-1",
            encoding="Equal Width",
            can_one_hot=True,
            can_binning=True,
        )

        self.assertEqual(
            self._combo_items(),
            ["None", "One-Hot", "Equal Width", "Equal Frequency", "Ordinal", "Custom"],
        )
        self.assertEqual(self.widget.encoding_combo.currentText(), "Equal Width")


class TestMainControllerMenuState(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._app = QApplication.instance() or QApplication([])

    def setUp(self):
        df = pd.DataFrame({"A": [1, 2, 3]})
        wrapper = DataFrameWrapper(df)
        manager = TransformationManager(wrapper)
        self.window = MainWindow()
        self.controller = MainController(self.window, manager)

    def tearDown(self):
        self.window.close()

    def test_undo_redo_actions_reflect_history_state(self):
        self.assertFalse(self.window.action_undo.isEnabled())
        self.assertFalse(self.window.action_redo.isEnabled())

        self.controller.manager.add_row_add(0)
        self.controller.refresh_view()

        self.assertTrue(self.window.action_undo.isEnabled())
        self.assertFalse(self.window.action_redo.isEnabled())

        self.controller.undo()

        self.assertFalse(self.window.action_undo.isEnabled())
        self.assertTrue(self.window.action_redo.isEnabled())


class TestMainControllerMultiColumnEncoding(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._app = QApplication.instance() or QApplication([])

    def setUp(self):
        df = pd.DataFrame(
            {
                "numeric": [1, 2, 3],
                "category": ["A", "B", "A"],
                "other": [10, 20, 30],
            }
        )
        wrapper = DataFrameWrapper(df)
        manager = TransformationManager(wrapper)
        self.window = MainWindow()
        self.controller = MainController(self.window, manager)

    def tearDown(self):
        self.window.close()

    def _encoding_combo_items(self):
        combo = self.window.column_options.encoder_options.encoding_combo
        return [combo.itemText(i) for i in range(combo.count())]

    def _select_columns_by_indexes(self, indexes):
        selection_model = self.window.table_view.selectionModel()
        model = self.window.table_view.model()

        selection_model.clearSelection()
        for col_index in indexes:
            index = model.index(0, col_index)
            selection_model.select(index, QItemSelectionModel.SelectionFlag.Select)

    def test_mixed_numeric_and_categorical_selection_shows_common_encoding_options(self):
        self._select_columns_by_indexes([0, 1])

        self.controller.on_header_clicked(0)

        self.assertEqual(self._encoding_combo_items(), ["None", "One-Hot"])

    def test_one_hot_applies_to_all_selected_columns(self):
        self._select_columns_by_indexes([0, 1])
        uuid_numeric = self.controller.model.get_column_uuid(0)

        self.controller.on_encoding_change(uuid_numeric, "One-Hot")

        output_columns = list(self.controller.manager.df_wrapper.df.columns)
        self.assertNotIn("numeric", output_columns)
        self.assertNotIn("category", output_columns)
        self.assertIn("other", output_columns)

    def test_multi_select_one_hot_then_none_does_not_crash(self):
        self._select_columns_by_indexes([0, 1])
        uuid_numeric = self.controller.model.get_column_uuid(0)

        self.controller.on_encoding_change(uuid_numeric, "One-Hot")
        self.controller.on_encoding_change(uuid_numeric, "None")

        # Re-open column panel to cover selection/ordering path after parent-child transitions.
        self.controller.on_header_clicked(0)

        output_columns = list(self.controller.manager.df_wrapper.df.columns)
        self.assertIn("numeric", output_columns)
        self.assertIn("category", output_columns)

    def test_multi_select_one_hot_then_none_keeps_both_redos(self):
        self._select_columns_by_indexes([0, 1])
        uuid_numeric = self.controller.model.get_column_uuid(0)

        self.controller.on_encoding_change(uuid_numeric, "One-Hot")
        self.controller.on_encoding_change(uuid_numeric, "None")

        self.assertEqual(len(self.controller.manager.redo), 2)

        self.controller.redo()
        cols_after_first_redo = list(self.controller.manager.df_wrapper.df.columns)
        self.assertTrue(any(col.startswith("numeric_") for col in cols_after_first_redo))
        self.assertIn("category", cols_after_first_redo)

        self.controller.redo()
        cols_after_second_redo = list(self.controller.manager.df_wrapper.df.columns)
        self.assertTrue(any(col.startswith("numeric_") for col in cols_after_second_redo))
        self.assertTrue(any(col.startswith("category_") for col in cols_after_second_redo))
