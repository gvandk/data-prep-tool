import os
import unittest
from unittest.mock import patch

import pandas as pd
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QAbstractItemView

from data_prep_tool.core.dataframe_wrapper import DataFrameWrapper
from data_prep_tool.core.transformation_manager import TransformationManager
from data_prep_tool.ui.main_controller import MainController
from data_prep_tool.ui.main_window import MainWindow


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


class TestMainControllerSelectionState(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls._app = QApplication.instance() or QApplication([])

	def setUp(self):
		df = pd.DataFrame(
			{
				"A": [1, 2, 3, 4],
				"B": ["x", "y", "z", "w"],
				"C": [True, False, True, False],
			}
		)
		wrapper = DataFrameWrapper(df)
		manager = TransformationManager(wrapper)
		self.window = MainWindow()
		self.controller = MainController(self.window, manager)

	def tearDown(self):
		self.window.close()

	def test_update_row_selection_shift_selects_range(self):
		with patch(
			"data_prep_tool.ui.selection_state.QApplication.keyboardModifiers",
			return_value=Qt.KeyboardModifier.NoModifier,
		):
			selected_rows = self.controller._update_row_selection(1)
		self.assertEqual(selected_rows, [1])

		with patch(
			"data_prep_tool.ui.selection_state.QApplication.keyboardModifiers",
			return_value=Qt.KeyboardModifier.ShiftModifier,
		):
			selected_rows = self.controller._update_row_selection(3)

		self.assertEqual(selected_rows, [1, 2, 3])
		self.assertEqual(self.controller._selected_rows, {1, 2, 3})

	def test_update_header_selection_ctrl_toggles_columns(self):
		with patch(
			"data_prep_tool.ui.selection_state.QApplication.keyboardModifiers",
			return_value=Qt.KeyboardModifier.NoModifier,
		):
			selected_columns = self.controller._update_header_selection(0)
		self.assertEqual(selected_columns, [0])

		with patch(
			"data_prep_tool.ui.selection_state.QApplication.keyboardModifiers",
			return_value=Qt.KeyboardModifier.ControlModifier,
		):
			selected_columns = self.controller._update_header_selection(2)
		self.assertEqual(selected_columns, [0, 2])

		with patch(
			"data_prep_tool.ui.selection_state.QApplication.keyboardModifiers",
			return_value=Qt.KeyboardModifier.ControlModifier,
		):
			selected_columns = self.controller._update_header_selection(0)
		self.assertEqual(selected_columns, [2])

	def test_panel_close_resets_selection_state(self):
		self.controller._selected_rows = {1, 2}
		self.controller._last_row_clicked = 2
		self.controller._header_selected_columns = {0, 1}
		self.controller._last_header_clicked_column = 1
		self.controller._active_row_index = 3

		self.controller.on_panel_close()

		self.assertEqual(self.controller._selected_rows, set())
		self.assertIsNone(self.controller._last_row_clicked)
		self.assertEqual(self.controller._header_selected_columns, set())
		self.assertIsNone(self.controller._last_header_clicked_column)
		self.assertEqual(self.controller._active_row_index, -1)
		self.assertEqual(
			self.window.table_view.selectionMode(),
			QAbstractItemView.SelectionMode.SingleSelection,
		)

	def test_cell_click_clears_multi_selection_state(self):
		self.controller._selected_rows = {0, 1}
		self.controller._last_row_clicked = 1
		self.controller._header_selected_columns = {0, 2}
		self.controller._last_header_clicked_column = 2

		target_index = self.controller.model.index(2, 1)
		self.controller.on_cell_clicked(target_index)

		self.assertEqual(self.controller._selected_rows, set())
		self.assertIsNone(self.controller._last_row_clicked)
		self.assertEqual(self.controller._header_selected_columns, set())
		self.assertIsNone(self.controller._last_header_clicked_column)
		self.assertEqual(self.controller._active_row_index, 2)
