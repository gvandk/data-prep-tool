import unittest
import pandas as pd
import numpy as np
from tool_uuid.core.dataframe_wrapper import DataFrameWrapper
from tool_uuid.core.transformation_manager import TransformationManager
from tool_uuid.core.script_generator import ScriptGenerator
from tool_uuid.transformation.binning_transformation import BinningTransformation

class TestBinningTransformation(unittest.TestCase):
    def setUp(self):
        # Create data with a clear range for easy binning verification
        # 0, 10, 20, ... 90
        self.data = pd.DataFrame({'Score': [0, 10, 20, 30, 40, 50, 60, 70, 80, 90]})
        self.wrapper = DataFrameWrapper(self.data)
        self.score_uuid = self.wrapper.get_uuid_by_name('Score')
        self.col_index = 0 # 'Score' is at index 0

    def test_equal_width_apply(self):
        """Test standard Equal Width binning (pd.cut)."""
        transform = BinningTransformation(self.col_index, "Equal Width", 2)
        self.wrapper = transform.apply(self.wrapper)

        # 1. Check Rename
        self.assertIn('Score_binned', self.wrapper.df.columns)
        self.assertNotIn('Score', self.wrapper.df.columns)
        
        # 2. Check Data
        # Range 0-90 split into 2 bins: (-0.09, 45.0] and (45.0, 90.0]
        # 0, 10, 20, 30, 40 -> Bin 1
        # 50, 60, 70, 80, 90 -> Bin 2
        binned_col = self.wrapper.df['Score_binned']
        self.assertEqual(binned_col.nunique(), 2)
        self.assertEqual(binned_col.iloc[0], binned_col.iloc[4]) # 0 and 40 in same bin
        self.assertNotEqual(binned_col.iloc[0], binned_col.iloc[5]) # 0 and 50 in diff bins

    def test_equal_frequency_apply(self):
        """Test Equal Frequency binning (pd.qcut)."""
        # Create skewed data: many 0s, few 100s
        data = pd.DataFrame({'Skewed': [0, 0, 0, 0, 100, 100, 100, 100]})
        wrapper = DataFrameWrapper(data)
        uuid = wrapper.get_uuid_by_name('Skewed')
        
        transform = BinningTransformation(0, "Equal Frequency", 2)
        wrapper = transform.apply(wrapper)

        # Should result in 2 buckets of 4 items each
        counts = wrapper.df['Skewed_binned'].value_counts()
        self.assertEqual(counts.iloc[0], 4)
        self.assertEqual(counts.iloc[1], 4)

    def test_intraordinal_apply(self):
        """Test Intraordinal scaling (labels=False)."""
        transform = BinningTransformation(self.col_index, "Intraordinal", 5)
        self.wrapper = transform.apply(self.wrapper)

        # Should result in integer codes 0, 1, 2, 3, 4
        # Since data is perfect 0-90, we expect strict distribution
        binned_col = self.wrapper.df['Score_binned']
        
        # Check type is integer/numeric, not categorical interval
        self.assertTrue(pd.api.types.is_numeric_dtype(binned_col))
        
        # 0 should be code 0, 90 should be code 4
        self.assertEqual(binned_col.min(), 0)
        self.assertEqual(binned_col.max(), 4)

    def test_undo_restores_state(self):
        """Test that undo restores name and original float data."""
        original_data = self.wrapper.df['Score'].copy()
        
        transform = BinningTransformation(self.col_index, "Equal Width", 2)
        self.wrapper = transform.apply(self.wrapper)
        
        # Apply Undo
        self.wrapper = transform.undo(self.wrapper)
        
        # Verify Name
        self.assertIn('Score', self.wrapper.df.columns)
        self.assertNotIn('Score_binned', self.wrapper.df.columns)
        
        # Verify Data Equality
        pd.testing.assert_series_equal(self.wrapper.df['Score'], original_data)


class TestBinningIntegration(unittest.TestCase):
    def setUp(self):
        self.data = pd.DataFrame({'A': [1, 5, 10]})
        self.wrapper = DataFrameWrapper(self.data)
        self.manager = TransformationManager(self.wrapper)

    def test_script_generation_equal_width(self):
        self.manager.add_binning(0, "Equal Width", 3)
        
        graph = self.manager.build_dependency_graph()
        script = ScriptGenerator(graph).generate_script()
        
        self.assertIn("pd.cut(df['A'], bins=3)", script)
        self.assertIn("df.drop(columns=['A'], inplace=True)", script)

    def test_script_generation_equal_frequency(self):
        self.manager.add_binning(0, "Equal Frequency", 4)
        
        graph = self.manager.build_dependency_graph()
        script = ScriptGenerator(graph).generate_script()
        
        self.assertIn("pd.qcut(df['A'], q=4, duplicates='drop')", script)

    def test_script_generation_intraordinal(self):
        self.manager.add_binning(0, "Intraordinal", 5)
        
        graph = self.manager.build_dependency_graph()
        script = ScriptGenerator(graph).generate_script()
        
        self.assertIn("pd.cut(df['A'], bins=5, labels=False)", script)

    def test_complex_flow_rename_then_bin(self):
        """Test consistency when renaming BEFORE binning."""
        # 1. Rename 'A' -> 'Age'
        self.manager.add_rename(0, 'Age')
        
        # 2. Bin 'Age' (Index is still 0)
        self.manager.add_binning(0, "Equal Width", 2)
        
        graph = self.manager.build_dependency_graph()
        script = ScriptGenerator(graph).generate_script()
        
        # Script should rename first
        self.assertIn("df.rename(columns={'A': 'Age'}, inplace=True)", script)
        
        # Then bin 'Age'
        self.assertIn("pd.cut(df['Age'], bins=2)", script)
        self.assertIn("df.drop(columns=['Age'], inplace=True)", script)

if __name__ == "__main__":
    unittest.main()