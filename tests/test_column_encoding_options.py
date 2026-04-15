import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pandas as pd
from PyQt6.QtWidgets import QApplication

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
