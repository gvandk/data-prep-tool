import unittest
import pandas as pd
from PyQt6.QtCore import Qt
from data_prep_tool.core.dataframe_wrapper import DataFrameWrapper
from data_prep_tool.models.table_model import DataFrameModel

class TestTableModel(unittest.TestCase):
    def setUp(self):
        df = pd.DataFrame({'A': [1, 2]})
        self.wrapper = DataFrameWrapper(df)
        self.model = DataFrameModel(self.wrapper)
        self.uuid_a = self.wrapper.get_uuid_by_name('A')

    def test_flags_are_not_editable(self):
        index = self.model.index(0, 0)
        flags = self.model.flags(index)
        self.assertFalse(flags & Qt.ItemFlag.ItemIsEditable)

    def test_set_data_does_not_update_or_emit(self):
        """setData should return False and keep DF unchanged for non-editable model."""
        index = self.model.index(0, 0)
        changed = self.model.setData(index, 99, role=Qt.ItemDataRole.EditRole)
        self.assertFalse(changed)
        
        # Verify data was not updated
        self.assertEqual(self.wrapper.df.at[0, 'A'], 1)