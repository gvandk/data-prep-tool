import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pandas as pd
from PyQt6.QtWidgets import QApplication

from data_prep_tool.core.dataframe_wrapper import DataFrameWrapper
from data_prep_tool.core.transformation_manager import TransformationManager
from data_prep_tool.ui.main_controller import MainController
from data_prep_tool.ui.main_window import MainWindow
from data_prep_tool.ui.layouts.column_filter import ColumnFilter
from data_prep_tool.ui.layouts.column_encoding import ColumnEncoding
from data_prep_tool.ui.layouts.column_options import ColumnPanel
from data_prep_tool.ui.layouts.row_options import RowPanel


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


class TestColumnFilter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.widget = ColumnFilter()

    def test_switching_columns_clears_filter_input(self):
        self.widget.set_current_column("u1", "First")
        self.widget.value_input.setText("stale value")

        self.widget.set_current_column("u2", "Second")

        self.assertEqual(self.widget.value_input.text(), "")


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


class TestMainControllerGeneralInfoStats(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._app = QApplication.instance() or QApplication([])

    def setUp(self):
        df = pd.DataFrame(
            {
                "A": [1, np.nan],
                "B": ["x", "y"],
                "C": [True, False],
                "D": ["True", "False"],
            }
        )
        wrapper = DataFrameWrapper(df)
        manager = TransformationManager(wrapper)
        self.window = MainWindow()
        self.controller = MainController(self.window, manager)

    def tearDown(self):
        self.window.close()

    def test_general_panel_shows_missing_values_and_column_dtypes(self):
        self.controller.refresh_view()

        self.assertEqual(self.window.general_options.missing_values_label.text(), "Total missing values: 1")
        self.assertTrue(self.window.general_options.column_types_title_label.font().bold())
        dtype_text = self.window.general_options.column_types_label.text()
        self.assertIn('"A": float64', dtype_text)
        self.assertIn('"B": object', dtype_text)
        self.assertIn('"C": bool', dtype_text)
        self.assertIn('"D": binary', dtype_text)

    def test_general_panel_keeps_binary_dtype_after_custom_label_change(self):
        self.controller.on_binary_values_changed("Apple", "Banana")

        dtype_text = self.window.general_options.column_types_label.text()
        self.assertIn('"D": binary', dtype_text)
        self.assertNotIn('"D": object', dtype_text)


class TestMainControllerRowDeleteSelection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._app = QApplication.instance() or QApplication([])

    def setUp(self):
        df = pd.DataFrame({"A": [1, 2, 3, 4, 5]})
        wrapper = DataFrameWrapper(df)
        manager = TransformationManager(wrapper)
        self.window = MainWindow()
        self.controller = MainController(self.window, manager)

    def tearDown(self):
        self.window.close()

    def test_delete_rows_is_single_undoable_action(self):
        self.controller.on_delete_rows([1, 3])

        self.assertEqual(list(self.controller.manager.df_wrapper.df["A"]), [1, 3, 5])
        self.assertEqual(len(self.controller.manager.history), 1)

        self.controller.undo()
        self.assertEqual(list(self.controller.manager.df_wrapper.df["A"]), [1, 2, 3, 4, 5])


class TestMainControllerRowAddVisibility(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._app = QApplication.instance() or QApplication([])

    def setUp(self):
        df = pd.DataFrame({"A": [1, 2, 3, 4, 5]})
        wrapper = DataFrameWrapper(df)
        manager = TransformationManager(wrapper)
        self.window = MainWindow()
        self.controller = MainController(self.window, manager)

    def tearDown(self):
        self.window.close()

    @patch("data_prep_tool.ui.main_controller.QInputDialog.getText", return_value=("9", True))
    def test_add_row_expands_view_and_focuses_new_row_when_capped(self, _mock_get_text):
        self.controller.on_view_settings_changed(3, 2)

        with patch.object(self.window.table_view, "scrollTo", wraps=self.window.table_view.scrollTo) as scroll_to_mock:
            self.controller.on_add_row()

        self.assertEqual(self.controller.model.max_rows, 6)
        self.assertEqual(self.window.general_options.max_rows_input.text(), "6")
        self.assertEqual(self.controller.model.rowCount(), 6)

        selection_model = self.window.table_view.selectionModel()
        self.assertIsNotNone(selection_model)
        self.assertEqual(selection_model.currentIndex().row(), 5)

        self.assertTrue(scroll_to_mock.called)
        scrolled_rows = [call.args[0].row() for call in scroll_to_mock.call_args_list if call.args]
        self.assertIn(5, scrolled_rows)


class TestColumnPanelMultiSelection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.panel = ColumnPanel()

    def test_multi_column_mode_shows_only_merge_controls(self):
        self.panel.set_multi_column_mode(["u1", "u2"], ["A", "B"], can_merge=True)

        self.assertFalse(self.panel.column_merge.isHidden())
        self.assertTrue(self.panel.column_filter.isHidden())
        self.assertTrue(self.panel.encoder_options.isHidden())
        self.assertTrue(self.panel.delete_btn.isHidden())
        self.assertTrue(self.panel.column_merge.merge_button.isEnabled())
        self.assertTrue(self.panel.column_merge.delete_sources_checkbox.isChecked())

    def test_multi_column_mode_disables_merge_when_not_binary(self):
        self.panel.set_multi_column_mode(["u1", "u2"], ["A", "B"], can_merge=False)

        self.assertFalse(self.panel.column_merge.isHidden())
        self.assertFalse(self.panel.column_merge.merge_button.isEnabled())

    def test_single_column_mode_restores_standard_controls(self):
        self.panel.set_multi_column_mode(["u1", "u2"], ["A", "B"], can_merge=True)
        self.panel.set_single_column_mode()

        self.assertTrue(self.panel.column_merge.isHidden())
        self.assertFalse(self.panel.column_filter.isHidden())
        self.assertFalse(self.panel.encoder_options.isHidden())
        self.assertFalse(self.panel.delete_btn.isHidden())

    def test_filter_widget_is_above_encoding_widget(self):
        panel_layout = self.panel.layout()
        filter_index = panel_layout.indexOf(self.panel.column_filter)
        encoding_index = panel_layout.indexOf(self.panel.encoder_options)

        self.assertGreaterEqual(filter_index, 0)
        self.assertGreaterEqual(encoding_index, 0)
        self.assertLess(filter_index, encoding_index)

    def test_merge_checkbox_is_above_merge_button(self):
        group_layout = self.panel.column_merge.group.layout()
        checkbox_index = group_layout.indexOf(self.panel.column_merge.delete_sources_checkbox)
        button_index = group_layout.indexOf(self.panel.column_merge.merge_button)

        self.assertLess(checkbox_index, button_index)


class TestRowPanelMultiSelection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.panel = RowPanel()

    def test_set_rows_displays_selected_rows(self):
        self.panel.set_rows([3, 1, 3])

        self.assertIn("Selected rows (2): 1, 3", self.panel.row_index.text())
        self.assertTrue(self.panel.delete_btn.isEnabled())
        self.assertIn("(2)", self.panel.delete_btn.text())

    def test_delete_emits_all_selected_rows(self):
        self.panel.set_rows([2, 5])
        captured = []
        self.panel.delete_row_requested.connect(lambda rows: captured.append(rows))

        self.panel._on_delete()

        self.assertEqual(captured, [[2, 5]])

    def test_set_rows_empty_disables_delete(self):
        self.panel.set_rows([])

        self.assertIn("Selected rows: none", self.panel.row_index.text())
        self.assertFalse(self.panel.delete_btn.isEnabled())
