import unittest
import pandas as pd
import numpy as np
from data_prep_tool.core.dataframe_wrapper import DataFrameWrapper
from data_prep_tool.transformation.cell_edit_transformation import CellEditTransformation

class TestTransformations(unittest.TestCase):
    def setUp(self):
        # Create dummy data
        data = pd.DataFrame({'A': [10, 20, 30]})
        self.wrapper = DataFrameWrapper(data)
        self.uuid_a = self.wrapper.get_uuid_by_name('A')

    def test_cell_edit_apply_undo(self):
        # 1. Apply Edit (Change 10 -> 99 at index 0)
        transform = CellEditTransformation(0, self.uuid_a, 99)
        self.wrapper = transform.apply(self.wrapper)
        
        # Check Pandas updated
        self.assertEqual(self.wrapper.df.at[0, 'A'], 99)
        
        # 2. Undo
        self.wrapper = transform.undo(self.wrapper)
        
        # Check restored
        self.assertEqual(self.wrapper.df.at[0, 'A'], 10)

    def test_cell_edit_type_safety(self):
        """Test that editing an int column with a string number keeps it int."""
        transform = CellEditTransformation(0, self.uuid_a, "99") # String input
        self.wrapper = transform.apply(self.wrapper)
        
        # Should be int 99, not string "99"
        val = self.wrapper.df.at[0, 'A']
        self.assertEqual(val, 99)
        
        # [FIX] Accept both Python native types AND Numpy types
        self.assertIsInstance(val, (int, float, np.integer, np.floating))