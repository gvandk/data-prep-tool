import unittest
import pandas as pd
from PyQt6.QtCore import Qt
from core.dataframe_wrapper import DataFrameWrapper
from models.table_model import DataFrameModel
from unittest.mock import Mock

class TestTableModel(unittest.TestCase):
    def setUp(self):
        df = pd.DataFrame({'A': [1, 2]})
        self.wrapper = DataFrameWrapper(df)
        self.model = DataFrameModel(self.wrapper)
        self.uuid_a = self.wrapper.get_uuid_by_name('A')

    def test_flags_are_editable(self):
        index = self.model.index(0, 0)
        flags = self.model.flags(index)
        self.assertTrue(flags & Qt.ItemFlag.ItemIsEditable)

    def test_set_data_emits_signal(self):
        """setData should NOT update DF directly, but emit a signal."""
        # Mock the signal
        self.model.cell_edit_request = Mock()
        self.model.cell_edit_request.emit = Mock()
        
        index = self.model.index(0, 0)
        self.model.setData(index, 99, role=Qt.ItemDataRole.EditRole)
        
        # Verify signal was called with correct args
        # Arg 1: Row (0), Arg 2: UUID, Arg 3: Value (99)
        self.model.cell_edit_request.emit.assert_called_with(0, self.uuid_a, 99)
        
        # Verify Data was NOT updated yet (Controller does that)
        self.assertEqual(self.wrapper.df.at[0, 'A'], 1)